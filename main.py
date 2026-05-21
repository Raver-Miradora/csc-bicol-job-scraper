"""
CSC Bicol Job Scraper — CLI Entry Point

Commands:
  start       Start automated monitoring (runs continuously)
  check       Perform a one-time manual check
  stats       Display tracking statistics

Usage:
    python main.py start
    python main.py check --notify
    python main.py stats
"""

import sys
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

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python main.py [start|check|stats]")
        return
        
    cmd = args[0].lower()
    
    if cmd == "start":
        start_loop()
    elif cmd == "check":
        force_notify = "--notify" in args
        asyncio.run(run_check_once(force_notify=force_notify))
    elif cmd == "stats":
        print_stats()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python main.py [start|check|stats]")

if __name__ == "__main__":
    main()
