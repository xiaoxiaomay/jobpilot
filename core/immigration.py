"""
BC PNP Tech pathway logic.
Maps job titles to NOC codes and checks BC PNP Tech eligibility.
"""

# BC PNP Tech Priority Occupations (2025-2026)
BCPNP_TECH_NOCS = {
    "20012",  # Computer and Information Systems Managers (includes PM)
    "21211",  # Data Scientists
    "21220",  # Cybersecurity Specialists
    "21221",  # Business Systems Specialists (includes BA)
    "21222",  # Information Systems Specialists
    "21223",  # Database Analysts and Data Administrators
    "21230",  # Computer Systems Developers and Programmers
    "21231",  # Software Engineers and Designers
    "21232",  # Software Developers
    "21233",  # Web Designers
    "21234",  # Web Developers and Programmers
    "21311",  # Computer Engineers
    "22220",  # Computer Network and Web Technicians
    "22222",  # Information Systems Testing Technicians
}

# NOCs that are BC PNP eligible but NOT on Tech priority list
BCPNP_NON_TECH_ELIGIBLE = {
    "11201",  # Professional occupations in business management consulting
    # These go through regular BC PNP (not Tech stream) — slower but still works
}

NOC_DESCRIPTIONS = {
    "20012": "Computer and Information Systems Managers",
    "21211": "Data Scientists",
    "21220": "Cybersecurity Specialists",
    "21221": "Business Systems Specialists",
    "21222": "Information Systems Specialists",
    "21223": "Database Analysts and Data Administrators",
    "21230": "Computer Systems Developers and Programmers",
    "21231": "Software Engineers and Designers",
    "21232": "Software Developers",
    "21233": "Web Designers",
    "21234": "Web Developers and Programmers",
    "21311": "Computer Engineers",
    "22220": "Computer Network and Web Technicians",
    "22222": "Information Systems Testing Technicians",
    "11201": "Professional Occupations in Business Management Consulting",
}

# Map job title keywords to NOC codes
TITLE_TO_NOC = {
    # Data roles
    "data scientist": "21211",
    "machine learning": "21211",
    "applied scientist": "21211",
    "research scientist": "21211",
    "ai engineer": "21211",
    "ai scientist": "21211",
    "deep learning": "21211",
    "nlp engineer": "21211",
    "data analyst": "21223",
    "business intelligence": "21223",
    "bi analyst": "21223",
    "database": "21223",
    "analytics engineer": "21223",

    # Product roles
    "product manager": "20012",
    "technical product manager": "20012",
    "program manager": "20012",
    "it project manager": "20012",
    "analytics manager": "20012",

    # Business/Consulting roles
    "business analyst": "21221",
    "systems analyst": "21221",
    "product analyst": "21221",
    "ai consultant": "21221",
    "insights analyst": "21221",
    "management consultant": "11201",
    "strategy consultant": "11201",
    "consultant": "11201",

    # Cybersecurity
    "cybersecurity": "21220",
    "security analyst": "21220",
    "security engineer": "21220",
    "information security": "21220",
    "soc analyst": "21220",
    "threat analyst": "21220",

    # Software (for filtering/scoring)
    "software engineer": "21231",
    "software developer": "21231",
    "data engineer": "21231",
    "ml engineer": "21231",
    "backend engineer": "21231",
    "full stack": "21232",
    "frontend engineer": "21234",
    "web developer": "21234",
}

# BC median wage threshold for PNP SIRS scoring
BC_MEDIAN_HOURLY_WAGE = 38.46  # ~$80K/yr


def guess_noc_from_title(title: str) -> tuple[str, str]:
    """
    Guess NOC code from job title.

    Returns:
        (noc_code, noc_description) or ("", "") if no match.
    """
    title_lower = title.lower().strip()
    for keyword, noc in TITLE_TO_NOC.items():
        if keyword in title_lower:
            return noc, NOC_DESCRIPTIONS.get(noc, "")
    return "", ""


def is_bcpnp_eligible(noc_code: str) -> bool:
    """Check if a NOC code is in the BC PNP Tech priority list."""
    return noc_code in BCPNP_TECH_NOCS


def is_bcpnp_any_eligible(noc_code: str) -> bool:
    """Check if a NOC code is eligible for any BC PNP stream (Tech or non-Tech)."""
    return noc_code in BCPNP_TECH_NOCS or noc_code in BCPNP_NON_TECH_ELIGIBLE


def check_location_bc(location: str) -> bool:
    """Check if the job location is in British Columbia."""
    if not location:
        return False
    loc_lower = location.lower()
    bc_indicators = [
        "vancouver", "burnaby", "surrey", "richmond", "bc",
        "british columbia", "victoria", "kelowna", "kamloops",
        "nanaimo", "new westminster", "coquitlam", "langley",
        "abbotsford", "north vancouver", "west vancouver",
    ]
    return any(ind in loc_lower for ind in bc_indicators)


def salary_to_annual(salary: float, interval: str) -> float:
    """Convert salary to annual based on interval."""
    if not salary or not interval:
        return 0
    interval_lower = interval.lower()
    if "hour" in interval_lower:
        return salary * 2080
    elif "month" in interval_lower:
        return salary * 12
    elif "week" in interval_lower:
        return salary * 52
    return salary  # assume yearly


def salary_above_median(salary_annual: float) -> bool:
    """Check if salary is above BC median wage (better for PNP SIRS score)."""
    return salary_annual >= BC_MEDIAN_HOURLY_WAGE * 2080


def get_immigration_summary(jobs_data: list[dict]) -> dict:
    """
    Generate immigration pathway summary from a list of jobs.

    Returns dict with NOC distribution, PNP eligibility counts, salary analysis.
    """
    noc_counts = {}
    pnp_eligible = 0
    above_median = 0
    total = len(jobs_data)

    for job in jobs_data:
        noc = job.get("noc_code", "")
        if noc:
            noc_label = f"{noc} — {NOC_DESCRIPTIONS.get(noc, 'Unknown')}"
            noc_counts[noc_label] = noc_counts.get(noc_label, 0) + 1

        if job.get("bcpnp_eligible"):
            pnp_eligible += 1

        salary_min = job.get("salary_min") or 0
        salary_max = job.get("salary_max") or 0
        interval = job.get("salary_interval", "yearly")
        mid_salary = ((salary_min + salary_max) / 2) if salary_min and salary_max else salary_min or salary_max
        if mid_salary and salary_above_median(salary_to_annual(mid_salary, interval)):
            above_median += 1

    return {
        "total_jobs": total,
        "noc_distribution": noc_counts,
        "pnp_eligible_count": pnp_eligible,
        "pnp_eligible_pct": round(pnp_eligible / total * 100, 1) if total else 0,
        "above_median_wage": above_median,
        "above_median_pct": round(above_median / total * 100, 1) if total else 0,
    }
