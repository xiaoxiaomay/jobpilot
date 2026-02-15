"""
Page 3: Tracker — Application progress tracking and weekly activity.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

from core.db import get_connection, init_db, log_activity

init_db()

st.set_page_config(page_title="Tracker — JobPilot", page_icon="📊", layout="wide")
st.title("📊 Application Tracker")

STATUS_OPTIONS = ["new", "saved", "applied", "interviewing", "rejected", "offer", "withdrawn"]
STATUS_PIPELINE = ["saved", "applied", "interviewing", "offer"]


# ─── Pipeline Summary ────────────────────────────────────────────────
conn = get_connection()
status_counts = {}
for s in STATUS_OPTIONS:
    count = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = ?", (s,)).fetchone()[0]
    status_counts[s] = count

# Response rate
applied_count = status_counts.get("applied", 0) + status_counts.get("interviewing", 0) + status_counts.get("offer", 0) + status_counts.get("rejected", 0)
responded_count = status_counts.get("interviewing", 0) + status_counts.get("offer", 0) + status_counts.get("rejected", 0)
response_rate = round(responded_count / applied_count * 100, 1) if applied_count > 0 else 0

# Avg days to response
avg_response = conn.execute("""
    SELECT AVG(JULIANDAY(date_response) - JULIANDAY(date_applied))
    FROM jobs WHERE date_applied IS NOT NULL AND date_response IS NOT NULL
""").fetchone()[0]
conn.close()

st.subheader("Pipeline")

# Pipeline visualization
pipeline_cols = st.columns(len(STATUS_PIPELINE) + 1)
for i, status in enumerate(STATUS_PIPELINE):
    with pipeline_cols[i]:
        count = status_counts.get(status, 0)
        st.metric(status.title(), count)

with pipeline_cols[-1]:
    st.metric("Response Rate", f"{response_rate}%")

st.caption(
    f"Avg days to response: {avg_response:.0f}" if avg_response else "Avg days to response: N/A"
)

st.markdown("---")


# ─── Weekly Activity Targets ─────────────────────────────────────────
st.subheader("This Week's Activity")

# Get current week's Monday
today = datetime.now()
monday = today - timedelta(days=today.weekday())
week_start = monday.strftime("%Y-%m-%d")

conn = get_connection()
# Count this week's applications
week_applied = conn.execute("""
    SELECT COUNT(*) FROM jobs
    WHERE date_applied >= ? AND status IN ('applied', 'interviewing', 'offer')
""", (week_start,)).fetchone()[0]

week_interviews = conn.execute("""
    SELECT COUNT(*) FROM jobs
    WHERE status = 'interviewing' AND date_applied >= ?
""", (week_start,)).fetchone()[0]

# Check for existing weekly target record
weekly = conn.execute(
    "SELECT * FROM weekly_targets WHERE week_start = ?", (week_start,)
).fetchone()
conn.close()

# Targets (configurable)
with st.expander("Set Weekly Targets"):
    target_apps = st.number_input("Application target", value=10, min_value=1, max_value=50)
    target_interviews = st.number_input("Interview target", value=3, min_value=1, max_value=20)
    target_networking = st.number_input("Networking target", value=5, min_value=1, max_value=20)

act_col1, act_col2, act_col3 = st.columns(3)

with act_col1:
    pct = min(week_applied / target_apps, 1.0) if target_apps > 0 else 0
    st.metric("Applications", f"{week_applied}/{target_apps}")
    st.progress(pct)

with act_col2:
    pct = min(week_interviews / target_interviews, 1.0) if target_interviews > 0 else 0
    st.metric("Interviews", f"{week_interviews}/{target_interviews}")
    st.progress(pct)

with act_col3:
    networking = 0  # TODO: could track via activity log
    pct = min(networking / target_networking, 1.0) if target_networking > 0 else 0
    st.metric("Networking", f"{networking}/{target_networking}")
    st.progress(pct)

st.markdown("---")


# ─── Application Table (editable) ────────────────────────────────────
st.subheader("Applications")

conn = get_connection()
apps_df = pd.read_sql_query("""
    SELECT id, title, company, location, status, date_applied,
           date_response, ats_score, score_total, priority, notes, job_url
    FROM jobs
    WHERE status NOT IN ('new') AND is_archived = 0
    ORDER BY
        CASE status
            WHEN 'offer' THEN 1
            WHEN 'interviewing' THEN 2
            WHEN 'applied' THEN 3
            WHEN 'saved' THEN 4
            WHEN 'rejected' THEN 5
            WHEN 'withdrawn' THEN 6
        END,
        date_applied DESC
""", conn)
conn.close()

if apps_df.empty:
    st.info(
        "No applications tracked yet. "
        "Save jobs from the Job Pool or apply from the Apply page to start tracking."
    )
else:
    # Show editable table for status updates
    for idx, row in apps_df.iterrows():
        with st.container(border=True):
            cols = st.columns([2, 2, 1.5, 1, 1, 2])
            with cols[0]:
                st.markdown(f"**{row['title']}**")
                st.caption(row["company"])
            with cols[1]:
                st.caption(f"📍 {row['location']}")
                if row["date_applied"]:
                    st.caption(f"Applied: {row['date_applied']}")
            with cols[2]:
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(row["status"]) if row["status"] in STATUS_OPTIONS else 0,
                    key=f"status_{row['id']}",
                    label_visibility="collapsed",
                )
                if new_status != row["status"]:
                    conn = get_connection()
                    updates = {"status": new_status}
                    if new_status == "applied" and not row["date_applied"]:
                        updates["date_applied"] = datetime.now().strftime("%Y-%m-%d")
                    if new_status in ("interviewing", "rejected", "offer"):
                        updates["date_response"] = datetime.now().strftime("%Y-%m-%d")

                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    conn.execute(
                        f"UPDATE jobs SET {set_clause} WHERE id = ?",
                        list(updates.values()) + [row["id"]],
                    )
                    conn.commit()
                    conn.close()
                    log_activity(f"status_changed_to_{new_status}", job_id=row["id"])
                    st.rerun()

            with cols[3]:
                if row["score_total"]:
                    st.metric("Score", f"{row['score_total']:.0f}", label_visibility="collapsed")
            with cols[4]:
                if row["ats_score"]:
                    st.metric("ATS", f"{row['ats_score']:.0f}%", label_visibility="collapsed")
            with cols[5]:
                note = st.text_input(
                    "Notes", value=row["notes"] or "",
                    key=f"note_{row['id']}", label_visibility="collapsed",
                    placeholder="Add notes...",
                )
                if note != (row["notes"] or ""):
                    conn = get_connection()
                    conn.execute("UPDATE jobs SET notes = ? WHERE id = ?", (note, row["id"]))
                    conn.commit()
                    conn.close()

st.markdown("---")


# ─── Add Manual Job ──────────────────────────────────────────────────
with st.expander("➕ Add Manual Job"):
    with st.form("add_manual_job"):
        m_title = st.text_input("Job Title*")
        m_company = st.text_input("Company*")
        m_location = st.text_input("Location", value="Vancouver, BC")
        m_url = st.text_input("Job URL")
        m_notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Job")

        if submitted and m_title and m_company:
            from core.ranker import rank_job
            job = rank_job({
                "title": m_title,
                "company": m_company,
                "location": m_location,
                "description": "",
                "job_url": m_url,
                "source": "manual",
                "salary_min": None,
                "salary_max": None,
                "salary_interval": "yearly",
                "job_type": "fulltime",
            })
            from core.scraper import save_jobs_to_db
            job["status"] = "saved"
            job["notes"] = m_notes
            count = save_jobs_to_db([job])
            if count > 0:
                st.success(f"Added **{m_title}** at **{m_company}**!")
                log_activity("manual_add", details=f"{m_title} at {m_company}")
                st.rerun()
            else:
                st.warning("Job may already exist (duplicate URL).")


# ─── Weekly Trend Chart ──────────────────────────────────────────────
st.subheader("Weekly Trend")

conn = get_connection()
trend_df = pd.read_sql_query("""
    SELECT
        strftime('%Y-W%W', date_applied) as week,
        COUNT(*) as applications
    FROM jobs
    WHERE date_applied IS NOT NULL
    GROUP BY week
    ORDER BY week
""", conn)
conn.close()

if not trend_df.empty:
    fig = px.bar(
        trend_df, x="week", y="applications",
        title="Applications per Week",
        labels={"week": "Week", "applications": "Applications"},
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No application data yet for the trend chart.")
