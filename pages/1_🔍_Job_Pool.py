"""
Page 1: Job Pool — Discover, score, and browse job opportunities.
"""

import json
import pandas as pd
import streamlit as st
import urllib.parse

from core.db import get_connection, init_db, log_activity
from core.networking import generate_networking_intel, TEMPLATES

init_db()

st.set_page_config(page_title="Job Pool — JobPilot", page_icon="🔍", layout="wide")
st.title("🔍 Job Pool")


# ─── Refresh / Scrape button ─────────────────────────────────────────
header_left, header_right = st.columns([3, 1])
with header_right:
    refresh_btn = st.button("🔄 Refresh Jobs", use_container_width=True)
    load_sample_btn = st.button("📂 Load Sample Data", use_container_width=True)

if refresh_btn:
    with st.spinner("Scraping jobs from job boards... This may take a few minutes."):
        try:
            from core.scraper import scrape_and_rank
            messages = []
            result = scrape_and_rank(progress_callback=lambda m: messages.append(m))
            for msg in messages:
                st.caption(msg)
            st.success(
                f"Done! Scraped {result['total_scraped']} jobs, "
                f"{result['new_inserted']} new added (total: {result['total_in_db']})"
            )
            st.rerun()
        except ImportError:
            st.error("python-jobspy not installed. Run: `pip install python-jobspy`")
        except Exception as e:
            st.error(f"Scraping failed: {e}")

if load_sample_btn:
    from core.scraper import load_sample_data
    count = load_sample_data()
    if count > 0:
        st.success(f"Loaded {count} sample jobs!")
    else:
        st.info("Sample data already loaded or file not found.")
    st.rerun()


# ─── Load jobs from DB ───────────────────────────────────────────────
conn = get_connection()
df = pd.read_sql_query("""
    SELECT id, title, company, location, description,
           salary_min, salary_max, salary_interval,
           score_skills, score_immigration, score_salary,
           score_company, score_success, score_total,
           score_interview, interview_format_details,
           priority, noc_code, noc_description, bcpnp_eligible,
           status, date_scraped, search_query, job_url, notes,
           tier, networking_score, networking_notes, success_details
    FROM jobs
    WHERE is_archived = 0
    ORDER BY score_total DESC
""", conn)
conn.close()

if df.empty:
    st.info("No jobs in the database. Click **Refresh Jobs** to scrape or **Load Sample Data** to test.")
    st.stop()

# Fill NaN values
df["tier"] = df["tier"].fillna("B")
df["score_interview"] = df["score_interview"].fillna(50)


# ─── KPI Bar with Tier Distribution ──────────────────────────────────
total = len(df)
tier_a = len(df[df["tier"] == "A"])
tier_b = len(df[df["tier"] == "B"])
tier_c = len(df[df["tier"] == "C"])
pnp_count = len(df[df["bcpnp_eligible"] == 1])
avg_score = df["score_total"].mean()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("🎯 Tier A", tier_a)
k2.metric("✅ Tier B", tier_b)
k3.metric("🟢 Tier C", tier_c)
k4.metric("Total Jobs", total)
k5.metric("BC PNP", pnp_count)
k6.metric("Avg Score", f"{avg_score:.0f}")


# ─── Weekly Application Plan (Change 7) ──────────────────────────────
with st.container(border=True):
    st.markdown("**📋 Recommended Weekly Application Plan:**")
    plan_cols = st.columns(3)
    with plan_cols[0]:
        st.markdown(
            "🎯 **Tier A — Stretch (2-3/week)**\n\n"
            "Senior DS at big tech\n\n"
            "Strategy: Network first, apply only with referral. "
            "These likely have live coding — only apply if you find a champion."
        )
    with plan_cols[1]:
        st.markdown(
            "✅ **Tier B — Sweet Spot (5-7/week)**\n\n"
            "Mid-level DA/DS at mid-size companies, PM roles\n\n"
            "Strategy: Generate tailored resume + cover letter, apply directly. "
            "Check Glassdoor for interview format before applying."
        )
    with plan_cols[2]:
        st.markdown(
            "🟢 **Tier C — Quick Win (3-5/week)**\n\n"
            "BA, Consultant, junior DA, contract roles\n\n"
            "Strategy: Fast applications, use \"Accessible\" resume tone. "
            "These rarely have live coding — highest interview probability."
        )
    st.caption(
        "💡 Pro Tip: For Tier B, always check Glassdoor interview reviews first. "
        "If the company uses take-home case studies, it's effectively a Tier C for you."
    )

st.markdown("---")


# ─── Role Type Quick Filter (Change 5) ───────────────────────────────
ROLE_CATEGORIES = {
    "Data Scientist": ["data scientist", "applied scientist", "research scientist"],
    "Data Analyst": ["data analyst", "analytics engineer"],
    "Product Manager": ["product manager", "program manager", "technical product manager"],
    "Business Analyst": ["business analyst", "systems analyst"],
    "Consultant": ["consultant", "management consultant", "strategy consultant"],
    "Analytics Manager": ["analytics manager", "analytics lead", "analytics director", "insights"],
    "BI Analyst": ["bi analyst", "business intelligence"],
    "Other": [],
}

role_filter = st.multiselect(
    "Target Roles",
    options=list(ROLE_CATEGORIES.keys()),
    default=list(ROLE_CATEGORIES.keys()),
    help="Select which role types to show",
)


# ─── Sidebar Filters ─────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # Tier filter
    tiers = sorted(df["tier"].dropna().unique().tolist())
    tier_labels = {"A": "🎯 A (Stretch)", "B": "✅ B (Sweet Spot)", "C": "🟢 C (Quick Win)"}
    selected_tiers = st.multiselect(
        "Tier",
        tiers,
        default=tiers,
        format_func=lambda x: tier_labels.get(x, x),
    )

    # Interview Format Filter (Change 4)
    interview_filter = st.select_slider(
        "Interview Coding Risk",
        options=["All", "Low Risk Only", "No Live Coding"],
        value="All",
        help="Filter jobs by likelihood of live coding in interviews",
    )

    # Priority filter
    priorities = sorted(df["priority"].dropna().unique().tolist())
    selected_priorities = st.multiselect("Priority", priorities, default=priorities)

    # Status filter
    statuses = sorted(df["status"].dropna().unique().tolist())
    selected_statuses = st.multiselect("Status", statuses, default=statuses)

    # Min score sliders
    min_score = st.slider("Min Total Score", 0, 100,
                          value=0, step=5)
    min_success = st.slider("Min Success Score", 0, 100,
                            value=0, step=5)
    min_interview = st.slider("Min Interview Score", 0, 100,
                              value=0, step=5)

    # BC PNP only
    pnp_only = st.checkbox("BC PNP Eligible Only")

    # Company filter
    companies = sorted(df["company"].dropna().unique().tolist())
    selected_companies = st.multiselect("Company", companies, default=[])

    # Exclude keywords from titles
    DEFAULT_EXCLUDE = "senior, lead, principal, head, staff, director, vp, engineer, software, programming, architect, devops, sre, platform"
    if "exclude_keywords" not in st.session_state:
        st.session_state["exclude_keywords"] = DEFAULT_EXCLUDE
    exclude_input = st.text_input(
        "🚫 Exclude Keywords",
        value=st.session_state["exclude_keywords"],
        help="Comma-separated keywords. Jobs whose title contains ANY of these are hidden.",
        key="exclude_kw_input",
    )
    st.session_state["exclude_keywords"] = exclude_input

    # Search text
    search_query = st.text_input("Search (title/company/description)")


# ─── Apply Filters ───────────────────────────────────────────────────
filtered = df.copy()

if selected_tiers:
    filtered = filtered[filtered["tier"].isin(selected_tiers)]

# Interview format filter (Change 4)
if interview_filter == "Low Risk Only":
    filtered = filtered[filtered["score_interview"] >= 50]
elif interview_filter == "No Live Coding":
    filtered = filtered[filtered["score_interview"] >= 70]

# Role type filter (Change 5)
if role_filter and "Other" not in role_filter:
    # Gather all keywords for selected role categories
    role_keywords = []
    for role_name in role_filter:
        role_keywords.extend(ROLE_CATEGORIES.get(role_name, []))
    if role_keywords:
        mask = filtered["title"].str.lower().apply(
            lambda t: any(kw in t for kw in role_keywords)
        )
        filtered = filtered[mask]
elif role_filter and "Other" in role_filter and len(role_filter) == 1:
    # Only "Other" selected — show jobs that don't match any category
    all_keywords = []
    for kws in ROLE_CATEGORIES.values():
        all_keywords.extend(kws)
    if all_keywords:
        mask = filtered["title"].str.lower().apply(
            lambda t: not any(kw in t for kw in all_keywords)
        )
        filtered = filtered[mask]

if selected_priorities:
    filtered = filtered[filtered["priority"].isin(selected_priorities)]
if selected_statuses:
    filtered = filtered[filtered["status"].isin(selected_statuses)]
if min_score > 0:
    filtered = filtered[filtered["score_total"] >= min_score]
if min_success > 0:
    filtered = filtered[filtered["score_success"] >= min_success]
if min_interview > 0:
    filtered = filtered[filtered["score_interview"] >= min_interview]
if pnp_only:
    filtered = filtered[filtered["bcpnp_eligible"] == 1]
if selected_companies:
    filtered = filtered[filtered["company"].isin(selected_companies)]
if search_query:
    q = search_query.lower()
    filtered = filtered[
        filtered["title"].str.lower().str.contains(q, na=False) |
        filtered["company"].str.lower().str.contains(q, na=False) |
        filtered["description"].str.lower().str.contains(q, na=False)
    ]

# Exclude keywords filter
if exclude_input.strip():
    exclude_kws = [kw.strip().lower() for kw in exclude_input.split(",") if kw.strip()]
    if exclude_kws:
        filtered = filtered[~filtered["title"].str.lower().apply(
            lambda t: any(kw in t for kw in exclude_kws)
        )]

st.caption(f"Showing {len(filtered)} of {total} jobs")


# ─── Job Table ────────────────────────────────────────────────────────
display_df = filtered[[
    "score_total", "tier", "title", "company", "location",
    "score_skills", "score_interview", "score_success",
    "bcpnp_eligible", "status",
]].copy()

display_df.columns = [
    "Score", "Tier", "Title", "Company", "Location",
    "Skills", "Interview", "Success",
    "PNP", "Status",
]

# Format PNP column
display_df["PNP"] = display_df["PNP"].map({1: "Yes", 0: "—"})

# Tier with emoji
tier_display = {"A": "🎯 A", "B": "✅ B", "C": "🟢 C"}
display_df["Tier"] = display_df["Tier"].map(tier_display).fillna(display_df["Tier"])

st.dataframe(
    display_df,
    use_container_width=True,
    height=400,
    column_config={
        "Score": st.column_config.NumberColumn(format="%.0f"),
        "Skills": st.column_config.NumberColumn(format="%.0f"),
        "Interview": st.column_config.NumberColumn(format="%.0f"),
        "Success": st.column_config.NumberColumn(format="%.0f"),
    },
)


# ─── Job Detail Panel ────────────────────────────────────────────────
st.markdown("---")
st.subheader("Job Details")

job_options = {
    f"[{r['score_total']:.0f}] [{r['tier']}] {r['title']} @ {r['company']}": r["id"]
    for _, r in filtered.iterrows()
}

if not job_options:
    st.info("No jobs match your filters.")
    st.stop()

selected_label = st.selectbox("Select a job to view details", options=list(job_options.keys()))
selected_id = job_options[selected_label]

# Fetch full job record
conn = get_connection()
job = conn.execute("SELECT * FROM jobs WHERE id = ?", (selected_id,)).fetchone()
conn.close()

if job:
    detail_left, detail_right = st.columns([1.5, 1])

    with detail_left:
        # Tier badge
        tier_val = job["tier"] or "B"
        tier_badges = {
            "A": "🎯 **Tier A — Stretch** (focus on networking + referrals)",
            "B": "✅ **Tier B — Sweet Spot** (primary target, apply directly)",
            "C": "🟢 **Tier C — Quick Win** (fast application, build momentum)",
        }
        st.markdown(tier_badges.get(tier_val, f"Tier {tier_val}"))

        st.markdown(f"### {job['title']}")
        st.markdown(f"**{job['company']}** — {job['location']}")

        if job["salary_min"] and job["salary_max"]:
            st.markdown(
                f"💰 ${job['salary_min']:,.0f} — ${job['salary_max']:,.0f} "
                f"({job['salary_interval'] or 'yearly'})"
            )

        if job["noc_code"]:
            pnp_badge = "✅" if job["bcpnp_eligible"] else "❓"
            st.markdown(f"🍁 NOC: {job['noc_code']} ({job['noc_description']}) {pnp_badge}")

        st.markdown(f"**Status:** {job['status']} | **Scraped:** {job['date_scraped']}")

        if job["job_url"]:
            st.markdown(f"[🔗 View Original Posting]({job['job_url']})")

        with st.expander("Full Description", expanded=False):
            st.write(job["description"] or "No description available.")

    with detail_right:
        st.markdown("**Score Breakdown**")
        scores = {
            "Skills (30%)": job["score_skills"],
            "Immigration (25%)": job["score_immigration"],
            "Interview (15%)": job["score_interview"],
            "Salary (10%)": job["score_salary"],
            "Company (10%)": job["score_company"],
            "Success (10%)": job["score_success"],
        }
        for label, score_val in scores.items():
            if score_val is not None:
                st.progress(score_val / 100, text=f"{label}: {score_val:.0f}")
            else:
                st.caption(f"{label}: N/A")

        st.metric("Total Score", f"{job['score_total']:.0f}" if job['score_total'] else "N/A")

        # Interview format assessment
        interview_score = job["score_interview"] or 50
        if interview_score >= 80:
            st.success("🟢 Likely no live coding")
        elif interview_score >= 50:
            st.warning("🟡 Format unknown — check Glassdoor")
        else:
            st.error("🔴 Likely has live coding")

        # Glassdoor interview search link
        company_name = job["company"] or ""
        company_encoded = urllib.parse.quote(company_name)
        glassdoor_url = (
            f"https://www.glassdoor.ca/Interview/"
            f"{company_encoded}-interview-questions-SRCH_KE0,{len(company_name)}.htm"
        )
        st.link_button("🔍 Check interview format on Glassdoor", glassdoor_url)

        # Interview format details
        interview_details_raw = job["interview_format_details"] if job["interview_format_details"] else "{}"
        try:
            interview_details = json.loads(interview_details_raw)
        except (json.JSONDecodeError, TypeError):
            interview_details = {}

        if interview_details:
            with st.expander("🎤 Interview Format Breakdown", expanded=False):
                for key, detail in interview_details.items():
                    st.caption(f"• {key.replace('_', ' ').title()}: {detail}")

        # Success score details
        success_details_raw = job["success_details"] if job["success_details"] else "{}"
        try:
            success_details = json.loads(success_details_raw)
        except (json.JSONDecodeError, TypeError):
            success_details = {}

        if success_details:
            with st.expander("📊 Success Score Breakdown", expanded=False):
                st.caption("Base: 40 points")
                for key, detail in success_details.items():
                    st.caption(f"• {key.replace('_', ' ').title()}: {detail}")

    # ─── Networking Section ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("🤝 Networking Intelligence")

    net_intel = generate_networking_intel(company_name)

    net_score = net_intel["networking_score"]
    if net_score >= 8:
        st.markdown(f"**Networking Score:** +{net_score} (company known to have international talent)")
    elif net_score >= 4:
        st.markdown(f"**Networking Score:** +{net_score} (moderate networking potential)")
    else:
        st.markdown(f"**Networking Score:** +{net_score} (limited known connections, still worth trying)")

    st.markdown("**🔗 Find Connections:**")
    link_cols = st.columns(3)
    for i, search in enumerate(net_intel["search_urls"]):
        with link_cols[i % 3]:
            st.link_button(
                search["label"],
                search["url"],
                use_container_width=True,
            )
            st.caption(search["why"])

    with st.expander("💡 Networking Tips"):
        for tip in net_intel["networking_tips"]:
            st.write(tip)

    with st.expander("📝 Connection Request Templates"):
        for template_name, template_text in TEMPLATES.items():
            label = template_name.replace("_", " ").title()
            st.markdown(f"**{label}:**")
            st.code(
                template_text.format(
                    name="[Name]",
                    company=company_name,
                    job_title=job["title"] or "[Job Title]",
                ),
                language=None,
            )

    # Action buttons
    st.markdown("---")
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

    with btn_col1:
        if job["status"] != "saved":
            if st.button("💾 Save", key="save_btn", use_container_width=True):
                conn = get_connection()
                conn.execute("UPDATE jobs SET status = 'saved' WHERE id = ?", (selected_id,))
                conn.commit()
                conn.close()
                log_activity("saved", job_id=selected_id)
                st.success("Job saved!")
                st.rerun()
        else:
            st.button("💾 Saved", disabled=True, use_container_width=True)

    with btn_col2:
        if st.button("📝 Generate Resume", key="gen_btn", use_container_width=True):
            st.switch_page("pages/2_📝_Apply.py")

    with btn_col3:
        if st.button("🗑️ Archive", key="archive_btn", use_container_width=True):
            conn = get_connection()
            conn.execute("UPDATE jobs SET is_archived = 1 WHERE id = ?", (selected_id,))
            conn.commit()
            conn.close()
            log_activity("archived", job_id=selected_id)
            st.success("Job archived!")
            st.rerun()

    with btn_col4:
        notes = st.text_input("Notes", value=job["notes"] or "", key="notes_input")
        if notes != (job["notes"] or ""):
            conn = get_connection()
            conn.execute("UPDATE jobs SET notes = ? WHERE id = ?", (notes, selected_id))
            conn.commit()
            conn.close()
