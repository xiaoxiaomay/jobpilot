"""
Page 2: Apply — AI-Powered Resume & Cover Letter Generator
This is the MOST IMPORTANT page. Uses Claude API to generate
ATS-optimized, customized resumes and cover letters.
"""

import json
import os
import re
import streamlit as st

from core.db import get_connection, init_db, log_activity
from core.ats_scorer import score_ats, extract_skills_for_db
from core.resume_generator import generate_application, load_profile, get_role_types, validate_no_fabrication
from core.docx_builder import build_resume, build_cover_letter
from core.skills_analyzer import save_skill_mentions

init_db()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILE_PATH = os.path.join(DATA_DIR, "master_profile.json")

st.set_page_config(page_title="Apply — JobPilot", page_icon="📝", layout="wide")
st.title("📝 Application Generator")

# Allowed numbers from the real profile — used to highlight unverified claims
_ALLOWED_NUMBERS = {
    "5%", "30%", "0.2%", "0.5%", "2.5x", "2.5X",
    "13 million", "$13", "31 million", "$31", "22 million", "$22",
    "100+", "9 entities", "20+", "22 entities", "18 countries",
    "7,000", "7000", "10+", "10 years",
    "2012", "2007", "2011", "2024", "2026",
}


def _highlight_unverified(text: str) -> str:
    """Return markdown text with unverified numbers highlighted in bold red."""
    _ALLOWED_PCTS = {"5%", "30%", "0.2%", "0.5%"}
    _ALLOWED_DOLLAR_PARTS = {"$13", "$31", "$22", "13 million", "31 million", "22 million"}
    _ALLOWED_MULT = {"2.5x", "2.5X"}

    def _check_pct(match):
        token = match.group(0)
        if token in _ALLOWED_PCTS:
            return token
        return f"**:red[{token}]**"

    def _check_dollar(match):
        token = match.group(0)
        if any(a in token for a in _ALLOWED_DOLLAR_PARTS):
            return token
        return f"**:red[{token}]**"

    def _check_mult(match):
        token = match.group(0)
        if token in _ALLOWED_MULT:
            return token
        return f"**:red[{token}]**"

    # Highlight percentages (exact match only)
    result = re.sub(r'\d+\.?\d*%', _check_pct, text)
    # Highlight dollar amounts (substring match for "$31 million" etc.)
    result = re.sub(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|k|M|B))?', _check_dollar, result)
    # Highlight "Nx" multipliers
    result = re.sub(r'\b\d+\.?\d*[xX]\b', _check_mult, result)
    return result

# Load profile
try:
    profile = load_profile(PROFILE_PATH)
except FileNotFoundError:
    st.error("Master profile not found at `data/master_profile.json`. Please copy it from `reference/`.")
    st.stop()

personal = profile.get("personal", {})
education = profile.get("education", [])

# ─── Layout: Left (input) | Right (output) ───────────────────────────
left_col, right_col = st.columns([1, 1.2])

# ─── LEFT PANEL — Input ──────────────────────────────────────────────
with left_col:
    st.subheader("Job Details")

    input_mode = st.radio(
        "Input method",
        ["Paste Job Description", "Select from saved jobs"],
        horizontal=True,
        label_visibility="collapsed",
    )

    jd_text = ""
    company = ""
    title = ""
    selected_job_id = None

    if input_mode == "Select from saved jobs":
        conn = get_connection()
        saved_jobs = conn.execute("""
            SELECT id, title, company, description, location,
                   salary_min, salary_max, score_total, priority
            FROM jobs
            WHERE status IN ('new', 'saved') AND is_archived = 0
            ORDER BY score_total DESC
        """).fetchall()
        conn.close()

        if not saved_jobs:
            st.warning("No saved jobs found. Go to Job Pool to discover and save jobs first.")
        else:
            job_options = {
                f"[{j['score_total'] or 0:.0f}] {j['title']} @ {j['company']}": j
                for j in saved_jobs
            }
            selected_label = st.selectbox("Select a job", options=list(job_options.keys()))
            if selected_label:
                selected_job = job_options[selected_label]
                jd_text = selected_job["description"] or ""
                company = selected_job["company"] or ""
                title = selected_job["title"] or ""
                selected_job_id = selected_job["id"]

                with st.expander("Job details", expanded=False):
                    st.write(f"**{title}** at **{company}**")
                    st.write(f"Location: {selected_job['location']}")
                    if selected_job["salary_min"] and selected_job["salary_max"]:
                        st.write(f"Salary: ${selected_job['salary_min']:,.0f} — ${selected_job['salary_max']:,.0f}")
    else:
        jd_text = st.text_area(
            "Paste the full job description",
            height=250,
            placeholder="Paste the complete job description here...",
        )
        col_c, col_t = st.columns(2)
        with col_c:
            company = st.text_input("Company name")
        with col_t:
            title = st.text_input("Job title")

    role_types = get_role_types()
    role_type = st.selectbox(
        "Target role type",
        options=list(role_types.keys()),
        format_func=lambda x: role_types[x],
    )

    # Resume tone
    tone_option = st.radio(
        "Resume Tone",
        ["Standard", "Accessible (for junior/mid roles)"],
        horizontal=True,
        help="Use 'Accessible' for Tier C jobs to avoid appearing overqualified",
    )
    tone = "accessible" if "Accessible" in tone_option else "standard"

    # Advanced options
    with st.expander("Advanced Options"):
        extra_instructions = st.text_area(
            "Custom instructions for AI",
            placeholder="e.g., Emphasize cloud experience, mention Tableau...",
            height=80,
        )
        hiring_manager = st.text_input("Hiring manager name", value="Hiring Manager")

    # Generate button
    can_generate = bool(jd_text and jd_text.strip() and company and title)
    generate_clicked = st.button(
        "⚡ Generate Resume & Cover Letter",
        type="primary",
        disabled=not can_generate,
        use_container_width=True,
    )

    if not can_generate:
        st.caption("Fill in the job description, company, and title to enable generation.")

# ─── RIGHT PANEL — Output ────────────────────────────────────────────
with right_col:
    # Always show ATS analysis if JD is present (even before generation)
    if jd_text and jd_text.strip():
        st.subheader("ATS Analysis")

        ats_result = score_ats(jd_text, profile)
        ats_score = ats_result["score"]

        # Score display with color
        if ats_score >= 80:
            score_color = "green"
            score_label = "EXCELLENT"
        elif ats_score >= 65:
            score_color = "orange"
            score_label = "GOOD"
        elif ats_score >= 50:
            score_color = "orange"
            score_label = "FAIR"
        else:
            score_color = "red"
            score_label = "LOW"

        score_col, detail_col = st.columns([1, 1])
        with score_col:
            st.metric("ATS Match Score", f"{ats_score:.0f}%")
            st.progress(min(ats_score / 100, 1.0))
            st.caption(f"Assessment: **:{score_color}[{score_label}]**")

        with detail_col:
            for cat, scores in ats_result["category_scores"].items():
                label = cat.replace("_", " ").title()
                st.caption(f"{label}: **{scores['matched']}/{scores['total']}** ({scores['percentage']}%)")

        # Missing keywords alert
        missing = ats_result["missing_keywords"]
        if missing:
            with st.expander(f"⚠️ Missing Keywords ({len(missing)})", expanded=True):
                missing_hard = [k for k in missing if k in {
                    "aws", "gcp", "azure", "snowflake", "tableau", "power bi",
                    "looker", "airflow", "dbt", "spark", "kubernetes", "terraform",
                    "docker", "mlflow", "sagemaker", "databricks", "bigquery",
                    "excel", "ci/cd", "scala", "java", "hadoop",
                }]
                missing_other = [k for k in missing if k not in missing_hard]

                if missing_hard:
                    st.markdown("**Critical (tools/platforms you may need):**")
                    st.write(", ".join(f"`{k}`" for k in missing_hard[:12]))
                if missing_other:
                    st.markdown("**Other missing keywords:**")
                    st.write(", ".join(f"`{k}`" for k in missing_other[:12]))

        # Save skill mentions if we have a job ID
        if selected_job_id:
            skills_for_db = extract_skills_for_db(jd_text, profile)
            save_skill_mentions(selected_job_id, skills_for_db)

    # ─── AI Generation ────────────────────────────────────────────────
    if generate_clicked and can_generate:
        st.markdown("---")
        st.subheader("Generated Application Materials")

        with st.spinner("Generating with Claude AI... (this takes 15-30 seconds)"):
            try:
                result = generate_application(
                    jd_text=jd_text,
                    company=company,
                    title=title,
                    role_type=role_type,
                    profile=profile,
                    extra_instructions=extra_instructions,
                    tone=tone,
                )

                # Validate for fabrication
                validation = validate_no_fabrication(result, profile)

                # Store in session state for persistence
                st.session_state["gen_result"] = result
                st.session_state["gen_company"] = company
                st.session_state["gen_title"] = title
                st.session_state["gen_ats"] = ats_result
                st.session_state["gen_validation"] = validation

                log_activity("generated_resume", job_id=selected_job_id,
                             details=f"Resume for {title} at {company}")

            except Exception as e:
                st.error(f"Generation failed: {e}")
                st.info("Make sure your `ANTHROPIC_API_KEY` is set in `.env`.")
                st.stop()

    # Display generated content (from session state if available)
    if "gen_result" in st.session_state:
        result = st.session_state["gen_result"]
        gen_company = st.session_state.get("gen_company", company)
        gen_title = st.session_state.get("gen_title", title)
        validation = st.session_state.get("gen_validation", {"warnings": []})

        st.markdown("---")

        # Show fabrication warnings
        if validation.get("warnings"):
            st.warning("Review these potentially fabricated claims before submitting:")
            for w in validation["warnings"]:
                st.write(f"- {w}")
            st.info("Please verify all numbers and claims match your real experience.")

        # Resume preview
        st.subheader("Resume Preview")
        with st.container(border=True):
            st.markdown(f"**{personal.get('name', '')}**")
            st.caption(
                f"{personal.get('location', '')} | {personal.get('email', '')} | "
                f"{personal.get('phone', '')}"
            )

            st.markdown("**Professional Summary**")
            st.write(result.get("summary", ""))

            st.markdown("**Technical Skills**")
            skills = result.get("skills", {})
            for cat, skill_list in skills.items():
                if skill_list:
                    label = cat.replace("_", " ").title()
                    st.markdown(f"*{label}:* {', '.join(skill_list)}")

            st.markdown("**Professional Experience**")
            for exp in result.get("experiences", []):
                st.markdown(f"**{exp.get('title', '')} — {exp.get('company', '')}**")
                loc = exp.get("location", "")
                dates = exp.get("dates", "")
                if loc or dates:
                    st.caption(f"{loc}{'  |  ' if loc and dates else ''}{dates}")
                for bullet in exp.get("bullets", []):
                    st.markdown(f"- {_highlight_unverified(bullet)}")

            st.markdown("**Education**")
            for edu in education:
                deg = edu.get("degree", "")
                inst = edu.get("institution", "")
                dates = edu.get("dates", "")
                st.markdown(f"**{deg}** — {inst} ({dates})")
                if edu.get("second_degree"):
                    st.markdown(f"**{edu['second_degree']}** — {inst}")

        # Cover letter preview
        cl = result.get("cover_letter", {})
        if cl:
            st.subheader("Cover Letter Preview")
            with st.container(border=True):
                for key in ["opening", "body_paragraph_1", "body_paragraph_2",
                            "body_paragraph_3", "closing"]:
                    text = cl.get(key, "")
                    if text:
                        st.markdown(_highlight_unverified(text))
                        st.write("")

        # Download buttons
        st.subheader("Downloads")
        dl_col1, dl_col2, dl_col3 = st.columns(3)

        with dl_col1:
            resume_buf = build_resume(result, personal, education)
            slug = gen_company.lower().replace(" ", "_")[:20]
            st.download_button(
                "📥 Download Resume (.docx)",
                data=resume_buf.getvalue(),
                file_name=f"Resume_{personal.get('name', 'resume').replace(' ', '')}_{slug}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        with dl_col2:
            if cl:
                cl_buf = build_cover_letter(
                    cl, personal, gen_company, gen_title,
                    hiring_manager=hiring_manager if 'hiring_manager' in dir() else "Hiring Manager",
                )
                st.download_button(
                    "📥 Download Cover Letter (.docx)",
                    data=cl_buf.getvalue(),
                    file_name=f"CoverLetter_{personal.get('name', 'cl').replace(' ', '')}_{slug}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

        with dl_col3:
            if "gen_ats" in st.session_state:
                ats = st.session_state["gen_ats"]
                report_lines = [
                    f"ATS MATCH REPORT — {gen_title} at {gen_company}",
                    f"Score: {ats['score']}%",
                    "",
                    f"Matched ({len(ats['matched_keywords'])}):",
                    ", ".join(ats["matched_keywords"]),
                    "",
                    f"Missing ({len(ats['missing_keywords'])}):",
                    ", ".join(ats["missing_keywords"]),
                ]
                st.download_button(
                    "📥 Download ATS Report (.txt)",
                    data="\n".join(report_lines),
                    file_name=f"ATS_Report_{slug}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

        # Mark job as applied if selected from DB
        if selected_job_id:
            st.markdown("---")
            if st.button("✅ Mark as Applied", use_container_width=True):
                conn = get_connection()
                conn.execute(
                    "UPDATE jobs SET status = 'applied', date_applied = date('now') WHERE id = ?",
                    (selected_job_id,),
                )
                conn.commit()
                conn.close()
                log_activity("applied", job_id=selected_job_id,
                             details=f"Applied to {gen_title} at {gen_company}")
                st.success(f"Marked **{gen_title} at {gen_company}** as applied!")
