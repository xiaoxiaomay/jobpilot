#!/usr/bin/env python3
"""
Job Application Pipeline
=========================
One-command pipeline: JD in → ATS score + targeted resume + cover letter out.

Usage:
    python pipeline.py --jd jd.txt --company "Acme Corp" --title "Senior Data Scientist" --role data_scientist
    python pipeline.py --jd jd.txt --company "Acme Corp" --title "AI Consultant" --role ai_consultant

Required: --jd (path to JD text file)
Optional: --company, --title, --role, --output-dir
"""

import json
import os
import subprocess
import sys
import argparse
from datetime import datetime
from pathlib import Path

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(TOOLKIT_DIR, "master_profile.json")

# Import ATS scorer
sys.path.insert(0, TOOLKIT_DIR)
from ats_scorer import extract_jd_keywords, build_resume_keyword_set, score_match, generate_gap_report, select_relevant_bullets, load_profile


def slugify(text):
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")[:40]


def run_pipeline(jd_path, company, title, role, output_dir):
    """Run the full pipeline."""
    print("=" * 70)
    print("JOB APPLICATION PIPELINE")
    print(f"Company: {company}")
    print(f"Position: {title}")
    print(f"Target Role Type: {role}")
    print("=" * 70)
    
    # Step 1: Load JD and Profile
    print("\n📄 Step 1: Loading JD and profile...")
    with open(jd_path, "r") as f:
        jd_text = f.read()
    
    profile = load_profile(PROFILE_PATH)
    
    # Step 2: ATS Scoring
    print("\n🔍 Step 2: Running ATS keyword analysis...")
    jd_keywords = extract_jd_keywords(jd_text)
    resume_text = build_resume_keyword_set(profile)
    match_results = score_match(jd_keywords, resume_text)
    
    report = generate_gap_report(jd_keywords, match_results, profile)
    
    # Save ATS report
    company_slug = slugify(company)
    date_str = datetime.now().strftime("%Y%m%d")
    
    os.makedirs(output_dir, exist_ok=True)
    
    report_path = os.path.join(output_dir, f"ats_report_{company_slug}_{date_str}.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"   ✅ ATS Report saved: {report_path}")
    print(f"   📊 Match Score: {match_results['percentage']}%")
    
    # Step 3: Select top bullets
    print("\n📋 Step 3: Selecting optimal resume bullets...")
    top_bullets = select_relevant_bullets(profile, jd_keywords, role)
    
    # Collect all JD keywords for bullet scoring
    all_jd_kws = []
    for cat, kws in jd_keywords.items():
        if isinstance(kws, list):
            all_jd_kws.extend(kws)
    
    # Missing hard skills to add to Skills section
    missing_hard = match_results["missing"].get("hard_skills", [])
    matched_hard = match_results["matched"].get("hard_skills", [])
    
    # Step 4: Generate Resume Config
    print("\n📝 Step 4: Generating targeted resume...")
    resume_config = {
        "target_role": role,
        "company_name": company,
        "job_title": title,
        "selected_keywords": all_jd_kws,
        "extra_skills": [],  # Only add skills you genuinely have
        "summary_override": "",  # Use default template for the role
    }
    
    resume_config_path = os.path.join(output_dir, f"_resume_config_{company_slug}.json")
    with open(resume_config_path, "w") as f:
        json.dump(resume_config, f, indent=2)
    
    resume_path = os.path.join(output_dir, f"Resume_XiaoxiaoWu_{company_slug}_{date_str}.docx")
    
    result = subprocess.run(
        ["node", os.path.join(TOOLKIT_DIR, "resume_generator.js"),
         "--config", resume_config_path,
         "--output", resume_path],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(f"   ✅ Resume saved: {resume_path}")
    else:
        print(f"   ❌ Resume generation failed: {result.stderr}")
    
    # Step 5: Generate Cover Letter Config
    print("\n✉️  Step 5: Generating targeted cover letter...")
    cl_config = {
        "target_role": role,
        "company_name": company,
        "job_title": title,
        "hiring_manager": "Hiring Manager",
        "jd_matched_keywords": matched_hard[:10],
        "company_specific_closing": "",  # Will use default
    }
    
    cl_config_path = os.path.join(output_dir, f"_cl_config_{company_slug}.json")
    with open(cl_config_path, "w") as f:
        json.dump(cl_config, f, indent=2)
    
    cl_path = os.path.join(output_dir, f"CoverLetter_XiaoxiaoWu_{company_slug}_{date_str}.docx")
    
    result = subprocess.run(
        ["node", os.path.join(TOOLKIT_DIR, "cover_letter_generator.js"),
         "--config", cl_config_path,
         "--output", cl_path],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(f"   ✅ Cover letter saved: {cl_path}")
    else:
        print(f"   ❌ Cover letter generation failed: {result.stderr}")
    
    # Step 6: Summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE — SUMMARY")
    print("=" * 70)
    print(f"  ATS Match Score:    {match_results['percentage']}%")
    print(f"  Hard Skills Match:  {match_results['category_scores'].get('hard_skills', {}).get('percentage', 0)}%")
    print(f"  Missing Hard Skills: {len(missing_hard)}")
    print()
    print("  Generated Files:")
    print(f"    📊 {report_path}")
    print(f"    📄 {resume_path}")
    print(f"    ✉️  {cl_path}")
    print()
    
    if match_results['percentage'] < 65:
        print("  ⚠️  WARNING: ATS score below 65%. Review the ATS report for")
        print("     missing keywords and consider editing the resume manually.")
        print("     You can also edit the config JSON and re-run the pipeline.")
    elif match_results['percentage'] < 80:
        print("  🟡 GOOD: Score above 65% but below 80%. Consider manual tweaks")
        print("     to address the top 3-5 missing hard skills.")
    else:
        print("  ✅ EXCELLENT: High match score. Review and submit!")
    
    print()
    print("  NEXT STEPS:")
    print("    1. Review ATS report for missing keywords")
    print("    2. Open resume .docx and refine bullet points")
    print("    3. Customize cover letter closing paragraph for the company")
    print("    4. Re-run ATS scorer on the final version to verify score")
    print()
    
    return {
        "ats_score": match_results['percentage'],
        "files": {
            "report": report_path,
            "resume": resume_path,
            "cover_letter": cl_path,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Job Application Pipeline")
    parser.add_argument("--jd", required=True, help="Path to job description text file")
    parser.add_argument("--company", default="Company", help="Company name")
    parser.add_argument("--title", default="Position", help="Job title")
    parser.add_argument("--role", default="data_scientist",
                        choices=["data_scientist", "ai_consultant", "product_analyst", "data_analyst"],
                        help="Target role type")
    parser.add_argument("--output-dir", default="./output", help="Output directory")
    args = parser.parse_args()
    
    run_pipeline(args.jd, args.company, args.title, args.role, args.output_dir)


if __name__ == "__main__":
    main()
