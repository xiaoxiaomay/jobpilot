"""
Job Ranker — 6-dimension scoring system.
Scores and ranks jobs against the user's profile:
  - Skills match (30%)
  - Immigration pathway fit (25%)
  - Interview format (15%)
  - Salary level (10%)
  - Company reputation (10%)
  - Success probability (10%)
"""

import json
import os
import re
from pathlib import Path

from core.immigration import (
    BCPNP_TECH_NOCS,
    guess_noc_from_title,
    is_bcpnp_eligible,
    check_location_bc,
)
from core.networking import generate_networking_intel

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILE_PATH = os.path.join(DATA_DIR, "master_profile.json")
TAXONOMY_PATH = os.path.join(DATA_DIR, "skill_taxonomy.json")

# Scoring Weights (6 dimensions)
WEIGHTS = {
    "skills_match": 0.30,
    "immigration_fit": 0.25,
    "interview_format": 0.15,
    "salary_score": 0.10,
    "company_score": 0.10,
    "success_probability": 0.10,
}

# Known companies for company scoring
COMPANY_TIERS = {
    "tier1": [
        "amazon", "google", "microsoft", "meta", "apple", "nvidia",
        "salesforce", "shopify", "stripe", "databricks", "snowflake",
        "openai", "anthropic", "cohere", "hugging face",
        "lululemon", "hootsuite", "slack", "mastercard",
        "deloitte", "mckinsey", "bcg", "bain", "accenture", "pwc", "ey", "kpmg",
        "rbc", "td", "bmo", "scotiabank", "cibc",
        "telus", "shaw", "bc hydro",
    ],
    "tier2": [
        "clio", "bench", "dapper labs", "trulioo", "later",
        "absolute software", "d-wave", "1password",
        "thinkific", "procurify", "vidyard", "freshbooks",
        "vancouver coastal health", "phsa", "bc cancer",
        "fortinet", "borealis ai",
    ],
}

# Tier assignment company lists
TIER1_COMPANIES = [
    "amazon", "google", "microsoft", "meta", "apple", "netflix",
    "lululemon", "shopify", "rbc", "td", "bmo", "cibc", "scotiabank",
    "telus", "bchydro", "bc hydro", "deloitte", "pwc", "ey", "kpmg",
    "mckinsey", "bain", "bcg", "accenture",
]

SMALL_COMPANIES_OR_STARTUPS = [
    "bench", "clio", "hootsuite", "later", "absolute", "d-wave",
    "copperleaf", "eventbase", "finger food", "grow",
]

# Companies known to hire internationally
IMMIGRANT_FRIENDLY_COMPANIES = [
    "amazon", "microsoft", "google", "meta", "apple",
    "shopify", "clio", "d-wave", "hootsuite",
    "rbc", "td", "deloitte", "ey", "pwc", "kpmg",
    "phsa", "vancouver coastal health", "bc cancer",
]

# Companies known for live coding interviews
LIVE_CODING_COMPANIES = [
    "google", "meta", "amazon", "apple", "netflix",
    "microsoft", "uber", "airbnb", "stripe", "doordash", "instacart",
    "databricks", "snowflake", "palantir", "linkedin",
]

# Companies that typically use take-home or discussion format
TAKEHOME_COMPANIES = [
    # Vancouver mid-size tech
    "hootsuite", "later", "clio", "bench", "copperleaf",
    "visier", "absolute", "eventbase", "finger food",
    "grow", "thinkific", "trulioo", "benevity",
    # Vancouver non-tech
    "lululemon", "aritzia", "london drugs",
    "translink", "icbc", "bc hydro", "worksafe",
    "first west", "vancity", "coast capital",
    "phsa", "vancouver coastal health", "bc cancer",
    "city of vancouver",
    # Consulting firms (case interview, no coding)
    "deloitte", "ey", "kpmg", "accenture", "bdo",
    "bain", "bcg",
    # Banks
    "rbc", "td", "bmo", "cibc", "scotiabank", "hsbc",
]


def _load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _load_skill_sets() -> dict:
    """Load skill sets from taxonomy."""
    taxonomy = _load_json(TAXONOMY_PATH)
    return {
        "strong": set(taxonomy.get("user_strong", [])),
        "moderate": set(taxonomy.get("user_moderate", [])),
        "emerging": set(taxonomy.get("user_emerging", [])),
        "weak": set(taxonomy.get("user_weak", [])),
    }


def score_skills_match(title: str, description: str, skill_sets: dict) -> int:
    """Score how well job requirements match user's skills (0-100)."""
    job_text = f"{title} {description}".lower()
    if not job_text.strip():
        return 50

    strong_matches = sum(1 for s in skill_sets["strong"] if s in job_text)
    moderate_matches = sum(1 for s in skill_sets["moderate"] if s in job_text)
    emerging_matches = sum(1 for s in skill_sets["emerging"] if s in job_text)
    weak_matches = sum(1 for s in skill_sets["weak"] if s in job_text)

    total_mentioned = strong_matches + moderate_matches + emerging_matches + weak_matches
    if total_mentioned == 0:
        return 50

    score = (
        strong_matches * 1.0 +
        moderate_matches * 0.7 +
        emerging_matches * 0.4 +
        weak_matches * 0.1
    ) / total_mentioned * 100

    return min(100, max(0, round(score)))


def score_immigration_fit(title: str, description: str, location: str,
                          job_type: str, noc_code: str) -> int:
    """Score how well the job fits BC PNP Tech pathway (0-100)."""
    score = 50
    title_lower = title.lower() if title else ""
    desc_lower = description.lower() if description else ""
    jtype_lower = job_type.lower() if job_type else ""

    # NOC code in BC PNP Tech priority list
    if noc_code and noc_code in BCPNP_TECH_NOCS:
        score += 30

    # Title keywords that align with priority NOCs
    priority_titles = [
        "data scientist", "machine learning", "ml engineer",
        "cybersecurity", "security analyst", "security engineer",
        "software engineer", "software developer",
        "data analyst", "data engineer", "analytics",
        "ai", "artificial intelligence",
        "product manager", "business analyst", "consultant",
    ]
    if any(pt in title_lower for pt in priority_titles):
        score += 10

    # Location in BC
    if check_location_bc(location or ""):
        score += 10
    elif location and "remote" in location.lower():
        score += 5
    elif location and "canada" in location.lower():
        score += 3

    # Full-time
    if "full" in jtype_lower or "permanent" in jtype_lower:
        score += 5
    elif "contract" in jtype_lower or "temporary" in jtype_lower:
        score -= 15

    if "permanent" in desc_lower or "full-time" in desc_lower:
        score += 5

    # Experience level
    if "senior" in title_lower and "staff" not in title_lower and "principal" not in title_lower:
        score += 5
    elif "lead" in title_lower:
        score += 3
    elif "junior" in title_lower or "entry" in title_lower:
        score -= 5

    return min(100, max(0, round(score)))


def score_salary(salary_min: float, salary_max: float, interval: str) -> int:
    """Score salary level (0-100). Higher salary = higher BC PNP SIRS score."""
    if not salary_min and not salary_max:
        return 50

    if salary_min and salary_max:
        salary = (salary_min + salary_max) / 2
    elif salary_max:
        salary = salary_max
    else:
        salary = salary_min

    interval = (interval or "").lower()
    if "hour" in interval:
        salary = salary * 2080
    elif "month" in interval:
        salary = salary * 12

    if salary >= 145000:
        return 100
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


def score_company(company: str, description: str) -> int:
    """Score company reputation and size (0-100)."""
    company_lower = (company or "").lower().strip()
    if not company_lower:
        return 50

    for tier1 in COMPANY_TIERS["tier1"]:
        if tier1 in company_lower or company_lower in tier1:
            return 90

    for tier2 in COMPANY_TIERS["tier2"]:
        if tier2 in company_lower or company_lower in tier2:
            return 75

    desc_lower = (description or "").lower()
    if any(kw in desc_lower for kw in ["fortune 500", "global", "enterprise", "publicly traded"]):
        return 80
    elif any(kw in desc_lower for kw in ["series b", "series c", "series d", "well-funded"]):
        return 70
    elif any(kw in desc_lower for kw in ["startup", "early stage", "seed", "series a"]):
        return 55

    return 60


def score_interview_format(job: dict) -> tuple:
    """
    Score based on likelihood of live coding in the interview process.

    Higher score = less likely to have live coding = better for this user.

    Returns (score 0-100, details dict)
    """
    score = 50  # Neutral baseline
    details = {}

    title = (job.get("title") or "").lower()
    company = (job.get("company") or "").lower()
    description = (job.get("description") or "").lower()

    # ── ROLE-BASED SIGNALS ──

    # Roles that almost NEVER have live coding
    NO_CODING_ROLES = [
        "product manager", "program manager", "project manager",
        "management consultant", "strategy consultant", "consultant",
        "business analyst",
        "analytics manager", "analytics lead", "analytics director",
        "data strategy", "data governance",
        "operations analyst", "operations manager",
        "marketing analyst",
        "insights analyst", "insights manager",
        "chief", "coo", "cto", "vp ",
    ]
    role_matched = False
    for role in NO_CODING_ROLES:
        if role in title:
            score += 35
            details["role_type"] = f"+35 ('{role}' roles rarely have live coding)"
            role_matched = True
            break

    # Roles that USUALLY have live coding
    if not role_matched:
        HEAVY_CODING_ROLES = [
            "machine learning engineer", "ml engineer", "mle",
            "data engineer", "software engineer", "backend engineer",
            "full stack", "frontend engineer",
            "applied scientist",
            "research engineer",
        ]
        for role in HEAVY_CODING_ROLES:
            if role in title:
                score -= 30
                details["role_type"] = f"-30 ('{role}' roles almost always have live coding)"
                role_matched = True
                break

    # Roles that SOMETIMES have live coding
    if not role_matched:
        MIXED_ROLES = [
            "data scientist", "data analyst", "product analyst",
            "research scientist", "quantitative analyst",
            "bi analyst", "business intelligence",
        ]
        for role in MIXED_ROLES:
            if role in title:
                details["role_type"] = f"0 ('{role}' — interview format varies by company)"
                break

    # ── COMPANY-BASED SIGNALS ──

    for c in LIVE_CODING_COMPANIES:
        if c in company:
            score -= 20
            details["company_format"] = f"-20 ({c} is known for live coding interviews)"
            break
    else:
        for c in TAKEHOME_COMPANIES:
            if c in company:
                score += 15
                details["company_format"] = f"+15 ({c} typically uses take-home or discussion format)"
                break

    # ── JD TEXT SIGNALS ──

    # Positive signals (less likely to have live coding)
    if any(kw in description for kw in ["case study", "take-home", "take home",
                                         "presentation", "case presentation"]):
        score += 15
        details["jd_format_positive"] = "+15 (JD mentions case study / take-home / presentation)"

    if any(kw in description for kw in ["stakeholder", "cross-functional", "executive",
                                         "business partner", "strategic thinking"]):
        score += 10
        details["jd_business_focus"] = "+10 (JD emphasizes business/stakeholder skills over coding)"

    if any(kw in description for kw in ["tableau", "power bi", "looker", "dashboard",
                                         "visualization", "reporting"]):
        score += 8
        details["jd_bi_focus"] = "+8 (BI/visualization focus — less likely to test raw coding)"

    # Negative signals (more likely to have live coding)
    if any(kw in description for kw in ["leetcode", "hackerrank", "coderpad",
                                         "coding challenge", "coding assessment",
                                         "live coding", "technical screen",
                                         "whiteboard"]):
        score -= 25
        details["jd_coding_signal"] = "-25 (JD explicitly mentions coding test/assessment)"

    if any(kw in description for kw in ["system design", "design a system",
                                         "production code", "code review",
                                         "write efficient", "optimize query"]):
        score -= 15
        details["jd_engineering_signal"] = "-15 (JD has engineering/system design requirements)"

    if "strong programming" in description or "expert in python" in description:
        score -= 10
        details["jd_strong_coding"] = "-10 (JD requires strong/expert programming skills)"

    # ── INDUSTRY SIGNALS ──

    NON_TECH_KEYWORDS = [
        "healthcare", "hospital", "clinic", "pharma",
        "government", "public sector", "crown corporation",
        "insurance", "credit union", "bank",
        "retail", "fashion", "apparel",
        "real estate", "construction",
        "transportation", "transit", "logistics",
        "energy", "mining", "forestry",
        "nonprofit", "non-profit", "ngo",
        "university", "college", "education",
    ]
    for kw in NON_TECH_KEYWORDS:
        if kw in description or kw in company:
            score += 10
            details["industry"] = f"+10 (non-tech industry '{kw}' — typically lighter technical interviews)"
            break

    # Clamp 0-100
    score = max(0, min(100, score))

    return score, details


def calculate_success_score(job: dict) -> tuple:
    """
    Calculate realistic probability of getting an interview.
    Returns (score, details_dict).

    Factors (total 100 points):
    - Base: 40 points (everyone starts here)
    - Experience level match: +/- 20 points
    - Canadian experience barrier: -10 to -25 points
    - Company openness signals: +5 to +20 points
    - Competition level: -5 to -15 points
    - Niche advantage: +5 to +15 points
    - Networking potential: +5 to +15 points
    """
    score = 40  # Base score
    details = {}

    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    company = (job.get("company") or "").lower()
    location = (job.get("location") or "").lower()

    # --- Experience Level Match (+/- 20) ---
    if any(w in title for w in ["senior", "sr.", "sr "]):
        score += 5
        details["experience_match"] = "+5 (senior role, you have experience but overseas)"
    elif any(w in title for w in ["lead", "principal", "staff", "head", "director"]):
        score -= 5
        details["experience_match"] = "-5 (leadership role, usually needs local track record)"
    elif any(w in title for w in ["junior", "jr.", "associate", "entry"]):
        score += 10
        details["experience_match"] = "+10 (junior role, easy to qualify but may seem overqualified)"
    else:  # Mid-level
        score += 15
        details["experience_match"] = "+15 (mid-level role, good fit)"

    # --- Canadian Experience Barrier (-10 to -25) ---
    canadian_penalty = -15  # Default: significant barrier
    if "canadian experience" in description or "local experience" in description:
        canadian_penalty = -25
        details["canadian_exp"] = "-25 (JD explicitly requires Canadian experience)"
    elif "international" in description and ("welcome" in description or "valued" in description):
        canadian_penalty = -5
        details["canadian_exp"] = "-5 (JD welcomes international experience)"
    elif any(w in description for w in ["global", "cross-border", "multinational", "multilingual"]):
        canadian_penalty = -8
        details["canadian_exp"] = "-8 (role involves global work, your background is relevant)"
    elif "remote" in location:
        canadian_penalty = -10
        details["canadian_exp"] = "-10 (remote role, less local bias)"
    else:
        details["canadian_exp"] = "-15 (no signals about international candidates)"
    score += canadian_penalty

    # --- Company Openness Signals (+5 to +20) ---
    openness_bonus = 0
    if any(c in company for c in IMMIGRANT_FRIENDLY_COMPANIES):
        openness_bonus += 10
        details["company_openness"] = "+10 (company known to hire international talent)"

    # Diversity signals in JD
    diversity_keywords = [
        "diversity", "equity", "inclusion", "dei", "equal opportunity",
        "diverse backgrounds", "underrepresented", "belong",
    ]
    if any(kw in description for kw in diversity_keywords):
        openness_bonus += 5
        details["diversity_signal"] = "+5 (JD has diversity language)"

    # Visa/sponsorship signals
    if "visa sponsorship" in description or "work permit" in description:
        if "no visa" in description or "no sponsorship" in description or "not sponsor" in description:
            openness_bonus -= 10
            details["visa_signal"] = "-10 (explicitly won't sponsor)"
        else:
            openness_bonus += 5
            details["visa_signal"] = "+5 (mentions visa sponsorship positively)"

    score += openness_bonus

    # --- Competition Level (-5 to -15) ---
    if any(c in company for c in TIER1_COMPANIES):
        if "senior" in title or "lead" in title:
            score -= 15
            details["competition"] = "-15 (senior role at top company, extremely competitive)"
        else:
            score -= 8
            details["competition"] = "-8 (top company, competitive)"
    elif any(c in company for c in SMALL_COMPANIES_OR_STARTUPS):
        score -= 3
        details["competition"] = "-3 (smaller company, less competition)"
    else:
        score -= 5
        details["competition"] = "-5 (average competition)"

    # --- Niche Advantage (+5 to +15) ---
    niche_bonus = 0
    if "cybersecurity" in title and ("data" in title or "ml" in title or "machine learning" in description):
        niche_bonus += 10
        details["niche"] = "+10 (cybersecurity + DS is your unique niche)"
    if any(w in description for w in ["chinese market", "china", "apac", "asia pacific", "mandarin"]):
        niche_bonus += 10
        details["niche_china"] = "+10 (role values China/APAC experience)"
    if "quantitative" in title or "quant" in title:
        niche_bonus += 8
        details["niche_quant"] = "+8 (quantitative role matches your PE background)"
    if any(w in description for w in ["insurance", "insurtech"]):
        niche_bonus += 8
        details["niche_insurance"] = "+8 (insurance domain matches Shiyibei experience)"
    if any(w in description for w in ["graph neural", "gnn", "knowledge graph"]):
        niche_bonus += 10
        details["niche_gnn"] = "+10 (GNN expertise is rare, strong differentiator)"
    if "consulting" in title or "consultant" in title:
        niche_bonus += 8
        details["niche_consulting"] = "+8 (consulting role matches PwC background)"
    score += niche_bonus

    # --- Networking Potential (+5 to +15) ---
    networking_intel = generate_networking_intel(job.get("company", ""))
    networking_bonus = min(15, networking_intel["networking_score"])
    score += networking_bonus
    details["networking"] = f"+{networking_bonus} (networking potential at this company)"

    # Clamp to 0-100
    score = max(0, min(100, score))

    return score, details


def assign_tier(job: dict, scores: dict) -> str:
    """
    Assign tier considering interview format feasibility.

    Key change: Jobs with high live-coding probability are automatically
    Tier A (Stretch) or excluded, regardless of other scores.
    """
    interview_score = scores.get("score_interview", 50)
    success_score = scores.get("score_success", 50)

    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()

    # HARD RULE: If interview almost certainly has live coding → Tier A max
    if interview_score < 30:
        return "A"  # Stretch — only apply if you have a referral

    # HARD RULE: Roles that are purely engineering → Tier A
    engineering_roles = [
        "data engineer", "software engineer", "ml engineer",
        "machine learning engineer", "backend", "frontend",
        "platform engineer", "devops",
    ]
    if any(role in title for role in engineering_roles):
        return "A"

    # For remaining jobs, use combined signals
    stretch_signals = 0
    quickwin_signals = 0

    # Interview format contributes to tier
    if interview_score >= 70:
        quickwin_signals += 1  # Likely no live coding = easier path
    elif interview_score < 45:
        stretch_signals += 1  # Might have live coding = harder

    # Seniority and company signals
    if any(w in title for w in ["senior", "staff", "principal", "lead", "head"]):
        stretch_signals += 1
    if any(c in (job.get("company") or "").lower() for c in TIER1_COMPANIES):
        stretch_signals += 1
    if "canadian experience" in description:
        stretch_signals += 2

    if any(w in title for w in ["junior", "associate", "entry"]):
        quickwin_signals += 1
    if "contract" in (job.get("job_type") or "").lower():
        quickwin_signals += 1
    if any(w in title for w in ["product manager", "consultant", "business analyst"]):
        quickwin_signals += 1  # These roles don't have live coding

    # Small/mid companies
    if any(c in (job.get("company") or "").lower() for c in SMALL_COMPANIES_OR_STARTUPS):
        quickwin_signals += 1

    # Niche roles
    if any(w in title for w in ["cybersecurity", "insurance", "quant"]):
        quickwin_signals += 1

    # Tier assignment
    if stretch_signals >= 2 and quickwin_signals < 2:
        return "A"
    elif quickwin_signals >= 2 or success_score >= 60:
        return "C"
    else:
        return "B"


def rank_job(job: dict, skill_sets: dict = None) -> dict:
    """
    Score a single job and return updated dict with scores.

    Args:
        job: dict with keys: title, company, location, description,
             salary_min, salary_max, salary_interval, job_type
        skill_sets: pre-loaded skill sets (optional, loaded if None)

    Returns:
        Updated job dict with score fields added.
    """
    if skill_sets is None:
        skill_sets = _load_skill_sets()

    title = job.get("title", "")
    description = job.get("description", "")
    company = job.get("company", "")
    location = job.get("location", "")
    job_type = job.get("job_type", "")
    salary_min = job.get("salary_min") or 0
    salary_max = job.get("salary_max") or 0
    salary_interval = job.get("salary_interval", "yearly")

    # Guess NOC if not already set
    noc_code = job.get("noc_code", "")
    noc_desc = job.get("noc_description", "")
    if not noc_code:
        noc_code, noc_desc = guess_noc_from_title(title)

    # Compute scores
    s_skills = score_skills_match(title, description, skill_sets)
    s_immigration = score_immigration_fit(title, description, location, job_type, noc_code)
    s_salary = score_salary(salary_min, salary_max, salary_interval)
    s_company = score_company(company, description)

    # Interview format scoring (new)
    s_interview, interview_details = score_interview_format(job)

    # Realistic success scoring
    s_success, success_details = calculate_success_score(job)

    # Get networking score
    networking_intel = generate_networking_intel(company)
    networking_score = networking_intel["networking_score"]

    total = round(
        s_skills * WEIGHTS["skills_match"] +
        s_immigration * WEIGHTS["immigration_fit"] +
        s_interview * WEIGHTS["interview_format"] +
        s_salary * WEIGHTS["salary_score"] +
        s_company * WEIGHTS["company_score"] +
        s_success * WEIGHTS["success_probability"],
        1,
    )

    if total >= 75:
        priority = "HIGH"
    elif total >= 55:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    # Assign tier
    scores_dict = {
        "score_skills": s_skills,
        "score_success": s_success,
        "score_interview": s_interview,
        "score_total": total,
    }
    tier = assign_tier(job, scores_dict)

    job.update({
        "score_skills": s_skills,
        "score_immigration": s_immigration,
        "score_salary": s_salary,
        "score_company": s_company,
        "score_success": s_success,
        "score_interview": s_interview,
        "score_total": total,
        "priority": priority,
        "noc_code": noc_code,
        "noc_description": noc_desc,
        "bcpnp_eligible": 1 if is_bcpnp_eligible(noc_code) else 0,
        "tier": tier,
        "networking_score": networking_score,
        "networking_notes": json.dumps(networking_intel.get("networking_tips", [])),
        "success_details": json.dumps(success_details),
        "interview_format_details": json.dumps(interview_details),
    })

    return job


def rank_jobs(jobs: list[dict]) -> list[dict]:
    """Score and rank a list of jobs. Returns sorted list (highest score first)."""
    skill_sets = _load_skill_sets()
    ranked = [rank_job(job, skill_sets) for job in jobs]
    ranked.sort(key=lambda j: j.get("score_total", 0), reverse=True)
    return ranked
