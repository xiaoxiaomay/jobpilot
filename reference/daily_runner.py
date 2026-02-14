#!/usr/bin/env python3
"""
Daily Job Search Automation — Module A
========================================
Runs the full pipeline: scrape → rank → generate Excel tracker.
Can be scheduled via cron (Linux/Mac) or Task Scheduler (Windows).

Usage:
    python daily_runner.py                    # Run once now
    python daily_runner.py --setup-cron       # Set up daily cron job (Mac/Linux)
    python daily_runner.py --setup-launchd    # Set up macOS launchd agent
    python daily_runner.py --dry-run          # Show what would run

Schedule: Default runs at 8:00 AM daily.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TOOLKIT_DIR, "data")
OUTPUT_DIR = os.path.join(TOOLKIT_DIR, "output")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_daily():
    """Execute the full daily pipeline."""
    date_str = datetime.now().strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_path = os.path.join(DATA_DIR, "run_log.txt")
    
    print("=" * 60)
    print(f"DAILY JOB SEARCH — {timestamp}")
    print("=" * 60)
    
    # ─── Step 1: Scrape ──────────────────────────────────────────
    print("\n🔍 STEP 1: Scraping job boards...")
    raw_csv = os.path.join(DATA_DIR, "jobs_raw.csv")
    
    result = subprocess.run(
        [sys.executable, os.path.join(TOOLKIT_DIR, "job_scraper.py"),
         "--config", os.path.join(TOOLKIT_DIR, "scraper_config.json"),
         "--output", raw_csv],
        capture_output=True, text=True, cwd=TOOLKIT_DIR
    )
    
    if result.returncode != 0:
        print(f"  ❌ Scraper failed: {result.stderr}")
        log_entry = f"{timestamp} | FAIL | Scraper error: {result.stderr[:200]}\n"
    else:
        print(result.stdout)
        
        # ─── Step 2: Rank ────────────────────────────────────────
        print("\n📊 STEP 2: Ranking jobs...")
        ranked_csv = os.path.join(DATA_DIR, "jobs_ranked.csv")
        
        result2 = subprocess.run(
            [sys.executable, os.path.join(TOOLKIT_DIR, "job_ranker.py"),
             "--input", raw_csv,
             "--output", ranked_csv,
             "--top", "15"],
            capture_output=True, text=True, cwd=TOOLKIT_DIR
        )
        
        if result2.returncode != 0:
            print(f"  ❌ Ranker failed: {result2.stderr}")
        else:
            print(result2.stdout)
            
            # ─── Step 3: Excel Tracker ───────────────────────────
            print("\n📋 STEP 3: Generating Excel tracker...")
            tracker_path = os.path.join(OUTPUT_DIR, f"job_tracker_{date_str}.xlsx")
            
            result3 = subprocess.run(
                [sys.executable, os.path.join(TOOLKIT_DIR, "excel_tracker.py"),
                 "--input", ranked_csv,
                 "--output", tracker_path],
                capture_output=True, text=True, cwd=TOOLKIT_DIR
            )
            
            if result3.returncode != 0:
                print(f"  ❌ Tracker failed: {result3.stderr}")
            else:
                print(result3.stdout)
        
        log_entry = f"{timestamp} | OK | Completed full pipeline\n"
    
    # Write to log
    with open(log_path, "a") as f:
        f.write(log_entry)
    
    print("\n✅ Daily run complete!")
    print(f"📁 Data dir:   {DATA_DIR}")
    print(f"📁 Output dir: {OUTPUT_DIR}")


def setup_cron():
    """Set up a daily cron job (Linux/Mac)."""
    python_path = sys.executable
    script_path = os.path.abspath(__file__)
    
    cron_line = f"0 8 * * * cd {TOOLKIT_DIR} && {python_path} {script_path} >> {DATA_DIR}/cron_log.txt 2>&1"
    
    print("Setting up daily cron job (8:00 AM)...")
    print(f"\nCron entry:\n  {cron_line}")
    print(f"\nTo add manually:")
    print(f"  1. Run: crontab -e")
    print(f"  2. Add this line at the bottom:")
    print(f"     {cron_line}")
    print(f"  3. Save and exit")
    print(f"\nTo verify: crontab -l")
    
    try:
        # Try to add automatically
        import tempfile
        
        # Get existing crontab
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = existing.stdout if existing.returncode == 0 else ""
        
        if script_path in current_cron:
            print("\n⚠️  Cron job already exists!")
            return
        
        # Write new crontab
        new_cron = current_cron.rstrip() + "\n" + cron_line + "\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cron', delete=False) as f:
            f.write(new_cron)
            tmp_path = f.name
        
        result = subprocess.run(["crontab", tmp_path], capture_output=True, text=True)
        os.unlink(tmp_path)
        
        if result.returncode == 0:
            print("\n✅ Cron job added successfully!")
        else:
            print(f"\n❌ Failed to add cron: {result.stderr}")
            print("Please add manually using the instructions above.")
    except Exception as e:
        print(f"\n⚠️  Auto-setup failed ({e}). Please add manually.")


def setup_launchd():
    """Set up a macOS launchd agent for daily execution."""
    python_path = sys.executable
    script_path = os.path.abspath(__file__)
    
    plist_name = "com.jobtracker.daily"
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{plist_name}.plist")
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{plist_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{TOOLKIT_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{DATA_DIR}/launchd_log.txt</string>
    <key>StandardErrorPath</key>
    <string>{DATA_DIR}/launchd_error.txt</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>"""
    
    print("Setting up macOS launchd agent (daily at 8:00 AM)...")
    
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    with open(plist_path, "w") as f:
        f.write(plist_content)
    
    print(f"\n✅ LaunchAgent created: {plist_path}")
    print(f"\nTo activate:")
    print(f"  launchctl load {plist_path}")
    print(f"\nTo deactivate:")
    print(f"  launchctl unload {plist_path}")
    print(f"\nTo test immediately:")
    print(f"  launchctl start {plist_name}")


def show_windows_instructions():
    """Show Windows Task Scheduler setup instructions."""
    python_path = sys.executable
    script_path = os.path.abspath(__file__)
    
    print("Windows Task Scheduler Setup:")
    print("=" * 50)
    print(f"1. Open Task Scheduler (search 'Task Scheduler')")
    print(f"2. Click 'Create Basic Task'")
    print(f"3. Name: 'Daily Job Search'")
    print(f"4. Trigger: Daily at 8:00 AM")
    print(f"5. Action: Start a Program")
    print(f"   Program: {python_path}")
    print(f"   Arguments: {script_path}")
    print(f"   Start in: {TOOLKIT_DIR}")
    print(f"\nOr run via PowerShell:")
    print(f'  schtasks /create /tn "DailyJobSearch" /tr "{python_path} {script_path}" /sc daily /st 08:00')


def main():
    parser = argparse.ArgumentParser(description="Daily Job Search Automation")
    parser.add_argument("--setup-cron", action="store_true", help="Set up daily cron job")
    parser.add_argument("--setup-launchd", action="store_true", help="Set up macOS launchd agent")
    parser.add_argument("--setup-windows", action="store_true", help="Show Windows Task Scheduler instructions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    args = parser.parse_args()
    
    if args.setup_cron:
        setup_cron()
    elif args.setup_launchd:
        setup_launchd()
    elif args.setup_windows:
        show_windows_instructions()
    elif args.dry_run:
        print("DRY RUN — Would execute:")
        print(f"  1. job_scraper.py → {DATA_DIR}/jobs_raw.csv")
        print(f"  2. job_ranker.py  → {DATA_DIR}/jobs_ranked.csv")
        print(f"  3. excel_tracker.py → {OUTPUT_DIR}/job_tracker_YYYYMMDD.xlsx")
    else:
        run_daily()


if __name__ == "__main__":
    main()
