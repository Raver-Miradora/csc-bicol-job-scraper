"""
CSC Bicol Job Scraper — CLI Entry Point

Commands:
  start       Start automated monitoring (runs continuously)
  check       Perform a one-time manual check
  stats       Display tracking statistics
  config      Configure notification settings
  test        Test notification delivery

Usage:
    python main.py start
    python main.py check --notify
    python main.py stats
    python main.py config --setup
    python main.py test
"""

import sys
import os
import asyncio
from src.core.tracker import JobTracker
from src.utils.logger import get_logger

log = get_logger(__name__)

async def run_check_once(force_notify=False):
    tracker = JobTracker()
    await tracker.run_check(force_notify=force_notify)

def start_loop():
    import schedule
    import time
    
    tracker = JobTracker()
    
    def job():
        asyncio.run(tracker.run_check())
        
    def summary_job():
        asyncio.run(tracker.send_daily_summary())
    
    interval = tracker.config.get("app.check_interval_minutes", 60)
    schedule.every(interval).minutes.do(job)
    
    # Daily summary at 5 PM if enabled
    if tracker.config.get("app.daily_summary", True):
        summary_time = tracker.config.get("app.summary_time", "17:00")
        schedule.every().day.at(summary_time).do(summary_job)
        
    log.info(f"Started monitoring loop. Checking every {interval} minutes.")
    
    # Run once immediately
    job()
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def print_stats():
    tracker = JobTracker()
    stats = tracker.db.get_statistics()
    print("\n--- Tracking Statistics ---")
    print(f"Total Jobs Tracked: {stats.total_jobs_tracked}")
    print(f"Total Notifications Sent: {stats.total_notifications_sent}")
    print(f"Notification Success Rate: {stats.notification_success_rate:.1f}%")
    print(f"Last Scraped: {stats.last_scraped or 'Never'}")
    print("---------------------------\n")

async def test_notifications():
    print("Testing Notification Delivery...")
    tracker = JobTracker()
    if not tracker.notifiers:
        print("No notifiers are configured or enabled! Please check your config.yaml and .env files.")
        return
        
    test_job = {
        "position_title": "Test Position (CLI Test)",
        "agency": "CSC Test Agency",
        "location": "Test Region",
        "salary_grade": "99",
        "monthly_salary": "P99,999",
        "application_deadline": "2099-12-31",
        "job_url": "https://csc.gov.ph/career",
        "job_hash": "test_hash"
    }
    
    await tracker._dispatch_notifications([test_job])
    print("Test notifications dispatched.")

def setup_config():
    print("CSC Job Scraper - Configuration Setup")
    tg_token = input("Enter Telegram Bot Token (leave blank to skip): ").strip()
    tg_chat_id = input("Enter Telegram Chat ID (leave blank to skip): ").strip()
    discord_url = input("Enter Discord Webhook URL (leave blank to skip): ").strip()
    
    env_content = ""
    if tg_token and tg_chat_id:
        env_content += f"TELEGRAM_BOT_TOKEN={tg_token}\nTELEGRAM_CHAT_ID={tg_chat_id}\n"
    if discord_url:
        env_content += f"DISCORD_WEBHOOK_URL={discord_url}\n"
        
    if env_content:
        with open(".env", "w") as f:
            f.write(env_content)
        print("Successfully saved .env file!")
    else:
        print("No tokens provided. Setup skipped.")

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python main.py [start|check|stats|config|test]")
        return
        
    cmd = args[0].lower()
    
    if cmd == "start":
        start_loop()
    elif cmd == "check":
        force_notify = "--notify" in args
        asyncio.run(run_check_once(force_notify=force_notify))
    elif cmd == "stats":
        print_stats()
    elif cmd == "test":
        asyncio.run(test_notifications())
    elif cmd == "config":
        if "--setup" in args:
            setup_config()
        else:
            print("Usage: python main.py config --setup")
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python main.py [start|check|stats|config|test]")

if __name__ == "__main__":
    main()
