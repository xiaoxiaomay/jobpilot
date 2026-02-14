# 🎯 Job Application Toolkit — Xiaoxiao Wu

## 🚀 Setup (one-time)

```bash
# 1. Install Python dependencies
pip install python-jobspy pandas openpyxl python-docx

# 2. Install Node.js dependency
npm install -g docx

# 3. Edit your profile
# Open master_profile.json and update LinkedIn/GitHub URLs
```

---

## Module A — Daily Job Tracking (自动追踪)

### One-Command Daily Run
```bash
python daily_runner.py
```
This runs the full pipeline: **Scrape → Rank → Excel Tracker**

### Step-by-Step
```bash
# Step 1: Scrape jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter
python job_scraper.py --config scraper_config.json --output data/jobs_raw.csv

# Step 2: Score & rank against your profile
python job_ranker.py --input data/jobs_raw.csv --output data/jobs_ranked.csv

# Step 3: Generate formatted Excel tracker
python excel_tracker.py --input data/jobs_ranked.csv --output output/job_tracker.xlsx
```

### Schedule Daily (auto-run at 8AM)
```bash
python daily_runner.py --setup-cron      # Linux/Mac cron
python daily_runner.py --setup-launchd   # macOS launchd
python daily_runner.py --setup-windows   # Windows Task Scheduler instructions
```

### Ranking Criteria (5 dimensions)
| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Skills Match | 40% | How many JD keywords match your profile |
| Immigration Fit | 25% | BC PNP Tech eligible NOC, location, job type |
| Salary Score | 15% | Higher = better BC PNP SIRS score ($70/hr+ = HIGH) |
| Company Score | 10% | Tier 1/2 companies, reputation, stability |
| Success Probability | 10% | Experience alignment, no "Canadian exp" barrier |

### Customize Search
Edit `scraper_config.json` to change:
- `search_queries` — keywords to search
- `location` / `distance_miles` — geographic filter
- `hours_old` — only get jobs posted in last N hours
- `exclude_keywords` — filter out unwanted levels
- `company_watchlist` — career page URLs to monitor

---

## Module C+D — Resume & Cover Letter Pipeline (简历定制 + ATS评分)

### One-Command Application Pipeline
```bash
# Save a JD to a .txt file, then run:
python pipeline.py --jd path/to/jd.txt \
    --company "Lululemon" \
    --title "Senior Data Scientist" \
    --role data_scientist \
    --output-dir ./output
```

This generates THREE files:
- `ats_report_*.txt` — ATS匹配度评分报告
- `Resume_XiaoxiaoWu_*.docx` — 针对该JD定制的简历
- `CoverLetter_XiaoxiaoWu_*.docx` — 针对该JD定制的求职信

### Role Types (--role)
| Role | Best for |
|------|----------|
| `data_scientist` | Data Scientist, ML Engineer, Applied Scientist |
| `ai_consultant` | AI Consultant, Data Strategy, Enterprise AI |
| `product_analyst` | Product Analyst, Growth Analyst, Business Analyst |
| `data_analyst` | Data Analyst, BI Analyst, Analytics Engineer |

### Standalone ATS Scorer
```bash
python ats_scorer.py --jd path/to/jd.txt --target-role data_scientist
```

### ATS Score Interpretation
| Score | Assessment | Action |
|-------|-----------|--------|
| 80%+ | ✅ Excellent | Submit — high chance of passing ATS |
| 65-79% | 🟡 Good | Review missing skills, add what you can |
| 50-64% | ⚠️ Fair | Significant editing needed |
| <50% | ❌ Low | Consider if this role is a good fit |

---

## 📁 File Structure
```
job-toolkit/
├── daily_runner.py           # ⭐ Daily automation — scrape+rank+track
├── job_scraper.py            # Scrape LinkedIn/Indeed/Glassdoor/ZipRecruiter
├── job_ranker.py             # Score & rank jobs (5 dimensions)
├── excel_tracker.py          # Generate formatted Excel tracker
├── scraper_config.json       # Customize search parameters
│
├── pipeline.py               # ⭐ Per-application pipeline — ATS+resume+CL
├── ats_scorer.py             # ATS keyword extraction & scoring
├── resume_generator.js       # Targeted resume .docx generator
├── cover_letter_generator.js # Cover letter .docx generator
├── master_profile.json       # ⭐ Your background data — EDIT THIS
│
├── data/                     # Raw & ranked job CSVs
├── output/                   # Generated files (tracker, resumes, CLs)
└── sample_jd.txt             # Example JD for testing
```

## Daily Workflow
```
每天早上8点 daily_runner.py 自动运行
  ↓
打开 job_tracker.xlsx → 看 Dashboard → 找到 HIGH priority 的职位
  ↓
对每个要投的职位: 复制JD → 存为.txt → 运行 pipeline.py
  ↓
检查ATS分数 → 微调简历 → 投递
  ↓
在Application Log sheet里记录状态
```

## How to Customize

### 1. Edit master_profile.json
This is the "source of truth" for your resume. Update:
- `personal` — contact info, LinkedIn, GitHub URLs
- `summary_templates` — professional summaries per role type
- `experiences[].bullets` — add/modify bullet points
- `skills` — add new skills you acquire

### 2. Edit scraper_config.json
- `search_queries` — add/remove job titles to search
- `company_watchlist` — add company career page URLs
- `exclude_keywords` — filter unwanted job levels

### 3. Edit Config Files (per application)
After pipeline runs, tweak `_resume_config_*.json` and `_cl_config_*.json`:
- `extra_skills` — add skills from JD you genuinely have
- `summary_override` — custom summary for this application
- `company_specific_closing` — custom closing paragraph
- `hiring_manager` — if you know their name

## Immigration-Relevant NOC Codes
Your target positions map to these BC PNP Tech priority NOC codes:
- **NOC 21211** — Data Scientists ✅ (BC PNP Tech priority)
- **NOC 21220** — Cybersecurity Specialists ✅ (BC PNP Tech priority)
- **NOC 21221** — Business Systems Specialists
- **NOC 21223** — Database Analysts and Data Administrators
- **NOC 20012** — Computer and Information Systems Managers

When applying, make sure job titles align with these NOC descriptions.
