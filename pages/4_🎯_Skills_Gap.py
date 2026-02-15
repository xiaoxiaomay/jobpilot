"""
Page 4: Skills Gap — Aggregate skill gap analysis across all analyzed JDs.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.db import get_connection, init_db
from core.skills_analyzer import analyze_gaps
from core.ats_scorer import extract_skills_for_db, load_profile

init_db()

st.set_page_config(page_title="Skills Gap — JobPilot", page_icon="🎯", layout="wide")
st.title("🎯 Skills Gap Analysis")


# ─── Populate skill_mentions if empty ─────────────────────────────────
conn = get_connection()
mention_count = conn.execute("SELECT COUNT(*) FROM skill_mentions").fetchone()[0]
conn.close()

if mention_count == 0:
    st.info("Analyzing job descriptions to build skill data...")
    conn = get_connection()
    jobs = conn.execute(
        "SELECT id, description FROM jobs WHERE description IS NOT NULL AND description != ''"
    ).fetchall()
    conn.close()

    if jobs:
        try:
            profile = load_profile()
        except FileNotFoundError:
            st.error("Master profile not found.")
            st.stop()

        from core.skills_analyzer import save_skill_mentions
        for job in jobs:
            skills = extract_skills_for_db(job["description"], profile)
            save_skill_mentions(job["id"], skills)
        st.success(f"Analyzed {len(jobs)} job descriptions.")
        st.rerun()
    else:
        st.warning("No jobs with descriptions found. Go to Job Pool to add jobs first.")
        st.stop()


# ─── Run gap analysis ────────────────────────────────────────────────
gaps = analyze_gaps()

if gaps["total_jobs_analyzed"] == 0:
    st.warning("No skill data available yet. Analyze some job descriptions first.")
    st.stop()

st.markdown(f"**Based on {gaps['total_jobs_analyzed']} job descriptions analyzed:**")
st.markdown("---")


# ─── Layout ──────────────────────────────────────────────────────────
left_col, right_col = st.columns(2)


# ─── Missing Skills ──────────────────────────────────────────────────
with left_col:
    st.subheader("Most Frequently Missing Skills")

    missing = gaps["missing_skills"]
    if missing:
        for i, skill_info in enumerate(missing[:15], 1):
            freq = skill_info["frequency"]
            total = gaps["total_jobs_analyzed"]
            pct = skill_info["pct"]
            st.markdown(
                f"**{i}.** `{skill_info['skill']}` — "
                f"mentioned in {freq}/{total} JDs ({pct}%) ❌"
            )
    else:
        st.success("No significant skill gaps found!")


# ─── Strong Skills ───────────────────────────────────────────────────
with right_col:
    st.subheader("Your Strongest Matches")

    strong = gaps["strong_skills"]
    if strong:
        for i, skill_info in enumerate(strong[:15], 1):
            freq = skill_info["frequency"]
            total = gaps["total_jobs_analyzed"]
            pct = skill_info["pct"]
            st.markdown(
                f"**{i}.** `{skill_info['skill']}` — "
                f"matched in {freq}/{total} JDs ({pct}%) ✅"
            )

st.markdown("---")


# ─── Recommendations ─────────────────────────────────────────────────
st.subheader("Recommended Learning Priorities")

if gaps["recommendations"]:
    for rec in gaps["recommendations"]:
        st.markdown(f"- {rec}")

st.markdown("---")


# ─── Priority Chart (frequency x gap) ────────────────────────────────
st.subheader("Skill Priority Chart")

if missing:
    missing_df = pd.DataFrame(missing[:20])
    fig = px.bar(
        missing_df,
        x="skill",
        y="frequency",
        color="category",
        title="Missing Skills by Frequency",
        labels={"skill": "Skill", "frequency": "# of JDs mentioning", "category": "Category"},
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─── Category Radar Chart ────────────────────────────────────────────
st.subheader("Skill Category Coverage")

cat_breakdown = gaps["category_breakdown"]
if cat_breakdown:
    categories = []
    has_pcts = []
    for cat, data in cat_breakdown.items():
        total = data["has"] + data["missing"]
        if total > 0:
            categories.append(cat.replace("_", " ").title())
            has_pcts.append(round(data["has"] / total * 100, 1))

    if categories:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=has_pcts,
            theta=categories,
            fill='toself',
            name='Your Coverage',
            line_color='#2196F3',
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100]),
            ),
            showlegend=False,
            title="Skill Coverage by Category (%)",
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)


# ─── Detailed Category Table ─────────────────────────────────────────
with st.expander("Detailed Category Breakdown"):
    if cat_breakdown:
        rows = []
        for cat, data in cat_breakdown.items():
            total = data["has"] + data["missing"]
            pct = round(data["has"] / total * 100, 1) if total > 0 else 0
            rows.append({
                "Category": cat.replace("_", " ").title(),
                "Skills You Have": data["has"],
                "Skills Missing": data["missing"],
                "Total Mentions": total,
                "Coverage %": pct,
            })
        st.dataframe(
            pd.DataFrame(rows).sort_values("Coverage %", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# ─── Re-analyze button ───────────────────────────────────────────────
st.markdown("---")
if st.button("🔄 Re-analyze All Jobs"):
    conn = get_connection()
    conn.execute("DELETE FROM skill_mentions")
    conn.commit()
    conn.close()
    st.rerun()
