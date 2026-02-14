#!/usr/bin/env python3
"""
Job Ranker & Matcher — Module A
================================
Scores and ranks scraped jobs against your profile using multiple criteria:
  - Skills/experience match (40%)
  - Immigration pathway fit (25%)
  - Salary level (15%)
  - Company size & reputation (10%)
  - Success probability (10%)

Usage:
    python job_ranker.py --input jobs_raw.csv --output jobs_ranked.csv
    python job_ranker.py --input jobs_raw.csv --output jobs_ranked.csv --top 20

Requirements:
    pip install pandas
"""

import json
import os
import re
import sys
import pandas as pd
from pathlib import Path

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(TOOLKIT_DIR, "master_profile.json")

# ─── Scoring Weights ─────────────────────────────────────────────────
WEIGHTS = {
    "skills_match": 0.40,
    "immigration_fit": 0.25,
    "salary_score": 0.15,
    "company_score": 0.10,
    "success_probability": 0.10,
}

# ─── BC PNP Tech Priority NOCs ───────────────────────────────────────
BCPNP_TECH_NOCS = {
    "21211",  # Data Scientists
    "21220",  # Cybersecurity Specialists
    "21221",  # Business Systems Specialists
    "21222",  # Information Systems Specialists
    "21223",  # Database Analysts
    "21230",  # Computer Systems Developers and Programmers
    "21231",  # Software Engineers and Designers
    "21232",  # Software Developers
    "21233",  # Web Designers
    "21234",  # Web Developers and Programmers
    "21311",  # Computer Engineers
    "20012",  # Computer and Information Systems Managers
    "22220",  # Computer Network and Web Technicians
    "22222",  # Information Systems Testing Technicians
}

# ─── Skill Keywords by Priority Level ────────────────────────────────
# Your STRONG skills (you have deep experience)
STRONG_SKILLS = {
    "python", "sql", "r", "machine learning", "deep learning",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "nlp", "natural language processing", "gnn", "graph neural network",
    "reinforcement learning", "time series", "a/b testing", "ab testing",
    "causal inference", "statistical modeling", "regression",
    "clustering", "classification", "anomaly detection",
    "data visualization", "hypothesis testing", "random forest",
    "lightgbm", "xgboost", "neural network", "recommendation",
    "shap", "feature engineering", "data pipeline",
    "sentiment analysis", "chatbot", "nlg",
}

# Skills you have SOME experience with
MODERATE_SKILLS = {
    "flask", "docker", "git", "linux", "jupyter",
    "data product", "product analytics", "growth analytics",
    "segmentation", "personalization", "kpi", "metrics",
    "etl", "data warehouse", "api", "agile",
    "project management", "stakeholder",
}

# Skills you're LEARNING or have basic exposure to
EMERGING_SKILLS = {
    "cybersecurity", "network security", "rag",
    "retrieval augmented generation", "langchain", "llm",
    "large language model", "generative ai", "gen ai",
    "prompt engineering", "vector database",
    "hugging face", "transformer", "bert", "gpt",
}

# Skills you DON'T have (common in JDs)
WEAK_SKILLS = {
    "aws", "gcp", "azure", "sagemaker", "snowflake",
    "bigquery", "redshift", "databricks", "spark", "pyspark",
    "airflow", "dbt", "tableau", "power bi", "looker",
    "kubernetes", "terraform", "ci/cd", "scala", "java",
    "go", "rust", "c++", "hadoop", "hive", "presto",
    "mlflow", "wandb",
}

# ─── Known companies (for company scoring) ───────────────────────────
# You can expand this list
COMPANY_TIERS = {
    "tier1": [  # Top-tier, great for career
        "amazon", "google", "microsoft", "meta", "apple", "nvidia",
        "salesforce", "shopify", "stripe", "databricks", "snowflake",
        "openai", "anthropic", "cohere", "hugging face",
        "lululemon", "hootsuite", "slack", "mastercard",
        "deloitte", "mckinsey", "bcg", "bain", "accenture", "pwc", "ey", "kpmg",
        "rbc", "td", "bmo", "scotiabank", "cibc",
        "telus", "shaw", "bc hydro",
    ],
    "tier2": [  # Solid mid-size / well-known
        "clio", "bench", "dapper labs", "trulioo", "later",
        "absolute software", "d-wave", "1password",
        "thinkific", "procurify", "vidyard", "freshbooks",
        "vancouver coastal health", "phsa", "bc cancer",
    ],
}


def load_profile():
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)


def score_skills_match(row, profile):
    """Score how well job requirements match your skills (0-100)."""
    # Combine all text fields from the job
    text_fields = []
    for col in ["title", "description", "job_type"]:
        val = row.get(col, "")
        if pd.notna(val):
            text_fields.append(str(val).lower())
    job_text = " ".join(text_fields)
    
    if not job_text.strip():
        return 50  # No info, neutral score
    
    # Count skill matches by tier
    strong_matches = sum(1 for s in STRONG_SKILLS if s in job_text)
    moderate_matches = sum(1 for s in MODERATE_SKILLS if s in job_text)
    emerging_matches = sum(1 for s in EMERGING_SKILLS if s in job_text)
    weak_matches = sum(1 for s in WEAK_SKILLS if s in job_text)
    
    # Total skills mentioned in JD
    total_mentioned = strong_matches + moderate_matches + emerging_matches + weak_matches
    if total_mentioned == 0:
        return 50
    
    # Weighted score
    score = (
        strong_matches * 1.0 +
        moderate_matches * 0.7 +
        emerging_matches * 0.4 +
        weak_matches * 0.1
    ) / total_mentioned * 100
    
    return min(100, max(0, round(score)))


def score_immigration_fit(row):
    """Score how well the job fits BC PNP Tech pathway (0-100)."""
    score = 50  # Base score
    
    noc_guess = str(row.get("noc_code_guess", ""))
    title = str(row.get("title", "")).lower()
    description = str(row.get("description", "")).lower() if pd.notna(row.get("description")) else ""
    location = str(row.get("location", "")).lower()
    
    # NOC code in BC PNP Tech priority list
    for noc in BCPNP_TECH_NOCS:
        if noc in noc_guess:
            score += 30
            break
    
    # Title keywords that align with priority NOCs
    priority_titles = [
        "data scientist", "machine learning", "ml engineer",
        "cybersecurity", "security analyst", "security engineer",
        "software engineer", "software developer",
        "data analyst", "data engineer", "analytics",
        "ai", "artificial intelligence",
    ]
    if any(pt in title for pt in priority_titles):
        score += 10
    
    # Location in BC (critical for BC PNP)
    if any(loc in location for loc in ["vancouver", "burnaby", "surrey", "richmond", "bc", "british columbia"]):
        score += 10
    elif "remote" in location:
        score += 5  # Remote OK but less ideal for PNP
    elif "canada" in location:
        score += 3
    
    # Full-time (required for most PNP streams)
    job_type = str(row.get("job_type", "")).lower()
    if "full" in job_type or "permanent" in job_type:
        score += 5
    elif "contract" in job_type or "temporary" in job_type:
        score -= 15  # Contracts are risky for PNP
    
    # Job duration mention (PNP needs 1+ year)
    if "permanent" in description or "full-time" in description:
        score += 5
    
    # Experience level (not too senior = higher success chance)
    if "senior" in title and "staff" not in title and "principal" not in title:
        score += 5
    elif "lead" in title:
        score += 3
    elif "junior" in title or "entry" in title:
        score -= 5  # Underleveled
    
    return min(100, max(0, round(score)))


def score_salary(row):
    """Score salary level (0-100). Higher salary = higher BC PNP SIRS score."""
    min_salary = row.get("min_amount")
    max_salary = row.get("max_amount")
    
    if pd.isna(min_salary) and pd.isna(max_salary):
        return 50  # No data, neutral
    
    # Use midpoint if both available, otherwise use what we have
    if pd.notna(min_salary) and pd.notna(max_salary):
        salary = (float(min_salary) + float(max_salary)) / 2
    elif pd.notna(max_salary):
        salary = float(max_salary)
    else:
        salary = float(min_salary)
    
    # Check if hourly (convert to annual)
    interval = str(row.get("interval", "")).lower()
    if "hour" in interval:
        salary = salary * 2080  # 40hr/week * 52 weeks
    elif "month" in interval:
        salary = salary * 12
    
    # Score based on salary brackets (CAD)
    # BC PNP SIRS gives more points for higher wages
    # $70/hr ($145,600/yr) threshold for high-wage draws
    if salary >= 145000:
        return 100  # Excellent — qualifies for high-wage BC PNP draws
    elif salary >= 120000:
        return 90
    elif salary >= 100000:
        return 80
    elif salary >= 85000:
        return 65
    elif salary >= 70000:
        return 50
    elif salary >= 55000:
        return 30
    else:
        return 15


def score_company(row):
    """Score company reputation and size (0-100)."""
    company = str(row.get("company", "")).lower().strip()
    
    if not company:
        return 50
    
    # Check tier
    for tier1 in COMPANY_TIERS["tier1"]:
        if tier1 in company or company in tier1:
            return 90
    
    for tier2 in COMPANY_TIERS["tier2"]:
        if tier2 in company or company in tier2:
            return 75
    
    # Heuristics from description
    description = str(row.get("description", "")).lower() if pd.notna(row.get("description")) else ""
    
    # Company size signals
    if any(kw in description for kw in ["fortune 500", "global", "enterprise", "publicly traded"]):
        return 80
    elif any(kw in description for kw in ["series b", "series c", "series d", "well-funded"]):
        return 70
    elif any(kw in description for kw in ["startup", "early stage", "seed", "series a"]):
        return 55  # More risky for immigration
    
    return 60  # Default for unknown companies


def score_success_probability(row, skills_score):
    """Estimate probability of getting an interview (0-100)."""
    title = str(row.get("title", "")).lower()
    description = str(row.get("description", "")).lower() if pd.notna(row.get("description")) else ""
    
    score = 50  # Base
    
    # High skills match = higher success
    if skills_score >= 80:
        score += 20
    elif skills_score >= 60:
        score += 10
    elif skills_score < 40:
        score -= 15
    
    # Experience level alignment
    years_match = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', description)
    if years_match:
        max_years = max(int(y) for y in years_match)
        if max_years <= 10:
            score += 10  # Good match
        elif max_years <= 5:
            score += 15  # Overqualified (good position)
        elif max_years > 12:
            score -= 5
    
    # Canadian experience requirement (red flag for us)
    if "canadian experience" in description or "local experience" in description:
        score -= 20
    
    # Security clearance requirement
    if "security clearance" in description or "secret clearance" in description:
        score -= 25
    
    # Visa sponsorship mentioned
    if "sponsorship" in description:
        if "no sponsorship" in description or "not sponsor" in description:
            score -= 30  # They won't sponsor
        elif "sponsor" in description:
            score += 10
    
    # Work permit / PR requirement
    if "must be" in description and ("citizen" in description or "permanent resident" in description):
        if "work permit" not in description:
            score -= 20
    
    # Referral culture companies
    if any(c in str(row.get("company", "")).lower() for c in ["google", "meta", "amazon"]):
        score -= 10  # Very competitive, referral-heavy
    
    return min(100, max(0, round(score)))


def rank_jobs(df):
    """Score all jobs and produce final ranking."""
    if df.empty:
        return df
    
    profile = load_profile()
    
    print("📊 Scoring jobs...")
    
    # Calculate individual scores
    df["score_skills"] = df.apply(lambda r: score_skills_match(r, profile), axis=1)
    df["score_immigration"] = df.apply(score_immigration_fit, axis=1)
    df["score_salary"] = df.apply(score_salary, axis=1)
    df["score_company"] = df.apply(score_company, axis=1)
    df["score_success"] = df.apply(
        lambda r: score_success_probability(r, r["score_skills"]), axis=1
    )
    
    # Weighted composite score
    df["total_score"] = (
        df["score_skills"] * WEIGHTS["skills_match"] +
        df["score_immigration"] * WEIGHTS["immigration_fit"] +
        df["score_salary"] * WEIGHTS["salary_score"] +
        df["score_company"] * WEIGHTS["company_score"] +
        df["score_success"] * WEIGHTS["success_probability"]
    ).round(1)
    
    # Priority label
    df["priority"] = df["total_score"].apply(
        lambda s: "🔴 HIGH" if s >= 75 else ("🟡 MEDIUM" if s >= 55 else "⚪ LOW")
    )
    
    # Sort by total score
    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    
    return df


def print_summary(df, top_n=15):
    """Print a nice summary of top-ranked jobs."""
    print("\n" + "=" * 80)
    print(f"TOP {min(top_n, len(df))} RANKED JOBS")
    print("=" * 80)
    
    cols = ["total_score", "priority", "title", "company", "score_skills",
            "score_immigration", "score_salary", "bcpnp_tech_eligible"]
    
    available_cols = [c for c in cols if c in df.columns]
    
    for i, (_, row) in enumerate(df.head(top_n).iterrows()):
        print(f"\n#{i+1}  [{row.get('total_score', 0):.0f}/100] {row.get('priority', '')}")
        print(f"    {row.get('title', 'N/A')} @ {row.get('company', 'N/A')}")
        print(f"    Skills: {row.get('score_skills', 'N/A')} | Immigration: {row.get('score_immigration', 'N/A')} | Salary: {row.get('score_salary', 'N/A')} | Company: {row.get('score_company', 'N/A')}")
        print(f"    BC PNP Tech: {row.get('bcpnp_tech_eligible', '?')} | NOC: {row.get('noc_code_guess', '?')}")
        if pd.notna(row.get("job_url")):
            print(f"    URL: {row['job_url']}")
    
    # Stats
    print(f"\n{'─' * 80}")
    print(f"Total jobs: {len(df)}")
    high = len(df[df["priority"].str.contains("HIGH", na=False)])
    med = len(df[df["priority"].str.contains("MEDIUM", na=False)])
    print(f"Priority: 🔴 HIGH: {high} | 🟡 MEDIUM: {med} | ⚪ LOW: {len(df) - high - med}")
    
    bcpnp_yes = len(df[df.get("bcpnp_tech_eligible", pd.Series()).str.contains("Yes", na=False)])
    print(f"BC PNP Tech eligible: {bcpnp_yes}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Job Ranker — Module A")
    parser.add_argument("--input", required=True, help="Input CSV from job_scraper.py")
    parser.add_argument("--output", default="jobs_ranked.csv", help="Output ranked CSV")
    parser.add_argument("--top", type=int, default=15, help="Show top N results")
    args = parser.parse_args()
    
    print("=" * 60)
    print("JOB RANKER — Module A")
    print("=" * 60)
    
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} jobs from {args.input}")
    
    df = rank_jobs(df)
    
    # Save
    df.to_csv(args.output, index=False)
    print(f"\n💾 Ranked jobs saved to: {args.output}")
    
    print_summary(df, args.top)
    
    print(f"\n✅ Next: Run excel_tracker.py to generate the Excel dashboard")


if __name__ == "__main__":
    main()
