"""
ATS Resume Scoring Module.
Simulates Applicant Tracking System keyword matching.
Extracts keywords from a Job Description, compares against user profile,
and provides a match score with detailed gap analysis.
"""

import json
import os
import re
from pathlib import Path

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILE_PATH = os.path.join(DATA_DIR, "master_profile.json")
TAXONOMY_PATH = os.path.join(DATA_DIR, "skill_taxonomy.json")

# ATS weight categories
WEIGHT_MAP = {
    "hard_skills": 3.0,
    "soft_skills": 1.0,
    "experience_keywords": 2.0,
    "education_keywords": 1.5,
    "action_verbs": 0.5,
}

# Hard skill patterns (comprehensive list for tech/data roles)
HARD_SKILL_PATTERNS = {
    # Programming & Data
    "python", "sql", "r", "java", "scala", "javascript", "typescript", "c++",
    "bash", "shell", "matlab", "sas", "stata", "go", "rust", "ruby",
    # ML/AI
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "neural network", "llm",
    "large language model", "generative ai", "gen ai", "rag",
    "retrieval augmented generation", "fine-tuning", "prompt engineering",
    "langchain", "llamaindex", "vector database", "embeddings",
    "transformer", "bert", "gpt", "diffusion",
    # ML Frameworks
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "xgboost", "lightgbm", "catboost", "hugging face", "huggingface",
    "mlflow", "wandb", "optuna", "ray",
    # Data Tools
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "dask", "polars", "pyspark", "spark", "hadoop", "hive", "presto",
    "airflow", "dagster", "prefect", "dbt", "fivetran",
    # Databases
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "snowflake", "bigquery", "redshift", "databricks", "delta lake",
    # BI & Visualization
    "tableau", "power bi", "looker", "metabase", "superset",
    "excel", "google sheets",
    # Cloud
    "aws", "azure", "gcp", "google cloud", "s3", "ec2", "lambda",
    "sagemaker", "vertex ai", "cloud computing",
    # DevOps / Infra
    "docker", "kubernetes", "ci/cd", "git", "github", "gitlab",
    "terraform", "jenkins", "linux",
    # Security
    "cybersecurity", "security", "siem", "soc", "penetration testing",
    "vulnerability", "encryption", "firewall", "ids", "ips",
    "compliance", "gdpr", "hipaa", "iso 27001", "nist",
    # Statistics & Methods
    "a/b testing", "ab testing", "hypothesis testing", "causal inference",
    "regression", "classification", "clustering", "time series",
    "bayesian", "statistical modeling", "statistical analysis",
    "feature engineering", "feature selection", "dimensionality reduction",
    "anomaly detection", "fraud detection", "recommendation system",
    # Data Engineering
    "etl", "elt", "data pipeline", "data warehouse", "data lake",
    "data modeling", "data governance", "data quality",
    # Product/Business
    "product analytics", "growth analytics", "funnel analysis",
    "cohort analysis", "retention", "churn", "ltv", "lifetime value",
    "kpi", "okr", "metrics", "experimentation",
    "segmentation", "personalization",
    # Other
    "agile", "scrum", "jira", "confluence",
    "api", "rest", "graphql", "microservices",
}

SOFT_SKILL_KEYWORDS = {
    "communication", "leadership", "teamwork", "collaboration",
    "problem solving", "problem-solving", "critical thinking",
    "project management", "stakeholder", "cross-functional",
    "presentation", "mentoring", "coaching", "strategic",
    "analytical", "detail-oriented", "self-motivated", "adaptable",
}

EXPERIENCE_KEYWORDS = {
    "years of experience", "year experience", "senior", "lead",
    "manager", "director", "principal", "staff",
    "entry level", "junior", "mid-level", "intermediate",
}

EDUCATION_KEYWORDS = {
    "bachelor", "master", "phd", "doctorate", "mba",
    "computer science", "statistics", "mathematics", "engineering",
    "data science", "machine learning", "artificial intelligence",
    "cybersecurity", "information security",
}

ACTION_VERBS = {
    "led", "developed", "designed", "built", "implemented", "deployed",
    "managed", "analyzed", "optimized", "created", "established",
    "improved", "automated", "delivered", "collaborated", "mentored",
    "architected", "scaled", "reduced", "increased", "drove",
    "spearheaded", "pioneered", "transformed", "streamlined",
}


def load_profile(path: str = PROFILE_PATH) -> dict:
    """Load the master profile JSON."""
    with open(path, "r") as f:
        return json.load(f)


def load_taxonomy(path: str = TAXONOMY_PATH) -> dict:
    """Load the skill taxonomy JSON."""
    with open(path, "r") as f:
        return json.load(f)


def clean_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s/\-\+\.]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_jd_keywords(jd_text: str) -> dict:
    """Extract and categorize keywords from a job description."""
    jd_original = jd_text.lower()

    found = {
        "hard_skills": [],
        "soft_skills": [],
        "experience_keywords": [],
        "education_keywords": [],
        "action_verbs": [],
    }

    # Check hard skills (multi-word first, then single-word)
    for skill in sorted(HARD_SKILL_PATTERNS, key=len, reverse=True):
        if skill in jd_original or skill.replace(" ", "-") in jd_original or skill.replace("-", " ") in jd_original:
            found["hard_skills"].append(skill)

    for kw in SOFT_SKILL_KEYWORDS:
        if kw in jd_original:
            found["soft_skills"].append(kw)

    for kw in EXPERIENCE_KEYWORDS:
        if kw in jd_original:
            found["experience_keywords"].append(kw)

    for kw in EDUCATION_KEYWORDS:
        if kw in jd_original:
            found["education_keywords"].append(kw)

    jd_lower = clean_text(jd_text)
    for verb in ACTION_VERBS:
        if re.search(rf'\b{verb}\b', jd_lower):
            found["action_verbs"].append(verb)

    # Extract years of experience requirement
    years_match = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', jd_original)
    if years_match:
        found["years_required"] = max(int(y) for y in years_match)

    return found


def build_resume_keyword_set(profile: dict) -> str:
    """Build the set of keywords present in the candidate's profile."""
    all_text = ""

    for exp in profile["experiences"]:
        all_text += " " + exp["title"] + " " + exp["company"]
        bullets = exp.get("bullets", {})
        for key, val in bullets.items():
            if key == "keywords":
                all_text += " " + " ".join(val)
            elif isinstance(val, list):
                all_text += " " + " ".join(val)

    for category, skills in profile["skills"].items():
        all_text += " " + " ".join(skills)

    for edu in profile["education"]:
        all_text += " " + edu.get("degree", "")
        all_text += " " + " ".join(edu.get("relevant_coursework", []))

    for key, summary in profile.get("summary_templates", {}).items():
        all_text += " " + summary

    return clean_text(all_text)


def score_match(jd_keywords: dict, resume_text: str) -> dict:
    """Score how well the resume matches the JD keywords."""
    results = {
        "total_score": 0,
        "max_score": 0,
        "percentage": 0,
        "matched": {},
        "missing": {},
        "category_scores": {},
    }

    for category, keywords in jd_keywords.items():
        if category == "years_required":
            continue
        if not keywords:
            continue

        weight = WEIGHT_MAP.get(category, 1.0)
        matched = []
        missing = []

        for kw in keywords:
            kw_lower = kw.lower()
            variants = [
                kw_lower,
                kw_lower.replace("-", " "),
                kw_lower.replace(" ", "-"),
                kw_lower.replace(" ", ""),
                kw_lower.replace("/", " "),
            ]
            if any(v in resume_text for v in variants):
                matched.append(kw)
            else:
                missing.append(kw)

        cat_score = len(matched) * weight
        cat_max = len(keywords) * weight

        results["matched"][category] = matched
        results["missing"][category] = missing
        results["total_score"] += cat_score
        results["max_score"] += cat_max
        results["category_scores"][category] = {
            "matched": len(matched),
            "total": len(keywords),
            "percentage": round(len(matched) / len(keywords) * 100, 1) if keywords else 0,
        }

    if results["max_score"] > 0:
        results["percentage"] = round(results["total_score"] / results["max_score"] * 100, 1)

    return results


def score_ats(jd_text: str, profile: dict = None) -> dict:
    """
    Full ATS scoring pipeline.

    Returns:
        {
            "score": float (0-100),
            "matched_keywords": list,
            "missing_keywords": list,
            "category_scores": dict,
            "jd_keywords": dict,
            "years_required": int or None,
        }
    """
    if profile is None:
        profile = load_profile()

    jd_keywords = extract_jd_keywords(jd_text)
    resume_text = build_resume_keyword_set(profile)
    match_results = score_match(jd_keywords, resume_text)

    all_matched = []
    all_missing = []
    for cat_matched in match_results["matched"].values():
        all_matched.extend(cat_matched)
    for cat_missing in match_results["missing"].values():
        all_missing.extend(cat_missing)

    return {
        "score": match_results["percentage"],
        "matched_keywords": all_matched,
        "missing_keywords": all_missing,
        "category_scores": match_results["category_scores"],
        "jd_keywords": jd_keywords,
        "years_required": jd_keywords.get("years_required"),
    }


def generate_gap_report(jd_keywords: dict, match_results: dict) -> str:
    """Generate a text-based gap analysis report."""
    report = []
    report.append("=" * 70)
    report.append("ATS MATCH REPORT")
    report.append("=" * 70)
    report.append("")

    pct = match_results["percentage"]
    if pct >= 80:
        grade = "EXCELLENT — High chance of passing ATS"
    elif pct >= 65:
        grade = "GOOD — Likely to pass most ATS systems"
    elif pct >= 50:
        grade = "FAIR — May pass some ATS systems, optimization needed"
    else:
        grade = "LOW — Likely filtered out by ATS"

    report.append(f"OVERALL MATCH SCORE: {pct}%  ({match_results['total_score']:.1f}/{match_results['max_score']:.1f})")
    report.append(f"ASSESSMENT: {grade}")
    report.append("")

    report.append("-" * 70)
    report.append("CATEGORY BREAKDOWN")
    report.append("-" * 70)
    for cat, scores in match_results["category_scores"].items():
        bar_len = int(scores["percentage"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        report.append(f"  {cat:25s} [{bar}] {scores['percentage']:5.1f}%  ({scores['matched']}/{scores['total']})")
    report.append("")

    missing_hard = match_results["missing"].get("hard_skills", [])
    if missing_hard:
        report.append("-" * 70)
        report.append("CRITICAL MISSING HARD SKILLS")
        report.append("-" * 70)
        for skill in missing_hard:
            report.append(f"  x {skill}")
        report.append("")

    report.append("-" * 70)
    report.append("MATCHED KEYWORDS")
    report.append("-" * 70)
    for cat, matched in match_results["matched"].items():
        if matched:
            report.append(f"  {cat}: {', '.join(matched)}")

    return "\n".join(report)


def extract_skills_for_db(jd_text: str, profile: dict = None) -> list[dict]:
    """
    Extract skills from a JD for storage in the skill_mentions table.

    Returns list of dicts: [{"skill": ..., "category": ..., "user_has": 0|1}]
    """
    if profile is None:
        profile = load_profile()

    taxonomy = load_taxonomy()
    user_skills = set()
    for level in ["user_strong", "user_moderate", "user_emerging"]:
        user_skills.update(taxonomy.get(level, []))

    jd_keywords = extract_jd_keywords(jd_text)
    results = []
    seen = set()

    # Map skills to categories
    cat_lookup = {}
    for cat_name, cat_skills in taxonomy.get("categories", {}).items():
        for s in cat_skills:
            cat_lookup[s] = cat_name

    for cat, skills in jd_keywords.items():
        if not isinstance(skills, list):
            continue
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in seen:
                continue
            seen.add(skill_lower)
            results.append({
                "skill": skill_lower,
                "category": cat_lookup.get(skill_lower, cat),
                "user_has": 1 if skill_lower in user_skills else 0,
            })

    return results
