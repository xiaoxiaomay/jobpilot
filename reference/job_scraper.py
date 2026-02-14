#!/usr/bin/env python3
"""
Job Scraper — Module A
=======================
Scrapes job postings from LinkedIn, Indeed, Glassdoor, ZipRecruiter
using python-jobspy library. Filters, deduplicates, and saves to CSV.

Usage:
    python job_scraper.py [--config scraper_config.json] [--output jobs_raw.csv]

Requirements:
    pip install python-jobspy pandas

Note: For Wellfound/AngelList and company career pages, see company_scraper.py
"""

import json
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

try:
    from jobspy import scrape_jobs
except ImportError:
    print("ERROR: python-jobspy not installed.")
    print("Run: pip install python-jobspy")
    sys.exit(1)

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(TOOLKIT_DIR, "scraper_config.json")

DEFAULT_CONFIG = {
    "search_queries": [
        "data scientist",
        "senior data scientist",
        "machine learning engineer",
        "AI consultant",
        "product analyst",
        "data analyst cybersecurity",
        "data analyst",
        "applied scientist",
        "ML engineer",
        "NLP engineer"
    ],
    "location": "Vancouver, BC, Canada",
    "distance_miles": 30,
    "job_type": "fulltime",
    "results_per_query": 20,
    "sites": ["linkedin", "indeed", "glassdoor", "zip_recruiter"],
    "hours_old": 72,  # Only jobs posted in last 72 hours
    "country": "Canada",
    "exclude_keywords": [
        "intern", "internship", "co-op", "coop",
        "director", "vp", "vice president",
        "staff engineer", "principal"
    ],
    "must_include_keywords": [],  # If set, at least one must appear
    "min_salary": 70000,  # CAD annual
    "target_noc_codes": {
        "21211": "Data Scientists",
        "21220": "Cybersecurity Specialists",
        "21221": "Business Systems Specialists",
        "21223": "Database Analysts and Data Administrators",
        "21231": "Software Engineers and Designers",
        "20012": "Computer and Information Systems Managers"
    }
}


def load_config(config_path=None):
    """Load scraper configuration."""
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            user_config = json.load(f)
        # Merge with defaults
        config = {**DEFAULT_CONFIG, **user_config}
    else:
        config = DEFAULT_CONFIG.copy()
    return config


def scrape_all_jobs(config):
    """Run scraping across all queries and sites."""
    all_jobs = []
    
    for query in config["search_queries"]:
        print(f"  🔍 Searching: '{query}'...")
        try:
            jobs = scrape_jobs(
                site_name=config["sites"],
                search_term=query,
                location=config["location"],
                distance=config["distance_miles"],
                job_type=config["job_type"],
                results_wanted=config["results_per_query"],
                hours_old=config["hours_old"],
                country_indeed=config["country"],
                is_remote=False,  # We want local BC jobs for immigration
            )
            
            if jobs is not None and len(jobs) > 0:
                jobs["search_query"] = query
                all_jobs.append(jobs)
                print(f"    ✅ Found {len(jobs)} jobs")
            else:
                print(f"    ⚠️ No results")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    if not all_jobs:
        print("\n❌ No jobs found across all queries.")
        return pd.DataFrame()
    
    # Combine all results
    df = pd.concat(all_jobs, ignore_index=True)
    print(f"\n📊 Total raw results: {len(df)}")
    
    return df


def filter_jobs(df, config):
    """Apply filters and deduplication."""
    if df.empty:
        return df
    
    original_count = len(df)
    
    # Deduplicate by job URL or title+company combo
    if "job_url" in df.columns:
        df = df.drop_duplicates(subset=["job_url"], keep="first")
    if "title" in df.columns and "company" in df.columns:
        df = df.drop_duplicates(subset=["title", "company"], keep="first")
    print(f"  After dedup: {len(df)} (removed {original_count - len(df)} duplicates)")
    
    # Exclude unwanted job levels
    exclude_kws = [kw.lower() for kw in config.get("exclude_keywords", [])]
    if exclude_kws and "title" in df.columns:
        mask = df["title"].str.lower().apply(
            lambda t: not any(kw in str(t) for kw in exclude_kws)
        )
        removed = len(df) - mask.sum()
        df = df[mask]
        if removed > 0:
            print(f"  Excluded {removed} jobs by title keywords")
    
    # Must include filter (if set)
    must_kws = [kw.lower() for kw in config.get("must_include_keywords", [])]
    if must_kws and "title" in df.columns:
        mask = df["title"].str.lower().apply(
            lambda t: any(kw in str(t) for kw in must_kws)
        )
        if mask.sum() > 0:
            df = df[mask]
    
    # Salary filter (if salary data available)
    if config.get("min_salary") and "min_amount" in df.columns:
        # Only filter rows that have salary data
        has_salary = df["min_amount"].notna()
        above_min = df["min_amount"] >= config["min_salary"]
        df = df[~has_salary | above_min]
    
    print(f"  After all filters: {len(df)} jobs")
    return df.reset_index(drop=True)


def enrich_jobs(df, config):
    """Add computed columns for tracking and ranking."""
    if df.empty:
        return df
    
    # Add metadata columns
    df["scraped_date"] = datetime.now().strftime("%Y-%m-%d")
    df["application_status"] = "New"  # New, Applied, Interview, Rejected, Offer
    df["priority"] = ""  # Will be filled by ranker
    df["notes"] = ""
    df["immigration_fit"] = ""  # Will be filled by ranker
    df["noc_code_guess"] = ""
    
    # Try to guess NOC code from title
    noc_map = config.get("target_noc_codes", {})
    title_to_noc = {
        "data scientist": "21211",
        "machine learning": "21211",
        "ml engineer": "21211",
        "applied scientist": "21211",
        "cybersecurity": "21220",
        "security analyst": "21220",
        "security engineer": "21220",
        "business analyst": "21221",
        "business systems": "21221",
        "data analyst": "21223",
        "database": "21223",
        "analytics engineer": "21223",
        "software engineer": "21231",
        "software developer": "21231",
        "product analyst": "21221",
        "ai consultant": "21211",
        "data engineer": "21231",
    }
    
    if "title" in df.columns:
        for idx, row in df.iterrows():
            title_lower = str(row.get("title", "")).lower()
            for keyword, noc in title_to_noc.items():
                if keyword in title_lower:
                    noc_desc = noc_map.get(noc, "")
                    df.at[idx, "noc_code_guess"] = f"{noc} ({noc_desc})"
                    break
    
    # BC PNP Tech eligibility flag
    bcpnp_tech_nocs = {"21211", "21220", "21221", "21223", "21231", "20012"}
    df["bcpnp_tech_eligible"] = df["noc_code_guess"].apply(
        lambda x: "✅ Yes" if any(noc in str(x) for noc in bcpnp_tech_nocs) else "❓ Check"
    )
    
    return df


def save_results(df, output_path, append=True):
    """Save results, optionally appending to existing tracker."""
    if df.empty:
        print("No jobs to save.")
        return
    
    if append and os.path.exists(output_path):
        # Load existing and append new jobs
        existing = pd.read_csv(output_path)
        
        # Find truly new jobs (not already in tracker)
        if "job_url" in df.columns and "job_url" in existing.columns:
            existing_urls = set(existing["job_url"].dropna().astype(str))
            new_mask = ~df["job_url"].astype(str).isin(existing_urls)
            new_jobs = df[new_mask]
        elif "title" in df.columns and "company" in df.columns:
            existing_keys = set(zip(
                existing.get("title", pd.Series()).fillna(""),
                existing.get("company", pd.Series()).fillna("")
            ))
            new_keys = list(zip(df["title"].fillna(""), df["company"].fillna("")))
            new_mask = pd.Series([k not in existing_keys for k in new_keys])
            new_jobs = df[new_mask]
        else:
            new_jobs = df
        
        if len(new_jobs) > 0:
            combined = pd.concat([existing, new_jobs], ignore_index=True)
            combined.to_csv(output_path, index=False)
            print(f"  📥 Added {len(new_jobs)} NEW jobs (total: {len(combined)})")
        else:
            print(f"  ℹ️ No new jobs found (all {len(df)} already in tracker)")
    else:
        df.to_csv(output_path, index=False)
        print(f"  💾 Saved {len(df)} jobs to {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Job Scraper — Module A")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH,
                        help="Path to scraper config JSON")
    parser.add_argument("--output", type=str, default="jobs_raw.csv",
                        help="Output CSV path")
    parser.add_argument("--no-append", action="store_true",
                        help="Overwrite instead of append to existing file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show config without scraping")
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    print("=" * 60)
    print("JOB SCRAPER — Module A")
    print("=" * 60)
    print(f"  Location:  {config['location']}")
    print(f"  Sites:     {', '.join(config['sites'])}")
    print(f"  Queries:   {len(config['search_queries'])}")
    print(f"  Max age:   {config['hours_old']} hours")
    print(f"  Output:    {args.output}")
    print()
    
    if args.dry_run:
        print("DRY RUN — queries that would be executed:")
        for q in config["search_queries"]:
            print(f"  → {q}")
        return
    
    # Step 1: Scrape
    print("📡 Step 1: Scraping job boards...")
    df = scrape_all_jobs(config)
    
    if df.empty:
        return
    
    # Step 2: Filter
    print("\n🔧 Step 2: Filtering and deduplicating...")
    df = filter_jobs(df, config)
    
    # Step 3: Enrich
    print("\n📋 Step 3: Enriching with metadata...")
    df = enrich_jobs(df, config)
    
    # Step 4: Save
    print("\n💾 Step 4: Saving results...")
    save_results(df, args.output, append=not args.no_append)
    
    print("\n✅ Done! Run job_ranker.py next to score and rank jobs.")


if __name__ == "__main__":
    main()
