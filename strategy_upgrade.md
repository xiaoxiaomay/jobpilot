# Feature Request: Tiered Application Strategy + Realistic Success Scoring + Networking Intelligence

## Background

The user has 10+ years of experience but ZERO Canadian work experience. Currently the system ranks jobs purely by "how good is the job for me" but ignores "how likely am I to actually get this job." This leads to wasted effort applying to senior roles at top companies that will never interview someone without local experience.

We need to fundamentally rethink the ranking and application strategy.

## Change 1: Tiered Application Strategy

### Concept

Instead of one score, jobs should be categorized into 3 tiers based on REALISTIC probability of getting an interview:

| Tier | Description | Strategy | Resume Approach | Weekly Target |
|------|-------------|----------|-----------------|---------------|
| 🎯 **Tier A: Stretch** | Dream jobs at top companies. Senior roles. | Apply selectively, focus on networking + referrals | Full experience, highlight leadership | 2-3 per week |
| ✅ **Tier B: Sweet Spot** | Mid-level roles where your skills match well and company likely open to international experience | Primary focus, highest volume | Balanced, emphasize technical depth | 5-7 per week |
| 🟢 **Tier C: Quick Win** | Junior/mid roles, smaller companies, contract positions, roles explicitly welcoming diverse backgrounds | Apply fast, get local experience ASAP | Tone down seniority, emphasize hands-on technical work | 3-5 per week |

### Implementation in `core/ranker.py`

Add a new function `assign_tier(job, scores)` that runs AFTER the existing scoring:

```python
def assign_tier(job: dict, scores: dict) -> str:
    """
    Assign application tier based on realistic interview probability.
    
    Tier A (Stretch): Great job but low interview probability
    Tier B (Sweet Spot): Good fit AND reasonable interview probability  
    Tier C (Quick Win): Maybe not the dream job but high interview probability
    """
    skills_score = scores.get("score_skills", 0)
    success_score = scores.get("score_success", 0)  # Updated success score (see Change 2)
    total_score = scores.get("score_total", 0)
    
    title = (job.get("title") or "").lower()
    company = (job.get("company") or "").lower()
    description = (job.get("description") or "").lower()
    salary_min = job.get("salary_min") or 0
    
    # Signals that make a job harder to get (Tier A indicators)
    stretch_signals = 0
    if any(w in title for w in ["senior", "staff", "principal", "lead", "head", "director"]):
        stretch_signals += 1
    if any(w in company for w in TIER1_COMPANIES):  # FAANG, big banks, Lululemon etc.
        stretch_signals += 1
    if salary_min and salary_min > 140000:
        stretch_signals += 1
    if "canadian experience" in description or "local experience" in description:
        stretch_signals += 2
    if any(w in description for w in ["5+ years", "7+ years", "10+ years"]):
        if "senior" in title or "lead" in title:
            stretch_signals += 1
    
    # Signals that make a job easier to get (Tier C indicators)
    quickwin_signals = 0
    if any(w in title for w in ["junior", "associate", "analyst", "entry"]):
        quickwin_signals += 1
    if "contract" in (job.get("job_type") or "").lower():
        quickwin_signals += 1
    if any(w in description for w in ["diverse backgrounds", "international experience welcome", 
                                       "newcomers", "open to candidates", "no experience required",
                                       "willing to train", "bootcamp"]):
        quickwin_signals += 1
    if any(w in company for w in SMALL_COMPANIES_OR_STARTUPS):
        quickwin_signals += 1
    if salary_min and salary_min < 80000:
        quickwin_signals += 1
    # Less competition: niche roles combining DS + other domain
    if any(w in title for w in ["cybersecurity", "bioinformatics", "quant"]):
        quickwin_signals += 1
    
    # Tier assignment logic
    if stretch_signals >= 2 and success_score < 60:
        return "A"  # Stretch
    elif quickwin_signals >= 2 or success_score >= 75:
        return "C"  # Quick Win
    else:
        return "B"  # Sweet Spot

# Company lists
TIER1_COMPANIES = [
    "amazon", "google", "microsoft", "meta", "apple", "netflix",
    "lululemon", "shopify", "rbc", "td", "bmo", "cibc", "scotiabank",
    "telus", "bchydro", "bc hydro", "deloitte", "pwc", "ey", "kpmg",
    "mckinsey", "bain", "bcg", "accenture"
]

SMALL_COMPANIES_OR_STARTUPS = [
    "bench", "clio", "hootsuite", "later", "absolute", "d-wave",
    "copperleaf", "eventbase", "finger food", "grow",
    # Add more as you discover them
]
```

### Add tier to database

```sql
ALTER TABLE jobs ADD COLUMN tier TEXT DEFAULT 'B';  -- A, B, C
```

### Display tier in Job Pool page

In `pages/1_🔍_Job_Pool.py`, add tier column and tier filter:
- 🎯 Tier A (Stretch) — shown in purple
- ✅ Tier B (Sweet Spot) — shown in green  
- 🟢 Tier C (Quick Win) — shown in blue

Add a recommended weekly plan box at the top:
```
📋 This Week's Application Plan:
   🎯 Tier A (Stretch): 2 jobs — focus on networking first
   ✅ Tier B (Sweet Spot): 5 jobs — your primary targets
   🟢 Tier C (Quick Win): 3 jobs — fast applications to build momentum
```

---

## Change 2: Realistic Success Scoring (Overhaul `score_success`)

The current success score is too optimistic. Rewrite it to account for the REAL barriers an immigrant without Canadian experience faces.

### New Success Score Formula (0-100)

```python
def calculate_success_score(job: dict, profile: dict) -> tuple[float, dict]:
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
    - Networking potential: +5 to +15 points (see Change 3)
    """
    score = 40  # Base score
    details = {}
    
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    company = (job.get("company") or "").lower()
    location = (job.get("location") or "").lower()
    
    # --- Experience Level Match (+/- 20) ---
    if any(w in title for w in ["senior", "sr.", "sr "]):
        # Senior roles: user has 10+ years, but all overseas
        score += 5  # Partial match
        details["experience_match"] = "+5 (senior role, you have experience but overseas)"
    elif any(w in title for w in ["lead", "principal", "staff", "head", "director"]):
        score -= 5  # These usually need proven local track record
        details["experience_match"] = "-5 (leadership role, usually needs local track record)"
    elif any(w in title for w in ["junior", "jr.", "associate", "entry"]):
        score += 10  # But risk of overqualification
        details["experience_match"] = "+10 (junior role, easy to qualify but may seem overqualified)"
    else:  # Mid-level
        score += 15
        details["experience_match"] = "+15 (mid-level role, good fit)"
    
    # --- Canadian Experience Barrier (-10 to -25) ---
    canadian_penalty = -15  # Default: significant barrier
    if "canadian experience" in description or "local experience" in description:
        canadian_penalty = -25
        details["canadian_exp"] = "-25 (JD explicitly requires Canadian experience ⛔)"
    elif "international" in description and ("welcome" in description or "valued" in description):
        canadian_penalty = -5
        details["canadian_exp"] = "-5 (JD welcomes international experience ✅)"
    elif any(w in description for w in ["global", "cross-border", "multinational", "multilingual"]):
        canadian_penalty = -8
        details["canadian_exp"] = "-8 (role involves global work, your background is relevant)"
    elif "remote" in location.lower():
        canadian_penalty = -10
        details["canadian_exp"] = "-10 (remote role, less local bias)"
    else:
        details["canadian_exp"] = "-15 (no signals about international candidates)"
    score += canadian_penalty
    
    # --- Company Openness Signals (+5 to +20) ---
    openness_bonus = 0
    # Companies known to hire internationally in Vancouver
    IMMIGRANT_FRIENDLY_COMPANIES = [
        "amazon", "microsoft", "google", "meta", "apple",
        "shopify", "clio", "d-wave", "hootsuite",
        "rbc", "td", "deloitte", "ey", "pwc", "kpmg",
        "phsa", "vancouver coastal health", "bc cancer",
        # Tech companies with known H1B/LMIA track records
    ]
    if any(c in company for c in IMMIGRANT_FRIENDLY_COMPANIES):
        openness_bonus += 10
        details["company_openness"] = "+10 (company known to hire international talent)"
    
    # Diversity signals in JD
    diversity_keywords = ["diversity", "equity", "inclusion", "dei", "equal opportunity",
                         "diverse backgrounds", "underrepresented", "belong"]
    if any(kw in description for kw in diversity_keywords):
        openness_bonus += 5
        details["diversity_signal"] = "+5 (JD has diversity language)"
    
    # Visa/sponsorship signals
    if "visa sponsorship" in description or "work permit" in description:
        if "no visa" in description or "no sponsorship" in description or "not sponsor" in description:
            openness_bonus -= 10
            details["visa_signal"] = "-10 (explicitly won't sponsor ⛔)"
        else:
            openness_bonus += 5
            details["visa_signal"] = "+5 (mentions visa sponsorship positively)"
    
    score += openness_bonus
    
    # --- Competition Level (-5 to -15) ---
    # Senior + big company = very competitive
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
    # Roles where user's unique background is a competitive advantage
    niche_bonus = 0
    if "cybersecurity" in title and ("data" in title or "ml" in title or "machine learning" in description):
        niche_bonus += 10  # DS + Cybersecurity is rare combination
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
    
    # Clamp to 0-100
    score = max(0, min(100, score))
    
    return score, details
```

### Show success score details in Job Pool

When user expands a job in Job Pool, show the success score breakdown alongside the existing score bars. This helps them understand WHY a job is rated easy or hard to get.

---

## Change 3: Networking Intelligence (LinkedIn Alumni Detection)

### Concept

For each company in the job pool, check if there are potential networking connections:
- Peking University (北京大学/PKU) alumni
- NYIT alumni  
- Chinese-origin professionals (by checking common Chinese surnames in leadership/DS roles)
- Former Uber employees
- Former PwC employees

This data helps the user know WHERE to spend networking effort.

### Implementation

Add a new field to the jobs table:

```sql
ALTER TABLE jobs ADD COLUMN networking_notes TEXT DEFAULT '';
ALTER TABLE jobs ADD COLUMN networking_score INTEGER DEFAULT 0;  -- 0-15 bonus points
```

Add a new module `core/networking.py`:

```python
"""
Networking Intelligence Module

Generates LinkedIn search URLs and networking recommendations
for each company in the job pool.

NOTE: This does NOT scrape LinkedIn. It generates search URLs
that the user can manually open to find connections.
"""

def generate_networking_intel(company: str, location: str = "Vancouver") -> dict:
    """
    Generate LinkedIn search URLs and networking recommendations.
    
    Returns dict with:
    - search_urls: list of LinkedIn search URLs to try
    - networking_tips: list of suggested actions
    - estimated_bonus: networking score (0-15)
    """
    company_clean = company.strip()
    company_encoded = company_clean.replace(" ", "%20")
    base = "https://www.linkedin.com/search/results/people/"
    
    searches = []
    tips = []
    bonus = 0
    
    # Search 1: PKU alumni at this company
    searches.append({
        "label": f"🎓 北大校友 at {company_clean}",
        "url": f"{base}?keywords=peking%20university&currentCompany=%5B%22{company_encoded}%22%5D",
        "why": "PKU alumni are most likely to respond to your outreach"
    })
    
    # Search 2: NYIT alumni at this company
    searches.append({
        "label": f"🎓 NYIT alumni at {company_clean}",
        "url": f"{base}?keywords=NYIT&currentCompany=%5B%22{company_encoded}%22%5D",
        "why": "NYIT alumni can speak to shared educational background"
    })
    
    # Search 3: Chinese professionals in data/ML roles at this company
    searches.append({
        "label": f"🇨🇳 Chinese DS/ML professionals at {company_clean}",
        "url": f"{base}?keywords=data%20scientist%20machine%20learning&currentCompany=%5B%22{company_encoded}%22%5D&geoUrn=%5B%22103366113%22%5D",
        "why": "Chinese-origin professionals may understand your background and be willing to refer"
    })
    
    # Search 4: Former Uber employees at this company
    searches.append({
        "label": f"🚗 Ex-Uber at {company_clean}",
        "url": f"{base}?keywords=uber&currentCompany=%5B%22{company_encoded}%22%5D",
        "why": "Former Uber colleagues understand the pace and data culture you come from"
    })
    
    # Search 5: Former PwC employees at this company
    searches.append({
        "label": f"🏢 Ex-PwC at {company_clean}",
        "url": f"{base}?keywords=pwc&currentCompany=%5B%22{company_encoded}%22%5D",
        "why": "Former PwC consultants value the analytical rigor you bring"
    })
    
    # Search 6: Data science team at this company in Vancouver
    searches.append({
        "label": f"📊 DS/ML team at {company_clean} Vancouver",
        "url": f"{base}?keywords=data%20scientist&currentCompany=%5B%22{company_encoded}%22%5D&geoUrn=%5B%22103366113%22%5D",
        "why": "Find potential hiring managers or team members to connect with"
    })
    
    # Networking tips
    tips.append(f"1. Search for PKU/NYIT alumni at {company_clean} — they're most likely to accept your connection request")
    tips.append(f"2. Look for Chinese-origin data scientists at {company_clean} — they understand the challenge of breaking into the Canadian market")
    tips.append(f"3. Check if anyone in the DS team at {company_clean} previously worked at Uber or PwC — shared experience is a strong networking hook")
    tips.append(f"4. When connecting, mention specific things: your PKU math background, Uber growth analytics experience, or PwC cross-border M&A work")
    
    # Companies with known Chinese/international employee presence get bonus
    HIGH_CHINESE_PRESENCE = [
        "amazon", "microsoft", "google", "meta", "apple", "shopify",
        "huawei", "tencent", "alibaba", "bytedance",
        "rbc", "td", "bmo", "deloitte", "pwc", "ey", "kpmg",
        "sap", "visier", "d-wave", "hootsuite",
    ]
    company_lower = company_clean.lower()
    if any(c in company_lower for c in HIGH_CHINESE_PRESENCE):
        bonus = 10
    elif any(c in company_lower for c in ["telus", "fortinet", "absolute", "bench", "clio"]):
        bonus = 5
    else:
        bonus = 2  # Small bonus for any networking effort
    
    return {
        "search_urls": searches,
        "networking_tips": tips,
        "networking_score": bonus
    }


# Connection request templates
TEMPLATES = {
    "pku_alumni": """Hi {name}, I noticed you're a PKU alumnus working at {company} — 小校友在温哥华！I'm a PKU Math graduate (2011) with 10+ years in data science and ML (ex-Uber, ex-PwC), recently relocated to Vancouver and pursuing my M.S. in CS at NYIT. I'd love to connect and hear about your experience at {company}. Would you be open to a brief chat? Thanks!""",
    
    "nyit_alumni": """Hi {name}, I see you're an NYIT alumnus at {company} — great to find a fellow NYIT connection! I'm currently in the M.S. Computer Science program at NYIT Vancouver, with 10+ years of data science experience. I'd love to connect and learn about the data team at {company}. Thanks!""",
    
    "ex_uber": """Hi {name}, I noticed you previously worked at Uber — I was a City Lead / South China Lead at Uber from 2015-2016, working on growth analytics and marketplace optimization. Small world! I'm now in Vancouver looking for DS opportunities. Would love to connect!""",
    
    "ex_pwc": """Hi {name}, I see you have PwC in your background — I was a Senior Consultant at PwC Management Consulting (2011-2015), specializing in M&A and growth strategy. I'm now in Vancouver transitioning into data science. Would love to connect with a fellow PwC alum!""",
    
    "chinese_professional": """Hi {name}, I'm a data scientist based in Vancouver with 10+ years of experience in ML/AI (ex-Uber, ex-PwC, Peking University). I'm exploring opportunities in {company}'s data team and would love to connect and learn about your experience there. Thanks!""",
    
    "hiring_manager": """Hi {name}, I saw the {job_title} opening at {company} and was very excited about it. I have 10+ years of ML/AI experience including scaling Uber China's analytics (5%→30% market share) and deploying GNN-based systems at a Sequoia-backed startup. I've applied through the portal and would welcome the chance to briefly discuss how my background aligns. Would you be open to a quick chat?""",
}
```

### Display in Job Pool (Job Detail Panel)

When user expands a job in Job Pool, add a "🤝 Networking" section below the score breakdown:

```
🤝 Networking Intelligence
Networking Score: +10 (company known to have international talent)

🔗 Find Connections:
  🎓 北大校友 at Lululemon       [Open LinkedIn Search →]
  🎓 NYIT alumni at Lululemon    [Open LinkedIn Search →]
  🇨🇳 Chinese DS/ML at Lululemon  [Open LinkedIn Search →]
  🚗 Ex-Uber at Lululemon        [Open LinkedIn Search →]
  🏢 Ex-PwC at Lululemon         [Open LinkedIn Search →]
  📊 DS team at Lululemon Van.   [Open LinkedIn Search →]

💡 Tips:
  1. Search for PKU alumni first — highest response rate
  2. Mention your Uber growth analytics experience as a hook
  3. After connecting, wait 2-3 days before asking about referrals
```

Each "Open LinkedIn Search →" is a clickable link (`st.link_button`) that opens the pre-built LinkedIn search URL.

### Add networking score to total score

In `core/ranker.py`, integrate the networking bonus into the success score:

```python
# In calculate_success_score or in the main ranking function:
networking_intel = generate_networking_intel(job["company"])
networking_bonus = networking_intel["networking_score"]
# Add to success score (capped at contributing max 15 points)
success_score += min(15, networking_bonus)
```

---

## Change 4: Resume Tone Adjustment for Tier C (Quick Win) Jobs

### Concept

For junior/mid roles (Tier C), the user needs to appear LESS overqualified. The AI resume generator should have a mode for this.

### Implementation

In `core/resume_generator.py`, when generating for a Tier C job, add these instructions to the Claude API prompt:

```
RESUME TONE: ACCESSIBLE (for Tier C / entry-mid level roles)

Since this is a junior or mid-level role, adjust the resume to:
1. Use title "Data Scientist" or "Data Analyst" — not "Head of" or "COO" or "General Manager"
2. For past roles with senior titles (Head of Quantitative Analysis, COO, General Manager):
   - Keep the real title but EMPHASIZE the hands-on technical work, not the leadership
   - Lead with technical bullets (built models, wrote code, analyzed data)
   - De-emphasize management/strategy bullets
3. Focus on DOING rather than LEADING:
   - "Built ML pipeline using LightGBM" ✅ 
   - "Led the development of ML infrastructure" ❌ (sounds too senior)
   - "Analyzed marketplace metrics using SQL and Python" ✅
   - "Formulated data-driven growth strategies" ❌ (sounds too strategic)
4. Keep the resume to 1 page if possible (de-emphasize older/less relevant experience)
5. Put Technical Skills section BEFORE Professional Experience
6. The goal is to appear as a strong individual contributor, not a manager
```

Add a "Resume Tone" option in the Apply page:
```python
tone = st.radio("Resume Tone", 
    ["Standard", "Accessible (for junior/mid roles)"],
    help="Use 'Accessible' for Tier C jobs to avoid appearing overqualified"
)
```

---

## Change 5: Update Job Pool KPI Bar

Add tier distribution to the KPI bar:

```
🎯 Tier A: 5 | ✅ Tier B: 10 | 🟢 Tier C: 5 | BC PNP: 16 | Avg Score: 84
```

---

## Summary of ALL Changes

| Change | Files Modified | Purpose |
|--------|---------------|---------|
| 1. Tiered strategy | `core/ranker.py`, `core/db.py`, `pages/1_*.py` | Categorize jobs into A/B/C tiers |
| 2. Realistic success | `core/ranker.py` | Account for Canadian experience barrier, company openness, competition |
| 3. Networking intel | NEW `core/networking.py`, `pages/1_*.py` | LinkedIn search URLs + connection templates |
| 4. Resume tone | `core/resume_generator.py`, `pages/2_*.py` | Accessible mode for junior roles |
| 5. Updated KPIs | `pages/1_*.py` | Show tier distribution |

## Testing

After implementing all changes:
1. Reload sample data — verify jobs are distributed across tiers A/B/C (not all in one tier)
2. Check Lululemon Senior DS → should be Tier A (stretch)
3. Check a junior analyst role → should be Tier C (quick win) 
4. Expand a job → verify networking links open correct LinkedIn search URLs
5. Generate resume in "Accessible" mode → verify it de-emphasizes leadership language
6. Verify success scores are now LOWER and more realistic (average should be 30-50, not 80+)
