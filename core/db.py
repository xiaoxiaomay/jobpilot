"""
Database initialization and helper functions for JobPilot.
Uses SQLite via sqlite3 — single file at data/jobs.db.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = DB_PATH):
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        description TEXT,
        job_url TEXT UNIQUE,
        source TEXT,
        salary_min REAL,
        salary_max REAL,
        salary_interval TEXT,
        job_type TEXT,
        date_posted TEXT,
        date_scraped TEXT DEFAULT (date('now')),
        search_query TEXT,
        score_skills REAL,
        score_immigration REAL,
        score_salary REAL,
        score_company REAL,
        score_success REAL,
        score_total REAL,
        priority TEXT,
        noc_code TEXT,
        noc_description TEXT,
        bcpnp_eligible INTEGER DEFAULT 0,
        status TEXT DEFAULT 'new',
        date_applied TEXT,
        date_response TEXT,
        resume_version TEXT,
        cover_letter_version TEXT,
        ats_score REAL,
        notes TEXT,
        is_archived INTEGER DEFAULT 0,
        tier TEXT DEFAULT 'B',
        networking_notes TEXT DEFAULT '',
        networking_score INTEGER DEFAULT 0,
        success_details TEXT DEFAULT '',
        score_interview REAL DEFAULT 50,
        interview_format_details TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS skill_mentions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill TEXT NOT NULL,
        category TEXT,
        job_id INTEGER,
        user_has INTEGER DEFAULT 0,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );

    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT (date('now')),
        action TEXT,
        job_id INTEGER,
        details TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );

    CREATE TABLE IF NOT EXISTS weekly_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start TEXT,
        jobs_reviewed INTEGER DEFAULT 0,
        applications_sent INTEGER DEFAULT 0,
        interviews INTEGER DEFAULT 0,
        networking_actions INTEGER DEFAULT 0,
        github_commits INTEGER DEFAULT 0,
        linkedin_posts INTEGER DEFAULT 0,
        notes TEXT
    );
    """)

    conn.commit()

    # Migrate existing databases: add new columns if they don't exist
    _migrate_columns = [
        ("tier", "TEXT DEFAULT 'B'"),
        ("networking_notes", "TEXT DEFAULT ''"),
        ("networking_score", "INTEGER DEFAULT 0"),
        ("success_details", "TEXT DEFAULT ''"),
        ("score_interview", "REAL DEFAULT 50"),
        ("interview_format_details", "TEXT DEFAULT ''"),
    ]
    existing_cols = {
        row[1] for row in cursor.execute("PRAGMA table_info(jobs)").fetchall()
    }
    for col_name, col_type in _migrate_columns:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
    conn.commit()

    conn.close()


def log_activity(action: str, job_id: int = None, details: str = None, db_path: str = DB_PATH):
    """Log an activity to the activity_log table."""
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO activity_log (action, job_id, details) VALUES (?, ?, ?)",
        (action, job_id, details),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
