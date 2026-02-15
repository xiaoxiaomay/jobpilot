# System Update: Interview Format Awareness + Expanded Role Targeting

## Background

The user's coding ability is limited: can read SQL/Python, can modify code with AI assistance, but CANNOT write code from scratch in a live setting. This means:
- ❌ Will fail any live coding interview (whiteboard, CoderPad, HackerRank)
- ✅ Can excel at take-home case studies (3-7 days, AI-assisted)
- ✅ Can handle verbal/conceptual technical discussions
- ✅ Strongest at: business case interviews, behavioral, strategy, product sense, presentation

This is a fundamental constraint that must be built into the ranking system.

## Change 1: Add Interview Format Scoring

### New scoring dimension: `score_interview_format` (weight: 15%)

Redistribute weights to accommodate:

**OLD weights:**
| Dimension | Weight |
|-----------|--------|
| Skills Match | 40% |
| Immigration | 25% |
| Salary | 15% |
| Company | 10% |
| Success | 10% |

**NEW weights:**
| Dimension | Weight |
|-----------|--------|
| Skills Match | 30% |
| Immigration | 25% |
| Interview Format | 15% |
| Salary | 10% |
| Company | 10% |
| Success | 10% |

### Implementation in `core/ranker.py`

```python
def score_interview_format(job: dict) -> tuple[float, dict]:
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
    
    # ============================================================
    # ROLE-BASED SIGNALS
    # ============================================================
    
    # Roles that almost NEVER have live coding
    NO_CODING_ROLES = [
        "product manager", "program manager", "project manager",
        "management consultant", "strategy consultant", "consultant",
        "business analyst",  # non-technical BA
        "analytics manager", "analytics lead", "analytics director",
        "data strategy", "data governance",
        "operations analyst", "operations manager",
        "marketing analyst",  # usually more tools-based
        "insights analyst", "insights manager",
        "chief", "coo", "cto", "vp ",  # executive roles
    ]
    for role in NO_CODING_ROLES:
        if role in title:
            score += 35
            details["role_type"] = f"+35 ('{role}' roles rarely have live coding)"
            break
    
    # Roles that USUALLY have live coding
    HEAVY_CODING_ROLES = [
        "machine learning engineer", "ml engineer", "mle",
        "data engineer", "software engineer", "backend engineer",
        "full stack", "frontend engineer",
        "applied scientist",  # at FAANG = live coding
        "research engineer",
    ]
    for role in HEAVY_CODING_ROLES:
        if role in title:
            score -= 30
            details["role_type"] = f"-30 ('{role}' roles almost always have live coding)"
            break
    
    # Roles that SOMETIMES have live coding (depends on company)
    MIXED_ROLES = [
        "data scientist", "data analyst", "product analyst",
        "research scientist", "quantitative analyst",
        "bi analyst", "business intelligence",
    ]
    for role in MIXED_ROLES:
        if role in title:
            # Don't change score here — let company signals determine
            details["role_type"] = f"0 ('{role}' — interview format varies by company)"
            break
    
    # ============================================================
    # COMPANY-BASED SIGNALS
    # ============================================================
    
    # Companies KNOWN to do live coding for DS/DA roles
    LIVE_CODING_COMPANIES = [
        "google", "meta", "amazon", "apple", "netflix",
        "microsoft",  # depends on team but usually yes
        "uber", "airbnb", "stripe", "doordash", "instacart",
        "databricks", "snowflake", "palantir",
        "linkedin",
    ]
    for c in LIVE_CODING_COMPANIES:
        if c in company:
            score -= 20
            details["company_format"] = f"-20 ({c} is known for live coding interviews)"
            break
    
    # Companies that typically use TAKE-HOME or DISCUSSION format
    TAKEHOME_COMPANIES = [
        # Vancouver mid-size tech
        "hootsuite", "later", "clio", "bench", "copperleaf",
        "visier", "absolute", "eventbase", "finger food",
        "grow", "thinkific", "trulioo", "benevity",
        # Vancouver non-tech (tend to be less coding-heavy)
        "lululemon", "aritzia", "london drugs",
        "translink", "icbc", "bc hydro", "worksafe",
        "first west", "vancity", "coast capital",
        "phsa", "vancouver coastal health", "bc cancer",
        "city of vancouver",
        # Consulting firms (case interview, no coding)
        "deloitte", "ey", "kpmg", "accenture", "bdo",
        "bain", "bcg",  # PwC excluded since user worked there
        # Banks (varies but BA/PM roles usually no live coding)
        "rbc", "td", "bmo", "cibc", "scotiabank", "hsbc",
    ]
    for c in TAKEHOME_COMPANIES:
        if c in company:
            score += 15
            details["company_format"] = f"+15 ({c} typically uses take-home or discussion format)"
            break
    
    # ============================================================
    # JD TEXT SIGNALS
    # ============================================================
    
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
        details["jd_coding_signal"] = "-25 (JD explicitly mentions coding test/assessment ⛔)"
    
    if any(kw in description for kw in ["system design", "design a system",
                                         "production code", "code review",
                                         "write efficient", "optimize query"]):
        score -= 15
        details["jd_engineering_signal"] = "-15 (JD has engineering/system design requirements)"
    
    if "strong programming" in description or "expert in python" in description:
        score -= 10
        details["jd_strong_coding"] = "-10 (JD requires strong/expert programming skills)"
    
    # ============================================================
    # INDUSTRY SIGNALS
    # ============================================================
    
    # Non-tech industries typically have easier technical interviews
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
```

### Add to database

```sql
ALTER TABLE jobs ADD COLUMN score_interview REAL DEFAULT 50;
ALTER TABLE jobs ADD COLUMN interview_format_details TEXT DEFAULT '';
```

### Display in Job Pool

Show interview format score as a progress bar in the score breakdown:
- 80-100: 🟢 "Likely no live coding"
- 50-79: 🟡 "Format unknown — check Glassdoor"
- 0-49: 🔴 "Likely has live coding"

Add a Glassdoor interview search link:
```python
glassdoor_url = f"https://www.glassdoor.ca/Interview/{company_encoded}-interview-questions-SRCH_KE0,{len(company)}.htm"
st.link_button("🔍 Check interview format on Glassdoor", glassdoor_url)
```

---

## Change 2: Expand Target Roles

### Update `data/scraper_config.json`

Add new search queries for roles that don't require live coding:

```json
{
  "search_queries": [
    "data scientist",
    "data analyst",
    "product analyst",
    "machine learning",
    "product manager data",
    "technical product manager",
    "product manager AI",
    "product manager analytics",
    "business analyst data",
    "analytics manager",
    "insights analyst",
    "BI analyst",
    "business intelligence analyst",
    "strategy consultant",
    "management consultant data",
    "data strategy",
    "AI consultant",
    "analytics consultant"
  ],
  "location": "Vancouver, BC, Canada",
  "distance": 50,
  "sites": ["linkedin", "indeed", "glassdoor", "zip_recruiter"],
  "hours_old": 72,
  "results_wanted": 25,
  "exclude_keywords": [
    "intern", "internship", "co-op", "coop",
    "director", "vp", "vice president",
    "data engineer", "software engineer", "ml engineer",
    "machine learning engineer", "backend", "frontend",
    "full stack", "devops", "sre", "platform engineer"
  ]
}
```

**IMPORTANT**: Note that "data engineer", "software engineer", "ml engineer" etc. are now in the EXCLUDE list. These roles almost always require live coding.

### Update `core/immigration.py` — Add new NOC codes

```python
# Expanded NOC mapping
TITLE_TO_NOC = {
    # Data roles (existing)
    "data scientist": "21211",
    "machine learning": "21211",
    "applied scientist": "21211",
    "research scientist": "21211",
    "data analyst": "21223",
    "business intelligence": "21223",
    "bi analyst": "21223",
    "database": "21223",
    
    # Product roles (NEW)
    "product manager": "20012",
    "technical product manager": "20012",
    "program manager": "20012",
    "it project manager": "20012",
    
    # Business/Consulting roles (NEW)
    "business analyst": "21221",
    "systems analyst": "21221",
    "management consultant": "11201",
    "strategy consultant": "11201",
    "consultant": "11201",
    "analytics manager": "20012",
    "insights analyst": "21221",
    
    # Cybersecurity (existing)
    "cybersecurity": "21220",
    "security analyst": "21220",
    "information security": "21220",
    
    # Software (for filtering out)
    "software engineer": "21231",
    "data engineer": "21231",
    "ml engineer": "21231",
}

# Update BC PNP Tech list to include new NOCs
BCPNP_TECH_NOCS = {
    "20012",  # Computer and information systems managers (includes PM)
    "21211",  # Data scientists
    "21220",  # Cybersecurity specialists
    "21221",  # Business systems specialists (includes BA)
    "21222",  # Information systems specialists
    "21223",  # Database analysts and data administrators
    "21230",  # Computer systems developers and programmers
    "21231",  # Software engineers and designers
    "21232",  # Software developers and programmers
    "21233",  # Web designers
    "21234",  # Web developers and programmers
    "21311",  # Computer engineers
    "22220",  # Computer network and web technicians
    "22222",  # Information systems testing technicians
}

# NOCs that are BC PNP eligible but NOT on Tech priority list
BCPNP_NON_TECH_ELIGIBLE = {
    "11201",  # Professional occupations in business management consulting
    # These go through regular BC PNP (not Tech stream) — slower but still works
}
```

### Update `data/master_profile.json` — Add new role templates

Add these to the `summary_templates` section:

```json
{
  "summary_templates": {
    "data_scientist": "... (existing) ...",
    "ai_consultant": "... (existing) ...",
    "product_analyst": "... (existing) ...",
    "data_analyst": "... (existing) ...",
    
    "product_manager": "Product Manager with 10+ years of experience driving data-driven product strategy across insurance, mobility, and fintech sectors. Led end-to-end product development of AI-powered sales platforms (MetLife: 2.5x conversion increase), marketplace optimization at Uber China (5%→30% market share), and NLP-based customer-facing tools. Combines deep analytical skills (Peking University Mathematics) with business acumen (PwC management consulting) and cross-functional leadership. Currently pursuing M.S. in Computer Science (Cybersecurity) at NYIT Vancouver.",

    "business_analyst": "Business Analyst with 10+ years of experience in requirements analysis, process optimization, and data-driven decision support across consulting, technology, and financial services. Expert in stakeholder management, cross-functional collaboration, and translating complex business needs into actionable solutions. Background includes M&A due diligence and integration at PwC (Haier-Sanyo acquisition across 9 entities), growth analytics at Uber China, and AI platform product development. Peking University Mathematics graduate, currently pursuing M.S. in Computer Science at NYIT Vancouver.",

    "analytics_manager": "Analytics Manager with 10+ years of experience building and leading data analytics functions across finance, technology, and consulting. Proven track record of designing experimentation frameworks (A/B testing, causal inference), building KPI dashboards, and translating analytical insights into executive-level recommendations. Led quantitative research teams at a private equity fund and growth analytics at Uber China. PwC management consulting background with expertise in cross-border M&A and strategic advisory. Peking University Mathematics, M.S. Computer Science (NYIT Vancouver).",

    "management_consultant": "Management Consultant with 10+ years of cross-industry experience spanning M&A advisory, growth strategy, operational optimization, and AI/data transformation. At PwC, led Haier's acquisition of Sanyo (2012 China M&A Service Award), including due diligence across 9 entities, $31M pension negotiation, and post-deal integration across 18 countries. Subsequently drove data-driven growth at Uber China (5%→30% market share) and built AI-powered business platforms for insurance (MetLife, Sequoia-backed). Combines analytical rigor (Peking University Mathematics) with hands-on technology expertise."
  }
}
```

---

## Change 3: Update Tier Assignment Logic

Update `assign_tier()` in `core/ranker.py` to incorporate interview format:

```python
def assign_tier(job: dict, scores: dict) -> str:
    """
    Assign tier considering interview format feasibility.
    
    Key change: Jobs with high live-coding probability are automatically 
    Tier A (Stretch) or excluded, regardless of other scores.
    """
    interview_score = scores.get("score_interview", 50)
    success_score = scores.get("score_success", 50)
    skills_score = scores.get("score_skills", 50)
    
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    
    # HARD RULE: If interview almost certainly has live coding → Tier A max
    if interview_score < 30:
        return "A"  # Stretch — only apply if you have a referral
    
    # HARD RULE: Roles that are purely engineering → Tier A
    engineering_roles = ["data engineer", "software engineer", "ml engineer", 
                        "machine learning engineer", "backend", "frontend",
                        "platform engineer", "devops"]
    if any(role in title for role in engineering_roles):
        return "A"
    
    # For remaining jobs, use the existing logic but factor in interview format
    stretch_signals = 0
    quickwin_signals = 0
    
    # Interview format contributes to tier
    if interview_score >= 70:
        quickwin_signals += 1  # Likely no live coding = easier path
    elif interview_score < 45:
        stretch_signals += 1  # Might have live coding = harder
    
    # Seniority and company signals (existing logic)
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
```

---

## Change 4: Add Interview Format Filter to Job Pool

In `pages/1_🔍_Job_Pool.py`, add to the sidebar filters:

```python
# Interview Format Filter
interview_filter = st.select_slider(
    "Interview Coding Risk",
    options=["All", "Low Risk Only", "No Live Coding"],
    value="All",
    help="Filter jobs by likelihood of live coding in interviews"
)

# Apply filter
if interview_filter == "Low Risk Only":
    df = df[df["score_interview"] >= 50]
elif interview_filter == "No Live Coding":
    df = df[df["score_interview"] >= 70]
```

---

## Change 5: Add "Role Type" Quick Filter

Add a role type filter at the top of Job Pool:

```python
role_filter = st.multiselect(
    "Target Roles",
    options=["Data Scientist", "Data Analyst", "Product Manager", 
             "Business Analyst", "Consultant", "Analytics Manager", 
             "BI Analyst", "Other"],
    default=["Data Scientist", "Data Analyst", "Product Manager", 
             "Business Analyst", "Consultant", "Analytics Manager", "BI Analyst"],
    help="Select which role types to show"
)
```

---

## Change 6: Update Apply Page Role Types

In `pages/2_📝_Apply.py`, update the "Target role type" dropdown:

```python
role_type = st.selectbox(
    "Target role type",
    options=[
        "Data Scientist / ML Engineer",
        "Data Analyst / BI Analyst",
        "Product Analyst",
        "Product Manager",            # NEW
        "Business Analyst",            # NEW
        "Analytics Manager",           # NEW
        "Management Consultant",       # NEW
        "AI / Data Consultant",
    ]
)
```

Map these to the summary templates in master_profile.json:
```python
ROLE_TO_TEMPLATE = {
    "Data Scientist / ML Engineer": "data_scientist",
    "Data Analyst / BI Analyst": "data_analyst",
    "Product Analyst": "product_analyst",
    "Product Manager": "product_manager",
    "Business Analyst": "business_analyst",
    "Analytics Manager": "analytics_manager",
    "Management Consultant": "management_consultant",
    "AI / Data Consultant": "ai_consultant",
}
```

---

## Change 7: Weekly Application Strategy Update

Update the recommended weekly plan at top of Job Pool:

```
📋 Recommended Weekly Application Plan:

🎯 Tier A — Stretch (2-3/week): Senior DS at big tech
   → Strategy: Network first, apply only with referral
   → These likely have live coding — only apply if you find a champion
   
✅ Tier B — Sweet Spot (5-7/week): Mid-level DA/DS at mid-size companies, PM roles
   → Strategy: Generate tailored resume + cover letter, apply directly
   → Check Glassdoor for interview format before applying
   
🟢 Tier C — Quick Win (3-5/week): BA, Consultant, junior DA, contract roles
   → Strategy: Fast applications, use "Accessible" resume tone
   → These rarely have live coding — highest interview probability

💡 Pro Tip: For Tier B, always check Glassdoor interview reviews first. 
   If the company uses take-home case studies, it's effectively a Tier C for you.
```

---

## Summary of ALL Changes

| # | Change | Files | Purpose |
|---|--------|-------|---------|
| 1 | Interview format scoring | `core/ranker.py`, DB | New 15% weight dimension: live coding likelihood |
| 2 | Expanded target roles | `data/scraper_config.json`, `core/immigration.py` | Add PM, BA, Consultant; exclude engineering roles |
| 3 | Updated tier assignment | `core/ranker.py` | Factor in interview format; auto-Tier-A for coding-heavy roles |
| 4 | Interview format filter | `pages/1_*.py` | Sidebar filter for coding risk level |
| 5 | Role type filter | `pages/1_*.py` | Quick filter by role category |
| 6 | New role types in Apply | `pages/2_*.py`, `data/master_profile.json` | PM, BA, Consultant resume templates |
| 7 | Updated weekly plan | `pages/1_*.py` | Interview-aware application strategy |

## Testing

After implementing:
1. Reload sample data — verify "Data Engineer" and "ML Engineer" roles are Tier A with low interview score
2. Verify "Product Manager" and "Business Analyst" roles get high interview format scores (70+)
3. Verify "Data Scientist at Google" gets low interview score vs "Data Analyst at TransLink" gets high
4. Generate resume for "Product Manager" role type — verify it uses the PM summary template
5. Check that scraper exclude list filters out engineering roles
6. Verify Glassdoor interview search link appears in job detail panel
7. Check that the "No Live Coding" filter works correctly
