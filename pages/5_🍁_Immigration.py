"""
Page 5: Immigration — BC PNP Tech eligibility tracker.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.db import get_connection, init_db
from core.immigration import (
    BCPNP_TECH_NOCS,
    NOC_DESCRIPTIONS,
    BC_MEDIAN_HOURLY_WAGE,
    salary_to_annual,
    salary_above_median,
)

init_db()

st.set_page_config(page_title="Immigration — JobPilot", page_icon="🍁", layout="wide")
st.title("🍁 Immigration Pathway Tracker")

st.markdown("**Your Target:** BC PNP Tech → Express Entry (EEBC)")
st.markdown("---")


# ─── Load job data ───────────────────────────────────────────────────
conn = get_connection()
df = pd.read_sql_query("""
    SELECT id, title, company, location, noc_code, noc_description,
           bcpnp_eligible, salary_min, salary_max, salary_interval,
           score_total, priority, status
    FROM jobs
    WHERE is_archived = 0
""", conn)
conn.close()

if df.empty:
    st.warning("No jobs in database. Go to Job Pool to add jobs first.")
    st.stop()

total_jobs = len(df)


# ─── BC PNP Eligible Stats ───────────────────────────────────────────
pnp_eligible = df[df["bcpnp_eligible"] == 1]
pnp_count = len(pnp_eligible)
pnp_pct = round(pnp_count / total_jobs * 100, 1) if total_jobs > 0 else 0

st.subheader("BC PNP Tech Eligibility Overview")

m1, m2, m3 = st.columns(3)
m1.metric("Total Jobs", total_jobs)
m2.metric("BC PNP Eligible", f"{pnp_count} ({pnp_pct}%)")
m3.metric("Not Eligible / Unknown", total_jobs - pnp_count)

st.markdown("---")


# ─── NOC Distribution ────────────────────────────────────────────────
st.subheader("NOC Distribution of Jobs")

noc_df = df[df["noc_code"].notna() & (df["noc_code"] != "")].copy()

if not noc_df.empty:
    noc_df["noc_label"] = noc_df.apply(
        lambda r: f"{r['noc_code']} — {r['noc_description']}" if r["noc_description"] else r["noc_code"],
        axis=1,
    )
    noc_counts = noc_df["noc_label"].value_counts().reset_index()
    noc_counts.columns = ["NOC", "Count"]

    chart_left, chart_right = st.columns(2)

    with chart_left:
        fig = px.pie(
            noc_counts, names="NOC", values="Count",
            title="NOC Code Distribution",
            hole=0.3,
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with chart_right:
        # Mark which NOCs are in PNP Tech
        noc_counts["PNP Tech"] = noc_counts["NOC"].apply(
            lambda x: "Yes" if any(noc in x for noc in BCPNP_TECH_NOCS) else "No"
        )
        fig = px.bar(
            noc_counts, x="NOC", y="Count", color="PNP Tech",
            title="Jobs by NOC Code",
            color_discrete_map={"Yes": "#4CAF50", "No": "#FF9800"},
        )
        fig.update_layout(xaxis_tickangle=-30, height=400)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No NOC codes assigned to jobs yet.")

st.markdown("---")


# ─── Salary vs PNP Threshold ─────────────────────────────────────────
st.subheader("Salary vs BC Median Wage Threshold")

median_annual = BC_MEDIAN_HOURLY_WAGE * 2080  # ~$80K

salary_df = df[(df["salary_min"].notna()) | (df["salary_max"].notna())].copy()

if not salary_df.empty:
    def calc_annual(row):
        s_min = row["salary_min"] or 0
        s_max = row["salary_max"] or 0
        mid = (s_min + s_max) / 2 if s_min and s_max else s_min or s_max
        return salary_to_annual(mid, row.get("salary_interval", "yearly"))

    salary_df["annual_salary"] = salary_df.apply(calc_annual, axis=1)
    salary_df["above_median"] = salary_df["annual_salary"].apply(
        lambda s: "Above Median" if s >= median_annual else "Below Median"
    )

    above_count = len(salary_df[salary_df["annual_salary"] >= median_annual])
    below_count = len(salary_df) - above_count

    s1, s2 = st.columns(2)
    s1.metric("Above Median Wage", f"{above_count} jobs",
              help=f"BC median: ${BC_MEDIAN_HOURLY_WAGE}/hr (${median_annual:,.0f}/yr)")
    s2.metric("Below Median Wage", f"{below_count} jobs")

    # Salary distribution chart
    salary_df["label"] = salary_df.apply(
        lambda r: f"{r['title'][:25]}\n{r['company'][:20]}", axis=1
    )
    salary_df = salary_df.sort_values("annual_salary", ascending=True)

    fig = px.bar(
        salary_df,
        x="annual_salary",
        y="label",
        color="above_median",
        orientation="h",
        title="Job Salaries vs BC Median Wage",
        labels={"annual_salary": "Annual Salary (CAD)", "label": "Job"},
        color_discrete_map={"Above Median": "#4CAF50", "Below Median": "#FF9800"},
    )
    fig.add_vline(
        x=median_annual, line_dash="dash", line_color="red",
        annotation_text=f"BC Median: ${median_annual:,.0f}",
    )
    fig.update_layout(height=max(300, len(salary_df) * 30))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No salary data available.")

st.markdown("---")


# ─── Requirements Checklist ──────────────────────────────────────────
st.subheader("BC PNP Tech Requirements Checklist")

checks = [
    ("Job in BC PNP Tech priority occupation",
     pnp_count > 0,
     f"{pnp_count} eligible jobs found"),
    ("Full-time, indeterminate job offer",
     None,
     "Verify with employer — must be full-time, permanent"),
    ("Employer registered with BC PNP",
     None,
     "Check with employer during interview stage"),
    ("Meet education requirements (M.S. + B.S.)",
     True,
     "M.S. Computer Science (NYIT Vancouver) + B.S. Mathematics (Peking University)"),
    ("Meet language requirements (CLB 7+)",
     True,
     "Bilingual English/Mandarin — take IELTS if not already done"),
    ("2+ years relevant experience",
     True,
     "10+ years of experience in data science, consulting, and tech"),
    ("Salary above BC median wage",
     above_count > 0 if not salary_df.empty else None,
     f"{above_count} jobs above ${median_annual:,.0f}/yr threshold" if not salary_df.empty else "No salary data"),
]

for label, status, detail in checks:
    if status is True:
        st.markdown(f"✅ **{label}**")
        st.caption(f"   {detail}")
    elif status is False:
        st.markdown(f"❌ **{label}**")
        st.caption(f"   {detail}")
    else:
        st.markdown(f"⬜ **{label}**")
        st.caption(f"   {detail}")

st.markdown("---")


# ─── BC PNP Tech NOC Reference ───────────────────────────────────────
with st.expander("BC PNP Tech Priority Occupations (2025-2026)"):
    noc_ref = []
    for noc in sorted(BCPNP_TECH_NOCS):
        desc = NOC_DESCRIPTIONS.get(noc, "")
        in_jobs = len(df[df["noc_code"] == noc])
        noc_ref.append({
            "NOC Code": noc,
            "Description": desc,
            "Jobs Found": in_jobs,
        })
    st.dataframe(pd.DataFrame(noc_ref), use_container_width=True, hide_index=True)
