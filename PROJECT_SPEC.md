# JobPilot — AI-Powered Job Search Dashboard
## Project Specification for Claude Code

> **How to use this document**: Give this file to Claude Code along with the `reference/` folder.
> Run: `claude` in the project root, then paste: "Read PROJECT_SPEC.md and start building."

---

## 1. PROJECT OVERVIEW

### What is this?
A Streamlit-based job search dashboard for a data scientist based in Vancouver, BC who is targeting Canadian PR through the BC PNP Tech pathway. The system automates the entire job search workflow: discovering jobs → ranking them → generating AI-powered customized resumes and cover letters → ATS scoring → tracking application progress → identifying skill gaps.

### Why does this exist?
The user has 10+ years of experience (Uber, PwC, AI startups, quantitative finance) but is getting zero callbacks in the Canadian job market due to:
1. Generic resumes that don't pass ATS keyword filters
2. No Canadian work experience
3. Manual, time-consuming application process
4. No way to track which jobs are worth applying to

### Who is the user?
- **Primary user**: Xiaoxiao Wu, the job seeker (profile in `reference/master_profile.json`)
- **Secondary users**: Friends in similar situations — immigrants targeting Canadian tech jobs via PNP
- The system should eventually be configurable for any user by swapping out the profile JSON

### Target roles (in priority order):
1. Data Scientist (NOC 21211 — BC PNP Tech priority)
2. AI/RAG Consultant (NOC 21221)
3. Product Analyst (NOC 21221)
4. Data Analyst (NOC 21223)
5. Cybersecurity Data Analyst (NOC 21220 — BC PNP Tech priority)

---

## 2. SYSTEM ARCHITECTURE

```
jobpilot/
├── app.py                          # Streamlit entry point — multi-page app
├── pages/
│   ├── 1_🔍_Job_Pool.py           # Job discovery + ranking dashboard
│   ├── 2_📝_Apply.py              # Resume + cover letter generator
│   ├── 3_📊_Tracker.py            # Application progress tracking
│   ├── 4_🎯_Skills_Gap.py         # Skills gap analysis
│   └── 5_🍁_Immigration.py        # BC PNP eligibility tracker
├── core/
│   ├── scraper.py                  # Job scraping (python-jobspy)
│   ├── ranker.py                   # 5-dimension job scoring
│   ├── ats_scorer.py               # ATS keyword extraction + scoring
│   ├── resume_generator.py         # AI-powered resume generation (Claude API)
│   ├── cover_letter_generator.py   # AI-powered cover letter generation (Claude API)
│   ├── docx_builder.py             # .docx file creation (python-docx)
│   ├── skills_analyzer.py          # Aggregate skill gap analysis
│   └── immigration.py              # BC PNP eligibility logic
├── data/
│   ├── master_profile.json         # User's background (THE source of truth)
│   ├── jobs.db                     # SQLite database for all job + application data
│   ├── scraper_config.json         # Search parameters
│   └── skill_taxonomy.json         # Categorized skill keywords
├── reference/                      # Files from prior work (READ THESE FIRST)
│   ├── master_profile.json         # ← Copy to data/ on first run
│   ├── linkedin_guide.md           # LinkedIn optimization copy
│   ├── github_portfolio_guide.md   # GitHub project plans
│   ├── module_e_execution_plan.md  # 10-week action plan
│   ├── scraper_config.json         # Search config
│   ├── ats_scorer.py               # Reference ATS scoring logic
│   ├── job_ranker.py               # Reference ranking logic
│   ├── job_scraper.py              # Reference scraping logic
│   └── sample_jobs_ranked.csv      # 20 sample jobs for testing
├── requirements.txt
├── .env.example                    # ANTHROPIC_API_KEY placeholder
├── README.md
├── Dockerfile
└── .gitignore
```

---

## 3. DATABASE SCHEMA (SQLite)

Use SQLite via `sqlite3` (no ORM needed). Single file: `data/jobs.db`.

```sql
-- All discovered jobs
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT,           -- Full JD text (critical for ATS scoring)
    job_url TEXT UNIQUE,        -- Dedup key
    source TEXT,                -- linkedin, indeed, glassdoor, zip_recruiter, manual
    salary_min REAL,
    salary_max REAL,
    salary_interval TEXT,       -- yearly, hourly, monthly
    job_type TEXT,              -- fulltime, parttime, contract
    date_posted TEXT,
    date_scraped TEXT DEFAULT (date('now')),
    search_query TEXT,          -- Which search term found this
    -- Computed scores (filled by ranker)
    score_skills REAL,
    score_immigration REAL,
    score_salary REAL,
    score_company REAL,
    score_success REAL,
    score_total REAL,
    priority TEXT,              -- HIGH, MEDIUM, LOW
    -- Immigration metadata
    noc_code TEXT,
    noc_description TEXT,
    bcpnp_eligible INTEGER DEFAULT 0,  -- 1=Yes, 0=Unknown
    -- Application tracking
    status TEXT DEFAULT 'new',  -- new, saved, applied, interviewing, rejected, offer, withdrawn
    date_applied TEXT,
    date_response TEXT,
    resume_version TEXT,        -- Filename of resume used
    cover_letter_version TEXT,  -- Filename of CL used
    ats_score REAL,             -- ATS score at time of application
    notes TEXT,
    is_archived INTEGER DEFAULT 0
);

-- Skill gap tracking (aggregated from all JDs)
CREATE TABLE skill_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill TEXT NOT NULL,
    category TEXT,              -- hard_skill, soft_skill, tool, certification
    job_id INTEGER,
    user_has INTEGER DEFAULT 0, -- 1=user has this skill, 0=gap
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Application activity log
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT DEFAULT (date('now')),
    action TEXT,                -- scraped, applied, interview_scheduled, rejected, etc.
    job_id INTEGER,
    details TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Weekly targets tracking
CREATE TABLE weekly_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT,            -- Monday date
    jobs_reviewed INTEGER DEFAULT 0,
    applications_sent INTEGER DEFAULT 0,
    interviews INTEGER DEFAULT 0,
    networking_actions INTEGER DEFAULT 0,
    github_commits INTEGER DEFAULT 0,
    linkedin_posts INTEGER DEFAULT 0,
    notes TEXT
);
```

---

## 4. PAGE SPECIFICATIONS

### Page 1: 🔍 Job Pool

**Purpose**: Discover, score, and browse job opportunities.

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  🔍 Job Pool                            [🔄 Refresh]  │
├────────────────────────────────────────────────────────┤
│  KPI Bar:                                              │
│  [Total Jobs: 156] [New Today: 12] [HIGH: 34]          │
│  [BC PNP Eligible: 89] [Avg Score: 67]                 │
├────────────────────────────────────────────────────────┤
│  Filters (sidebar):                                    │
│  - Priority: [HIGH] [MEDIUM] [LOW]                     │
│  - Status: [new] [saved] [applied] ...                 │
│  - Min Score: [slider 0-100]                           │
│  - BC PNP Only: [checkbox]                             │
│  - Company: [multiselect]                              │
│  - Search query: [text input]                          │
├────────────────────────────────────────────────────────┤
│  Job Table (sortable, clickable):                      │
│  Score | Priority | Title | Company | Skills | Immig.  │
│  95    | 🔴 HIGH  | Sr DS | Lulu    | 96     | 100    │
│  93    | 🔴 HIGH  | DS    | TELUS   | 98     | 100    │
│  ...                                                   │
├────────────────────────────────────────────────────────┤
│  Job Detail Panel (expands on click):                  │
│  Full description, all scores breakdown, action buttons│
│  [💾 Save] [📝 Generate Resume] [🗑️ Archive]          │
└────────────────────────────────────────────────────────┘
```

**Functionality**:
- "Refresh" button triggers `core/scraper.py` → scrape → rank → save to DB
- Table uses `st.dataframe` with column sorting
- Clicking a row expands job details below the table
- "Generate Resume" button navigates to Page 2 with JD pre-filled
- "Save" marks job as `status='saved'`
- Sidebar filters update table in real-time

**Backend**:
- `core/scraper.py`: Uses `python-jobspy` library (`from jobspy import scrape_jobs`)
- Search parameters from `data/scraper_config.json`
- After scraping, immediately run `core/ranker.py` on new jobs
- Dedup by `job_url` before inserting into DB

### Page 2: 📝 Apply (Resume & Cover Letter Generator)

**Purpose**: Generate ATS-optimized, AI-customized resume and cover letter for a specific job.

**THIS IS THE MOST IMPORTANT PAGE.** The quality of generated documents directly determines whether the user gets interviews.

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  📝 Application Generator                              │
├─────────────────────┬──────────────────────────────────┤
│  LEFT PANEL (input) │  RIGHT PANEL (output)            │
│                     │                                  │
│  Job Description:   │  ┌──────────────────────┐        │
│  [large text area]  │  │ ATS Score: 78% ✅    │        │
│                     │  │ ██████████░░ 78/100  │        │
│  Company: [input]   │  │                      │        │
│  Title: [input]     │  │ Skills: 85%          │        │
│  Role type:         │  │ Immigration: 100%    │        │
│  [dropdown]         │  │ Keywords matched: 24 │        │
│                     │  │ Keywords missing: 6  │        │
│  OR: Select from    │  └──────────────────────┘        │
│  saved jobs:        │                                  │
│  [dropdown]         │  Resume Preview:                 │
│                     │  [rendered preview of resume]    │
│  [⚡ Generate]      │                                  │
│                     │  Cover Letter Preview:           │
│  Advanced Options:  │  [rendered preview of CL]        │
│  ☐ Custom summary   │                                  │
│  ☐ Extra skills     │  [📥 Download Resume .docx]      │
│  ☐ Hiring manager   │  [📥 Download Cover Letter .docx]│
│    name             │  [📥 Download ATS Report .txt]   │
│                     │                                  │
│  Missing Skills:    │  Missing Keywords Alert:         │
│  [list of gaps      │  These JD keywords are not in    │
│   with suggestions] │  your resume. Consider adding:   │
│                     │  - Tableau ⚠️                    │
│                     │  - AWS ⚠️                        │
│                     │  - Snowflake ⚠️                  │
└─────────────────────┴──────────────────────────────────┘
```

**Functionality — AI-Powered Resume Generation**:

This is the critical differentiator. Use the **Anthropic Claude API** to generate customized resume content.

```python
# Pseudocode for resume generation flow:

def generate_resume(jd_text, company, title, role_type, profile):
    """
    Step 1: ATS Analysis
    - Extract keywords from JD (use ats_scorer.py logic)
    - Compare against user's skill inventory
    - Calculate ATS match score
    
    Step 2: AI Content Generation (Claude API)
    - Send prompt to Claude with: user profile + JD + instructions
    - Claude generates:
      a) Customized professional summary (2-3 sentences)
      b) Rewritten bullet points optimized for THIS JD
      c) Skills section ordered by JD relevance
    - Use structured output (JSON) for reliable parsing
    
    Step 3: Build .docx
    - Use python-docx to create formatted resume
    - Professional layout: name, contact, summary, skills, experience, education
    - Return both the .docx file and a text preview
    """
```

**Claude API Prompt Template for Resume Generation**:
```
You are an expert resume writer specializing in Canadian tech job applications.

Given the candidate's full background profile and a target job description, 
generate a tailored resume that maximizes ATS keyword match while remaining 
truthful to the candidate's actual experience.

## Candidate Profile:
{master_profile_json}

## Target Job Description:
{jd_text}

## Target Role Type: {role_type}
## Company: {company}
## Job Title: {title}

## Instructions:
1. Write a professional summary (2-3 sentences) that directly addresses 
   what this JD is looking for, using keywords from the JD naturally.

2. Select the 4-5 most relevant experiences from the profile. For each, 
   rewrite 3-5 bullet points that:
   - Start with strong action verbs
   - Include quantified results where available
   - Naturally incorporate JD keywords (don't keyword-stuff)
   - Emphasize transferable skills relevant to this specific role

3. Emphasize the candidate's INTERNATIONAL experience as a strength:
   - Cross-border M&A (Japan, SE Asia, Australia/NZ)
   - Global system implementations (18 countries)
   - Collaboration with US HQ teams
   Do NOT fabricate Canadian experience.

4. Order the technical skills section by relevance to this JD.

5. Do NOT include the OHSU experience.

## Output Format (JSON):
{
  "summary": "...",
  "experiences": [
    {
      "id": "uber",
      "title": "...",
      "company": "...",
      "dates": "...",
      "bullets": ["...", "...", "..."]
    }
  ],
  "skills": {
    "programming": ["..."],
    "ml_frameworks": ["..."],
    "data_tools": ["..."],
    "methods": ["..."]
  },
  "cover_letter": {
    "opening": "...",
    "body_paragraph_1": "...",
    "body_paragraph_2": "...",
    "body_paragraph_3": "...",
    "closing": "..."
  }
}
```

**Claude API Integration**:
```python
import anthropic

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

**IMPORTANT**: Use `claude-sonnet-4-20250514` for generation (fast + good quality). The API key should be loaded from `.env` file via `python-dotenv`.

**Docx Generation** (python-docx):
- US Letter size, 0.5" margins
- Font: Calibri 10pt for body, 14pt bold for name
- Sections: Contact → Summary → Technical Skills → Experience → Education
- Each experience: Title + Company on one line, dates right-aligned
- Bullets as actual bullet points
- No tables, no images, no fancy formatting (ATS can't parse them)

### Page 3: 📊 Tracker

**Purpose**: Track application status and weekly activity.

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  📊 Application Tracker                                │
├────────────────────────────────────────────────────────┤
│  Pipeline Summary:                                     │
│  [Saved:12] → [Applied:8] → [Interview:2] → [Offer:0] │
│  Response Rate: 25% | Avg Days to Response: 8          │
├────────────────────────────────────────────────────────┤
│  This Week's Activity:                                 │
│  Applications: 6/10 target ████████░░                  │
│  Interviews:   1/3 target  ████░░░░░░                  │
│  Networking:   3/5 target  ██████░░░░                  │
├────────────────────────────────────────────────────────┤
│  Application Table (editable status):                  │
│  Date | Company | Title | Status [dropdown] | ATS | Notes│
│  2/13 | Lulu    | Sr DS | Applied ▼         | 78% | ... │
│  2/12 | TELUS   | DS    | Interview ▼       | 82% | ... │
├────────────────────────────────────────────────────────┤
│  Weekly Trend Chart:                                   │
│  [Bar chart: applications per week over time]          │
└────────────────────────────────────────────────────────┘
```

**Functionality**:
- Status dropdown updates DB directly (`st.selectbox` per row)
- Weekly targets are configurable
- Charts use `st.bar_chart` or `plotly`
- "Add Manual Job" button for jobs found outside the scraper

### Page 4: 🎯 Skills Gap

**Purpose**: Aggregate all JD keywords across saved/applied jobs to show the user what skills they're missing most frequently.

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  🎯 Skills Gap Analysis                                │
├────────────────────────────────────────────────────────┤
│  Based on 45 job descriptions analyzed:                │
│                                                        │
│  Most Frequently Missing Skills:                       │
│  1. AWS/GCP (mentioned in 38/45 JDs, you: ❌)          │
│  2. Tableau (mentioned in 34/45 JDs, you: ❌)           │
│  3. Snowflake (mentioned in 28/45 JDs, you: ❌)        │
│  4. Docker (mentioned in 25/45 JDs, you: ❌)            │
│  5. dbt (mentioned in 18/45 JDs, you: ❌)              │
│  6. Airflow (mentioned in 15/45 JDs, you: ❌)          │
│                                                        │
│  Your Strongest Matches:                               │
│  1. Python (45/45 JDs, you: ✅)                        │
│  2. SQL (44/45 JDs, you: ✅)                           │
│  3. Machine Learning (42/45 JDs, you: ✅)              │
│  4. A/B Testing (30/45 JDs, you: ✅)                   │
│  ...                                                   │
│                                                        │
│  Recommended Learning Priority:                        │
│  [Visual chart: skill frequency × your gap = priority] │
│                                                        │
│  Skill Category Breakdown:                             │
│  [Radar chart: ML, Cloud, BI, DataEng, Stats, etc.]   │
└────────────────────────────────────────────────────────┘
```

**Backend**:
- Every time a JD is analyzed (Page 2), extract all skill keywords and save to `skill_mentions` table
- Aggregate across all analyzed JDs
- Compare against user's skills from `master_profile.json`
- Skills the user has: defined in profile's skills section + experience keywords
- Skills the user doesn't have: everything else that appears in JDs

### Page 5: 🍁 Immigration

**Purpose**: Track BC PNP Tech pathway eligibility across all jobs.

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  🍁 Immigration Pathway Tracker                        │
├────────────────────────────────────────────────────────┤
│  Your Target: BC PNP Tech → Express Entry (EEBC)       │
│                                                        │
│  NOC Distribution of Saved Jobs:                       │
│  [Pie chart: 21211 Data Scientists: 60%,               │
│   21220 Cybersecurity: 15%, 21221 Business: 12%, ...]  │
│                                                        │
│  BC PNP Tech Eligible Jobs: 89/156 (57%)               │
│                                                        │
│  Salary vs PNP Threshold:                              │
│  [Chart: job salaries vs $38.46/hr BC median wage]     │
│  Jobs above median wage: 67 (better PNP SIRS score)    │
│                                                        │
│  Key Requirements Checklist:                           │
│  ✅ Job in BC PNP Tech priority occupation             │
│  ⬜ Full-time, indeterminate job offer                 │
│  ⬜ Employer registered with BC PNP                    │
│  ✅ Meet education requirements (M.S. + B.S.)          │
│  ✅ Meet language requirements (CLB 7+)                │
│  ⬜ 2+ years relevant experience (✅ you have 10+)     │
└────────────────────────────────────────────────────────┘
```

---

## 5. CORE MODULE SPECIFICATIONS

### 5.1 core/scraper.py

Wraps `python-jobspy` library. Reference implementation: `reference/job_scraper.py`.

```python
from jobspy import scrape_jobs

def scrape_all_jobs(config: dict) -> list[dict]:
    """
    Scrape jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter.
    
    Args:
        config: From data/scraper_config.json
        
    Returns:
        List of job dicts with keys: title, company, location, 
        description, job_url, salary_min, salary_max, etc.
    """
```

Key behaviors:
- Run all search queries from config
- Dedup by job_url
- Filter out excluded keywords (intern, director, VP)
- Return raw results (ranking happens separately)

### 5.2 core/ranker.py

5-dimension scoring system. Reference: `reference/job_ranker.py`.

**Scoring dimensions and weights**:
| Dimension | Weight | Logic |
|-----------|--------|-------|
| Skills Match | 40% | Compare JD keywords against user's skills. User skills are categorized as STRONG (1.0x), MODERATE (0.7x), EMERGING (0.4x), WEAK (0.1x) |
| Immigration Fit | 25% | NOC code in BC PNP Tech list? Location in BC? Full-time? No "Canadian experience required"? |
| Salary | 15% | Higher salary = higher BC PNP SIRS score. $145K+ = 100, $120K+ = 90, etc. |
| Company | 10% | Known tier-1/tier-2 companies score higher. Startups < Series B score lower (immigration risk) |
| Success Probability | 10% | Experience level match, no citizenship requirement, no "no sponsorship" flag |

**Output**: score_total (0-100), priority label (HIGH/MEDIUM/LOW), individual dimension scores.

### 5.3 core/ats_scorer.py

ATS keyword analysis. Reference: `reference/ats_scorer.py`.

**Input**: JD text + user profile
**Output**: 
- Overall ATS score (0-100%)
- Matched keywords (with categories)
- Missing keywords (with suggestions for where to add them)
- Category breakdown (hard skills, tools, methods, soft skills)

**Keyword extraction approach**:
- Maintain a taxonomy of 200+ skill keywords in `data/skill_taxonomy.json`
- Extract multi-word phrases first (e.g., "machine learning" before "machine")
- Categorize each keyword: hard_skill, tool, method, soft_skill, certification
- Weight categories differently: hard_skills (3.0x), tools (2.5x), methods (2.0x), soft_skills (1.0x)

### 5.4 core/resume_generator.py

**THIS IS THE KEY MODULE. Use Claude API, not template filling.**

```python
def generate_application(
    jd_text: str,
    company: str,
    title: str,
    role_type: str,  # data_scientist, ai_consultant, product_analyst, data_analyst
    profile: dict,   # From master_profile.json
    extra_instructions: str = ""
) -> dict:
    """
    Uses Claude API to generate customized resume + cover letter content.
    
    Returns:
        {
            "summary": str,
            "experiences": [{"id", "title", "company", "dates", "bullets": []}],
            "skills": {"programming": [], "ml_frameworks": [], ...},
            "cover_letter": {"opening", "body_1", "body_2", "body_3", "closing"},
            "ats_score": float,
            "matched_keywords": [],
            "missing_keywords": []
        }
    """
```

**Important rules for resume generation**:
1. NEVER fabricate experience. All content must be based on `master_profile.json`
2. DO NOT include the OHSU experience (id: "ohsu")
3. DO emphasize international experience (cross-border M&A, global implementations, US HQ collaboration)
4. Target resume length: 2 pages max (US Letter)
5. Each experience: 3-5 bullets, starting with action verbs
6. Include quantified results wherever available in the profile
7. Skills section ordered by JD relevance, not alphabetically

### 5.5 core/docx_builder.py

Creates .docx files from structured content using `python-docx`.

**Resume format**:
- Page size: US Letter (8.5" × 11")
- Margins: 0.5" all sides
- Font: Calibri (body 10pt, name 14pt bold, section headers 11pt bold)
- No tables, no images, no columns (ATS compatibility)
- Sections separated by thin horizontal rule
- Bullet points: standard bullet character, hanging indent

**Cover letter format**:
- Same page setup as resume
- Date + recipient info at top
- 4-5 paragraphs
- Sign-off with name and contact

### 5.6 core/skills_analyzer.py

Aggregates skill mentions across all analyzed JDs.

```python
def analyze_gaps(db_path: str, user_skills: set) -> dict:
    """
    Query skill_mentions table, compare against user_skills.
    
    Returns:
        {
            "missing_skills": [{"skill": "AWS", "frequency": 38, "category": "cloud"}],
            "strong_skills": [{"skill": "Python", "frequency": 45, "category": "programming"}],
            "recommendations": ["Learn AWS SageMaker — appears in 84% of target JDs"]
        }
    """
```

### 5.7 core/immigration.py

BC PNP Tech pathway logic.

**BC PNP Tech Priority Occupations (2025-2026)**:
```python
BCPNP_TECH_NOCS = {
    "21211", "21220", "21221", "21222", "21223",
    "21230", "21231", "21232", "21233", "21234",
    "21311", "20012", "22220", "22222"
}
```

**NOC mapping from job titles**:
```python
TITLE_TO_NOC = {
    "data scientist": "21211",
    "machine learning": "21211",
    "ml engineer": "21211",
    "applied scientist": "21211",
    "research scientist": "21211",
    "cybersecurity": "21220",
    "security analyst": "21220",
    "business analyst": "21221",
    "product analyst": "21221",
    "data analyst": "21223",
    "software engineer": "21231",
    "data engineer": "21231",
}
```

---

## 6. KEY USER PROFILE DECISIONS

Based on our prior discussion, these decisions have been made:

### Include in resume:
- ✅ Gaff Sail PE — Head of Quantitative Analysis (10/2020 - 08/2024)
- ✅ Shiyibei — COO (09/2016 - 07/2017) — emphasize AI/ML aspects
- ✅ Uber — Senior Dops / City Lead (07/2015 - 09/2016) — highlight analytics and experimentation
- ✅ PwC — Senior Consultant (07/2011 - 06/2015) — emphasize cross-border M&A, global projects
- ✅ Peking University — B.S. Mathematics + B.A. Economics
- ✅ NYIT Vancouver — M.S. Computer Science (in progress)

### Exclude from resume:
- ❌ OHSU — Do not include (not a real position)
- ❌ Gaff Information Technology (GM role) — Include only if space allows and relevant

### Emphasize:
- International experience: Haier-Sanyo acquisition (Japan, SE Asia, AU/NZ), Workday global rollout (18 countries), Uber cross-HQ collaboration with San Francisco
- Quantified results: "5% → 30% market share", "0.2% → 0.5% conversion", "$31M pension impact", "2012 China M&A Service Award"
- Technical depth: GNN, RL, NLP chatbots, time series, A/B testing
- Business acumen: PwC consulting background, ability to communicate with stakeholders

### Location on resume:
- Do NOT write dual locations (e.g., "Shenzhen/San Francisco")
- Write actual location, describe cross-border collaboration in bullet points

---

## 7. CONFIGURATION FILES

### data/scraper_config.json
See `reference/scraper_config.json`. Key fields:
- `search_queries`: List of search terms
- `location`: "Vancouver, BC, Canada"
- `sites`: ["linkedin", "indeed", "glassdoor", "zip_recruiter"]
- `hours_old`: 72 (only recent postings)
- `exclude_keywords`: ["intern", "director", "vp", ...]

### data/skill_taxonomy.json
Categorized skill keywords used by ATS scorer and skills analyzer:
```json
{
  "user_strong": ["python", "sql", "r", "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "nlp", "gnn", "reinforcement learning", "time series", "a/b testing", "causal inference", "regression", "clustering", "random forest", "lightgbm", "shap", "sentiment analysis", "statistical modeling", "hypothesis testing", "data visualization", "feature engineering"],
  "user_moderate": ["flask", "docker", "git", "linux", "jupyter", "product analytics", "segmentation", "kpi", "etl", "api", "agile", "project management"],
  "user_emerging": ["cybersecurity", "network security", "rag", "langchain", "llm", "generative ai", "prompt engineering", "transformer", "bert"],
  "user_weak": ["aws", "gcp", "azure", "sagemaker", "snowflake", "bigquery", "databricks", "spark", "airflow", "dbt", "tableau", "power bi", "looker", "kubernetes", "terraform", "mlflow"],
  "categories": {
    "programming": ["python", "sql", "r", "java", "scala", "go", "rust", "c++"],
    "ml_frameworks": ["tensorflow", "pytorch", "scikit-learn", "keras", "lightgbm", "xgboost", "hugging face"],
    "cloud": ["aws", "gcp", "azure", "sagemaker", "vertex ai", "databricks"],
    "data_engineering": ["snowflake", "bigquery", "redshift", "spark", "airflow", "dbt", "kafka"],
    "bi_tools": ["tableau", "power bi", "looker", "metabase"],
    "devops": ["docker", "kubernetes", "terraform", "ci/cd", "github actions"],
    "ml_methods": ["nlp", "computer vision", "reinforcement learning", "time series", "recommendation", "anomaly detection", "causal inference", "a/b testing"],
    "soft_skills": ["communication", "stakeholder", "cross-functional", "leadership", "mentoring", "agile", "project management"]
  }
}
```

---

## 8. DEVELOPMENT PRIORITIES

Build in this order:

### Phase 1: Core Backend (Day 1-2)
1. Set up project structure, requirements.txt, SQLite DB
2. `core/ats_scorer.py` — port from reference, add skill_taxonomy.json
3. `core/ranker.py` — port from reference
4. `core/resume_generator.py` — Claude API integration
5. `core/docx_builder.py` — python-docx resume + cover letter builder
6. Test with sample data from `reference/sample_jobs_ranked.csv`

### Phase 2: Streamlit UI (Day 2-4)
1. `app.py` — multi-page setup
2. Page 2 (Apply) first — this is the highest-value page
3. Page 1 (Job Pool) — integrate scraper + ranker
4. Page 3 (Tracker) — CRUD on job status
5. Page 4 (Skills Gap) — aggregation queries
6. Page 5 (Immigration) — PNP eligibility stats

### Phase 3: Polish (Day 4-5)
1. Error handling and edge cases
2. Loading states and progress bars during scraping/generation
3. Caching (`@st.cache_data`) for expensive operations
4. README.md for GitHub
5. Dockerfile for easy deployment
6. `.env.example` with clear setup instructions

---

## 9. REQUIREMENTS

```
# requirements.txt
streamlit>=1.30.0
python-jobspy>=1.1.0
python-docx>=1.1.0
anthropic>=0.40.0
pandas>=2.0.0
plotly>=5.18.0
python-dotenv>=1.0.0
```

**Python version**: 3.10+
**External service**: Anthropic Claude API (key in .env)

---

## 10. README TEMPLATE (for GitHub)

```markdown
# 🧭 JobPilot — AI-Powered Job Search Dashboard

An intelligent job search platform for tech professionals targeting 
Canadian immigration through BC PNP Tech pathway.

## Features
- 🔍 Auto-scrape jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter
- 🏆 5-dimension job ranking (skills, immigration, salary, company, success)
- 📝 AI-powered resume & cover letter generation (Claude API)
- 📊 ATS score simulation and keyword gap analysis
- 🎯 Skills gap analysis across all target JDs
- 🍁 BC PNP Tech eligibility tracking
- 📈 Application progress dashboard

## Quick Start
```bash
git clone https://github.com/YOUR_USERNAME/jobpilot.git
cd jobpilot
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY
cp reference/master_profile.json data/master_profile.json  # Edit with your info
streamlit run app.py
```

## Customize for Your Profile
1. Edit `data/master_profile.json` with your background
2. Edit `data/scraper_config.json` with your target roles and location
3. Edit `data/skill_taxonomy.json` to categorize your skills

## Tech Stack
Python, Streamlit, SQLite, Claude API, python-jobspy, python-docx, plotly

## Author
Built by **Xiaoxiao Wu** as part of a job search automation project.
```

---

## 11. IMPORTANT NOTES FOR CLAUDE CODE

1. **Start by reading ALL files in `reference/`** — they contain working code and tested logic that should be adapted, not rewritten from scratch.

2. **The master_profile.json is the source of truth** for the user's background. All resume generation must be grounded in this file.

3. **Do NOT include OHSU experience** — this has been decided. Filter out any experience with id "ohsu" from master_profile.json.

4. **ATS scoring logic already works well** in `reference/ats_scorer.py` — port it to the new module structure rather than reinventing.

5. **Ranking logic already works** in `reference/job_ranker.py` — the scoring dimensions and weights are tested and validated.

6. **The Claude API call for resume generation is the most critical piece.** Spend extra effort on prompt engineering to get high-quality, JD-specific output. Test with at least 3 different JDs.

7. **python-jobspy can be flaky** — wrap all scraping in try/except, handle empty results gracefully, show clear error messages to user.

8. **Keep the UI simple and functional** — this is a productivity tool, not a design showcase. Use Streamlit's built-in components wherever possible.

9. **All generated .docx files should be ATS-compatible** — no tables, no text boxes, no images, no fancy formatting. Simple, clean, parseable.

10. **This project will be published on GitHub** as a portfolio piece, so write clean code with docstrings and a good README.
