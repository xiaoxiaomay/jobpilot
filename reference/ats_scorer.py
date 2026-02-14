#!/usr/bin/env python3
"""
ATS Resume Scoring Tool
========================
Simulates Applicant Tracking System keyword matching.
Extracts keywords from a Job Description, compares against resume/profile,
and provides a match score with detailed gap analysis.

Usage:
    python ats_scorer.py --jd "path/to/jd.txt" [--resume "path/to/resume.txt"]
    python ats_scorer.py --jd-text "paste JD text here"
"""

import json
import re
import sys
import os
from collections import Counter
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "master_profile.json")

# ATS weight categories
WEIGHT_MAP = {
    "hard_skills": 3.0,      # Technical skills, tools, languages
    "soft_skills": 1.0,      # Communication, leadership, etc.
    "experience_keywords": 2.0,  # Domain-specific experience terms
    "education_keywords": 1.5,   # Degree, certification terms
    "action_verbs": 0.5,        # Led, developed, managed, etc.
}

# Common ATS keyword categories
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


def load_profile(path=PROFILE_PATH):
    with open(path, "r") as f:
        return json.load(f)


def clean_text(text):
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s/\-\+\.]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_jd_keywords(jd_text):
    """Extract and categorize keywords from a job description."""
    jd_lower = clean_text(jd_text)
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
    
    for verb in ACTION_VERBS:
        if re.search(rf'\b{verb}\b', jd_lower):
            found["action_verbs"].append(verb)
    
    # Extract years of experience requirement
    years_match = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', jd_original)
    if years_match:
        found["years_required"] = max(int(y) for y in years_match)
    
    return found


def build_resume_keyword_set(profile):
    """Build the set of keywords present in the candidate's profile."""
    all_text = ""
    
    # Gather all text from profile
    for exp in profile["experiences"]:
        all_text += " " + exp["title"] + " " + exp["company"]
        bullets = exp.get("bullets", {})
        for key, val in bullets.items():
            if key == "keywords":
                all_text += " " + " ".join(val)
            elif isinstance(val, list):
                all_text += " " + " ".join(val)
    
    # Skills
    for category, skills in profile["skills"].items():
        all_text += " " + " ".join(skills)
    
    # Education
    for edu in profile["education"]:
        all_text += " " + edu.get("degree", "")
        all_text += " " + " ".join(edu.get("relevant_coursework", []))
    
    # Summaries
    for key, summary in profile.get("summary_templates", {}).items():
        all_text += " " + summary
    
    return clean_text(all_text)


def score_match(jd_keywords, resume_text):
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
            # Check various forms
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


def select_relevant_bullets(profile, jd_keywords, target_role="data_scientist"):
    """Select the most relevant bullets from master profile based on JD keywords."""
    all_jd_kws = set()
    for cat, kws in jd_keywords.items():
        if isinstance(kws, list):
            all_jd_kws.update(kw.lower() for kw in kws)
    
    bullet_scores = []
    
    for exp in profile["experiences"]:
        bullets = exp.get("bullets", {})
        for section_key, section_bullets in bullets.items():
            if section_key == "keywords":
                continue
            if isinstance(section_bullets, list):
                for bullet in section_bullets:
                    bullet_lower = clean_text(bullet)
                    score = sum(1 for kw in all_jd_kws if kw in bullet_lower)
                    # Boost bullets from experiences tagged with target role
                    if target_role in exp.get("tags", []):
                        score *= 1.5
                    bullet_scores.append({
                        "company": exp["company"],
                        "title": exp["title"],
                        "dates": exp["dates"],
                        "bullet": bullet,
                        "score": score,
                        "exp_id": exp["id"],
                    })
    
    bullet_scores.sort(key=lambda x: x["score"], reverse=True)
    return bullet_scores


def generate_gap_report(jd_keywords, match_results, profile):
    """Generate a detailed gap analysis report."""
    report = []
    report.append("=" * 70)
    report.append("ATS MATCH REPORT")
    report.append("=" * 70)
    report.append("")
    
    # Overall score
    pct = match_results["percentage"]
    if pct >= 80:
        grade = "✅ EXCELLENT — High chance of passing ATS"
    elif pct >= 65:
        grade = "🟡 GOOD — Likely to pass most ATS systems"
    elif pct >= 50:
        grade = "⚠️ FAIR — May pass some ATS systems, optimization needed"
    else:
        grade = "❌ LOW — Likely filtered out by ATS"
    
    report.append(f"OVERALL MATCH SCORE: {pct}%  ({match_results['total_score']:.1f}/{match_results['max_score']:.1f})")
    report.append(f"ASSESSMENT: {grade}")
    report.append("")
    
    # Category breakdown
    report.append("─" * 70)
    report.append("CATEGORY BREAKDOWN")
    report.append("─" * 70)
    for cat, scores in match_results["category_scores"].items():
        bar_len = int(scores["percentage"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        report.append(f"  {cat:25s} [{bar}] {scores['percentage']:5.1f}%  ({scores['matched']}/{scores['total']})")
    report.append("")
    
    # Critical missing hard skills
    missing_hard = match_results["missing"].get("hard_skills", [])
    if missing_hard:
        report.append("─" * 70)
        report.append("🔴 CRITICAL MISSING HARD SKILLS (must add to resume)")
        report.append("─" * 70)
        for skill in missing_hard:
            report.append(f"  ✗ {skill}")
        report.append("")
    
    # Missing soft skills
    missing_soft = match_results["missing"].get("soft_skills", [])
    if missing_soft:
        report.append("🟡 MISSING SOFT SKILLS (consider adding)")
        for skill in missing_soft:
            report.append(f"  ✗ {skill}")
        report.append("")
    
    # Matched keywords
    report.append("─" * 70)
    report.append("✅ MATCHED KEYWORDS")
    report.append("─" * 70)
    for cat, matched in match_results["matched"].items():
        if matched:
            report.append(f"  {cat}: {', '.join(matched)}")
    report.append("")
    
    # Years requirement
    years_req = jd_keywords.get("years_required")
    if years_req:
        report.append(f"📋 Years of experience required: {years_req}+")
        report.append(f"   Your experience: 10+ years (✅ meets requirement)")
        report.append("")
    
    # Recommendations
    report.append("─" * 70)
    report.append("📝 RECOMMENDATIONS FOR THIS JD")
    report.append("─" * 70)
    
    if missing_hard:
        report.append("")
        report.append("1. ADD MISSING HARD SKILLS to your resume:")
        for skill in missing_hard[:10]:
            # Try to suggest where to add
            suggestion = suggest_skill_placement(skill, profile)
            report.append(f"   • {skill} → {suggestion}")
    
    if pct < 65:
        report.append("")
        report.append("2. CONSIDER ADDING A SKILLS SECTION that explicitly lists:")
        all_missing = missing_hard + missing_soft
        report.append(f"   {', '.join(all_missing[:15])}")
    
    report.append("")
    report.append("3. COVER LETTER should emphasize:")
    matched_hard = match_results["matched"].get("hard_skills", [])
    report.append(f"   Top matched skills: {', '.join(matched_hard[:8])}")
    if missing_hard:
        report.append(f"   Address gaps: Show adjacent experience for {', '.join(missing_hard[:5])}")
    
    return "\n".join(report)


def suggest_skill_placement(skill, profile):
    """Suggest where in the resume a missing skill could be naturally added."""
    skill_lower = skill.lower()
    
    # Check if it's in our broader profile but just not emphasized
    all_keywords = set()
    for exp in profile["experiences"]:
        bullets = exp.get("bullets", {})
        kws = bullets.get("keywords", [])
        all_keywords.update(kw.lower() for kw in kws)
    
    if skill_lower in all_keywords:
        return "Already in profile — move to Skills section or emphasize in bullets"
    
    # Suggest based on category
    cloud_tools = {"aws", "azure", "gcp", "google cloud", "sagemaker", "s3", "ec2"}
    bi_tools = {"tableau", "power bi", "looker", "metabase"}
    data_eng = {"airflow", "dbt", "spark", "pyspark", "snowflake", "bigquery", "redshift", "databricks"}
    
    if skill_lower in cloud_tools:
        return "Add to Skills section + mention in project descriptions"
    elif skill_lower in bi_tools:
        return "Add to Skills section (consider a quick certification/project)"
    elif skill_lower in data_eng:
        return "Add to Skills section if you have experience; otherwise note in cover letter as 'eager to learn'"
    else:
        return "Add to Skills section or weave into relevant bullet points"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ATS Resume Scoring Tool")
    parser.add_argument("--jd", type=str, help="Path to job description file")
    parser.add_argument("--jd-text", type=str, help="Job description text (inline)")
    parser.add_argument("--profile", type=str, default=PROFILE_PATH, help="Path to master profile JSON")
    parser.add_argument("--target-role", type=str, default="data_scientist",
                        choices=["data_scientist", "ai_consultant", "product_analyst", "data_analyst"],
                        help="Target role type for bullet selection")
    parser.add_argument("--output", type=str, help="Output report file path")
    args = parser.parse_args()
    
    # Load JD
    if args.jd:
        with open(args.jd, "r") as f:
            jd_text = f.read()
    elif args.jd_text:
        jd_text = args.jd_text
    else:
        print("Error: Provide --jd (file path) or --jd-text (inline text)")
        sys.exit(1)
    
    # Load profile
    profile = load_profile(args.profile)
    
    # Extract JD keywords
    jd_keywords = extract_jd_keywords(jd_text)
    
    # Build resume keyword set
    resume_text = build_resume_keyword_set(profile)
    
    # Score
    match_results = score_match(jd_keywords, resume_text)
    
    # Generate report
    report = generate_gap_report(jd_keywords, match_results, profile)
    
    # Output
    print(report)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
    
    # Also output recommended bullets
    print("\n" + "=" * 70)
    print("TOP MATCHING BULLETS FROM YOUR PROFILE")
    print("=" * 70)
    top_bullets = select_relevant_bullets(profile, jd_keywords, args.target_role)
    seen_companies = set()
    for i, item in enumerate(top_bullets[:15]):
        company_key = item["exp_id"]
        if company_key not in seen_companies:
            seen_companies.add(company_key)
            print(f"\n[{item['title']} @ {item['company']}]")
        if item["score"] > 0:
            print(f"  ({item['score']:.1f}) {item['bullet'][:120]}...")
    
    # Return data for pipeline use
    return {
        "jd_keywords": jd_keywords,
        "match_results": match_results,
        "top_bullets": top_bullets[:20],
    }


if __name__ == "__main__":
    main()
