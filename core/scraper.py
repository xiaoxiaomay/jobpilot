"""
Job Scraper Module.
Wraps python-jobspy to scrape jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter.
Filters, deduplicates, and saves to SQLite database.
"""

import json
import os
import sqlite3
from datetime import datetime

from core.db import get_connection, log_activity
from core.ranker import rank_jobs
from core.immigration import guess_noc_from_title

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "scraper_config.json")


def load_config(config_path: str = CONFIG_PATH) -> dict:
    """Load scraper configuration."""
    default_config = {
        "search_queries": ["data scientist"],
        "location": "Vancouver, BC, Canada",
        "distance_miles": 30,
        "job_type": "fulltime",
        "results_per_query": 25,
        "sites": ["linkedin", "indeed", "glassdoor", "zip_recruiter"],
        "hours_old": 72,
        "country": "Canada",
        "exclude_keywords": [],
        "must_include_keywords": [],
        "min_salary": 70000,
    }

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            user_config = json.load(f)
        return {**default_config, **user_config}
    return default_config


def scrape_all_jobs(config: dict, progress_callback=None) -> list[dict]:
    """
    Scrape jobs from all configured sites and queries.

    Args:
        config: Scraper configuration dict.
        progress_callback: Optional callable(message: str) for status updates.

    Returns:
        List of job dicts.
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        raise ImportError("python-jobspy not installed. Run: pip install python-jobspy")

    all_jobs = []
    queries = config.get("search_queries", ["data scientist"])
    total = len(queries)

    for i, query in enumerate(queries):
        if progress_callback:
            progress_callback(f"Searching: '{query}' ({i+1}/{total})")

        try:
            jobs_df = scrape_jobs(
                site_name=config.get("sites", ["linkedin", "indeed"]),
                search_term=query,
                location=config.get("location", "Vancouver, BC, Canada"),
                distance=config.get("distance_miles", 30),
                job_type=config.get("job_type", "fulltime"),
                results_wanted=config.get("results_per_query", 25),
                hours_old=config.get("hours_old", 72),
                country_indeed=config.get("country", "Canada"),
                is_remote=False,
            )

            if jobs_df is not None and len(jobs_df) > 0:
                for _, row in jobs_df.iterrows():
                    job = {
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company", "")),
                        "location": str(row.get("location", "")),
                        "description": str(row.get("description", "")),
                        "job_url": str(row.get("job_url", "")),
                        "source": str(row.get("site", "")),
                        "salary_min": float(row["min_amount"]) if row.get("min_amount") and str(row.get("min_amount")) != "nan" else None,
                        "salary_max": float(row["max_amount"]) if row.get("max_amount") and str(row.get("max_amount")) != "nan" else None,
                        "salary_interval": str(row.get("interval", "yearly")),
                        "job_type": str(row.get("job_type", "")),
                        "date_posted": str(row.get("date_posted", "")),
                        "search_query": query,
                    }
                    all_jobs.append(job)

                if progress_callback:
                    progress_callback(f"  Found {len(jobs_df)} jobs for '{query}'")
            else:
                if progress_callback:
                    progress_callback(f"  No results for '{query}'")

        except Exception as e:
            if progress_callback:
                progress_callback(f"  Error for '{query}': {e}")
            continue

    return all_jobs


def filter_jobs(jobs: list[dict], config: dict) -> list[dict]:
    """Apply filters and deduplication."""
    if not jobs:
        return jobs

    # Dedup by job_url
    seen_urls = set()
    deduped = []
    for job in jobs:
        url = job.get("job_url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(job)
    jobs = deduped

    # Exclude unwanted keywords from titles
    exclude_kws = [kw.lower() for kw in config.get("exclude_keywords", [])]
    if exclude_kws:
        jobs = [
            j for j in jobs
            if not any(kw in j.get("title", "").lower() for kw in exclude_kws)
        ]

    # Must-include filter
    must_kws = [kw.lower() for kw in config.get("must_include_keywords", [])]
    if must_kws:
        filtered = [
            j for j in jobs
            if any(kw in j.get("title", "").lower() for kw in must_kws)
        ]
        if filtered:
            jobs = filtered

    return jobs


def save_jobs_to_db(jobs: list[dict], db_path: str = None) -> int:
    """
    Save jobs to the SQLite database. Skips duplicates by job_url.

    Returns:
        Number of new jobs inserted.
    """
    from core.db import get_connection, DB_PATH
    if db_path is None:
        db_path = DB_PATH

    conn = get_connection(db_path)
    cursor = conn.cursor()
    inserted = 0

    for job in jobs:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (
                    title, company, location, description, job_url, source,
                    salary_min, salary_max, salary_interval, job_type,
                    date_posted, date_scraped, search_query,
                    score_skills, score_immigration, score_salary,
                    score_company, score_success, score_total, priority,
                    noc_code, noc_description, bcpnp_eligible, status,
                    tier, networking_score, networking_notes, success_details,
                    score_interview, interview_format_details
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, date('now'), ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, 'new',
                    ?, ?, ?, ?,
                    ?, ?
                )
            """, (
                job.get("title"), job.get("company"), job.get("location"),
                job.get("description"), job.get("job_url"), job.get("source"),
                job.get("salary_min"), job.get("salary_max"),
                job.get("salary_interval"), job.get("job_type"),
                job.get("date_posted"), job.get("search_query"),
                job.get("score_skills"), job.get("score_immigration"),
                job.get("score_salary"), job.get("score_company"),
                job.get("score_success"), job.get("score_total"),
                job.get("priority"), job.get("noc_code"),
                job.get("noc_description"), job.get("bcpnp_eligible"),
                job.get("tier", "B"), job.get("networking_score", 0),
                job.get("networking_notes", ""), job.get("success_details", ""),
                job.get("score_interview", 50), job.get("interview_format_details", ""),
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except sqlite3.IntegrityError:
            continue

    conn.commit()
    conn.close()
    return inserted


def scrape_and_rank(config: dict = None, progress_callback=None) -> dict:
    """
    Full scrape → filter → rank → save pipeline.

    Returns:
        {"total_scraped": int, "new_inserted": int, "total_after": int}
    """
    if config is None:
        config = load_config()

    if progress_callback:
        progress_callback("Starting job scrape...")

    # Scrape
    raw_jobs = scrape_all_jobs(config, progress_callback)
    if progress_callback:
        progress_callback(f"Scraped {len(raw_jobs)} raw jobs")

    # Filter
    filtered = filter_jobs(raw_jobs, config)
    if progress_callback:
        progress_callback(f"After filtering: {len(filtered)} jobs")

    # Rank
    if progress_callback:
        progress_callback("Ranking jobs...")
    ranked = rank_jobs(filtered)

    # Save
    if progress_callback:
        progress_callback("Saving to database...")
    new_count = save_jobs_to_db(ranked)

    # Log activity
    log_activity("scraped", details=f"Scraped {len(raw_jobs)} jobs, {new_count} new")

    from core.db import get_connection
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_archived = 0").fetchone()[0]
    conn.close()

    if progress_callback:
        progress_callback(f"Done! {new_count} new jobs added (total: {total})")

    return {
        "total_scraped": len(raw_jobs),
        "new_inserted": new_count,
        "total_in_db": total,
    }


def load_sample_data() -> int:
    """Load sample CSV data into the database for testing."""
    import csv

    sample_path = os.path.join(DATA_DIR, "sample_jobs_raw.csv")
    if not os.path.exists(sample_path):
        return 0

    jobs = []
    with open(sample_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job = {
                "title": row.get("title", ""),
                "company": row.get("company", ""),
                "location": row.get("location", ""),
                "description": row.get("description", ""),
                "job_url": row.get("job_url", ""),
                "source": "sample",
                "salary_min": float(row["min_amount"]) if row.get("min_amount") else None,
                "salary_max": float(row["max_amount"]) if row.get("max_amount") else None,
                "salary_interval": row.get("interval", "yearly"),
                "job_type": "fulltime",
                "date_posted": row.get("scraped_date", ""),
                "search_query": row.get("search_query", ""),
            }
            jobs.append(job)

    ranked = rank_jobs(jobs)
    return save_jobs_to_db(ranked)
