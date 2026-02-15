"""
JobPilot — AI-Powered Job Search Dashboard
Streamlit multi-page entry point.
"""

import streamlit as st
import os
from core.db import init_db

# Initialize database on first run
init_db()

# Copy master profile to data/ if not present
data_dir = os.path.join(os.path.dirname(__file__), "data")
ref_dir = os.path.join(os.path.dirname(__file__), "reference")
profile_dest = os.path.join(data_dir, "master_profile.json")
profile_src = os.path.join(ref_dir, "master_profile.json")
if not os.path.exists(profile_dest) and os.path.exists(profile_src):
    import shutil
    shutil.copy2(profile_src, profile_dest)

st.set_page_config(
    page_title="JobPilot",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Home page ---
st.title("🧭 JobPilot")
st.subheader("AI-Powered Job Search Dashboard")

st.markdown("""
Welcome to **JobPilot** — your intelligent job search platform for Canadian tech immigration.

Use the sidebar to navigate between pages:

| Page | Purpose |
|------|---------|
| **Job Pool** | Discover, score & browse job opportunities |
| **Apply** | Generate AI-powered resumes & cover letters |
| **Tracker** | Track application status & weekly activity |
| **Skills Gap** | Identify skill gaps across target JDs |
| **Immigration** | BC PNP Tech eligibility tracking |
""")

# Quick stats from DB
from core.db import get_connection
conn = get_connection()
total_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_archived = 0").fetchone()[0]
high_priority = conn.execute("SELECT COUNT(*) FROM jobs WHERE priority = 'HIGH' AND is_archived = 0").fetchone()[0]
applied = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'").fetchone()[0]
pnp_eligible = conn.execute("SELECT COUNT(*) FROM jobs WHERE bcpnp_eligible = 1 AND is_archived = 0").fetchone()[0]
conn.close()

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs", total_jobs)
col2.metric("HIGH Priority", high_priority)
col3.metric("Applied", applied)
col4.metric("BC PNP Eligible", pnp_eligible)

if total_jobs == 0:
    st.info("No jobs in database yet. Go to **Job Pool** to scrape jobs or load sample data.")

    if st.button("Load Sample Data (20 test jobs)"):
        from core.scraper import load_sample_data
        count = load_sample_data()
        st.success(f"Loaded {count} sample jobs!")
        st.rerun()
