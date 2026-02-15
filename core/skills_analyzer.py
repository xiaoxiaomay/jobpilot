"""
Skills Gap Analyzer.
Aggregates skill mentions across all analyzed JDs to identify gaps and strengths.
"""

import json
import os
import sqlite3

from core.db import get_connection, DB_PATH

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TAXONOMY_PATH = os.path.join(DATA_DIR, "skill_taxonomy.json")
PROFILE_PATH = os.path.join(DATA_DIR, "master_profile.json")


def _load_user_skills() -> set:
    """Load the full set of skills the user has from taxonomy."""
    with open(TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)

    user_skills = set()
    for level in ["user_strong", "user_moderate", "user_emerging"]:
        user_skills.update(taxonomy.get(level, []))
    return user_skills


def _load_categories() -> dict:
    """Load skill category mappings."""
    with open(TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)
    cat_lookup = {}
    for cat_name, skills in taxonomy.get("categories", {}).items():
        for s in skills:
            cat_lookup[s.lower()] = cat_name
    return cat_lookup


def save_skill_mentions(job_id: int, skills: list[dict], db_path: str = DB_PATH):
    """
    Save extracted skills from a JD to the skill_mentions table.

    Args:
        job_id: The job's ID in the jobs table.
        skills: List of dicts with keys: skill, category, user_has
    """
    conn = get_connection(db_path)
    for s in skills:
        conn.execute(
            "INSERT INTO skill_mentions (skill, category, job_id, user_has) VALUES (?, ?, ?, ?)",
            (s["skill"], s["category"], job_id, s["user_has"]),
        )
    conn.commit()
    conn.close()


def analyze_gaps(db_path: str = DB_PATH) -> dict:
    """
    Aggregate skill mentions across all analyzed JDs.

    Returns:
        {
            "total_jobs_analyzed": int,
            "missing_skills": [{"skill", "frequency", "category", "pct"}],
            "strong_skills": [{"skill", "frequency", "category", "pct"}],
            "category_breakdown": {"category": {"has": int, "missing": int, "total": int}},
            "recommendations": [str],
        }
    """
    conn = get_connection(db_path)

    # Total unique jobs with skill mentions
    total_jobs = conn.execute(
        "SELECT COUNT(DISTINCT job_id) FROM skill_mentions"
    ).fetchone()[0]

    if total_jobs == 0:
        conn.close()
        return {
            "total_jobs_analyzed": 0,
            "missing_skills": [],
            "strong_skills": [],
            "category_breakdown": {},
            "recommendations": [],
        }

    # Skills the user is missing (user_has = 0)
    missing_rows = conn.execute("""
        SELECT skill, category, COUNT(DISTINCT job_id) as freq
        FROM skill_mentions
        WHERE user_has = 0
        GROUP BY skill
        ORDER BY freq DESC
    """).fetchall()

    # Skills the user has (user_has = 1)
    strong_rows = conn.execute("""
        SELECT skill, category, COUNT(DISTINCT job_id) as freq
        FROM skill_mentions
        WHERE user_has = 1
        GROUP BY skill
        ORDER BY freq DESC
    """).fetchall()

    # Category breakdown
    cat_rows = conn.execute("""
        SELECT category, user_has, COUNT(DISTINCT skill || '-' || job_id) as cnt
        FROM skill_mentions
        GROUP BY category, user_has
    """).fetchall()

    conn.close()

    missing_skills = [
        {
            "skill": row["skill"],
            "frequency": row["freq"],
            "category": row["category"],
            "pct": round(row["freq"] / total_jobs * 100, 1),
        }
        for row in missing_rows
    ]

    strong_skills = [
        {
            "skill": row["skill"],
            "frequency": row["freq"],
            "category": row["category"],
            "pct": round(row["freq"] / total_jobs * 100, 1),
        }
        for row in strong_rows
    ]

    category_breakdown = {}
    for row in cat_rows:
        cat = row["category"]
        if cat not in category_breakdown:
            category_breakdown[cat] = {"has": 0, "missing": 0, "total": 0}
        if row["user_has"] == 1:
            category_breakdown[cat]["has"] += row["cnt"]
        else:
            category_breakdown[cat]["missing"] += row["cnt"]
        category_breakdown[cat]["total"] += row["cnt"]

    # Generate recommendations
    recommendations = []
    for skill_info in missing_skills[:6]:
        pct = skill_info["pct"]
        skill = skill_info["skill"]
        recommendations.append(
            f"Learn {skill.title()} — appears in {pct}% of target JDs"
        )

    return {
        "total_jobs_analyzed": total_jobs,
        "missing_skills": missing_skills,
        "strong_skills": strong_skills,
        "category_breakdown": category_breakdown,
        "recommendations": recommendations,
    }
