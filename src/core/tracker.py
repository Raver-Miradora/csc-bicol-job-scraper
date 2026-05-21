"""
tracker.py — Core application orchestration logic.

Implemented in Phase 9: Core Application Loop.
"""

import os
import asyncio
from typing import List, Dict

from src.utils.logger import get_logger
from src.config.settings import load_config
from src.scraper.csc_scraper import CSCScraper
from src.filters.job_matcher import JobMatcher
from src.storage.database import Database
from src.notifications.telegram_notifier import TelegramNotifier
from src.notifications.discord_notifier import DiscordNotifier
from src.config.constants import DEFAULT_DB_PATH

log = get_logger(__name__)

class JobTracker:
    """Core orchestration class that glues all components together."""

    def __init__(self, config_path: str = "config/config.yaml"):
        # Load Config
        self.config = load_config(config_path)
        
        # Initialize Database
        db_path = self.config.get("database.path", DEFAULT_DB_PATH)
        # Ensure parent directory of db exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = Database(db_path)
        self.db.initialize()
        
        # Initialize Scraper
        # Fetch listing only by default, then selectively fetch details for matching jobs to save bandwidth
        self.scraper_config = self.config.get("scraper", {})
        self.scraper_config["fetch_details"] = False
        
        # Initialize Filters
        self.matcher = JobMatcher(self.config.get("filters", {}))
        
        # Initialize Notifiers
        self.notifiers = []
        
        # Setup Telegram
        if self.config.get("notifications.telegram.enabled", False):
            tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
            tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if tg_token and tg_chat_id:
                self.notifiers.append(("telegram", TelegramNotifier(tg_token, tg_chat_id)))
            else:
                log.warning("Telegram enabled but missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
                
        # Setup Discord
        if self.config.get("notifications.discord.enabled", False):
            discord_url = os.getenv("DISCORD_WEBHOOK_URL")
            if discord_url:
                self.notifiers.append(("discord", DiscordNotifier(discord_url)))
            else:
                log.warning("Discord enabled but missing DISCORD_WEBHOOK_URL.")

    async def run_check(self, force_notify: bool = False):
        """Run a single iteration of the job check loop."""
        from src.utils.logger import time_operation
        
        log.info("Starting job check cycle...")
        
        # 1. Fetch raw summaries
        with time_operation("full_scraping_cycle"):
            with CSCScraper(self.scraper_config) as scraper:
                summaries = scraper.fetch_job_listings()
                
                if not summaries:
                    log.info("No job listings found.")
                    return

            log.info(f"Fetched {len(summaries)} job summaries. Filtering...")
            
            # 2. Filter using JobMatcher (first pass based on summary info like Location/Title)
            # Many listings already have location and basic info.
            # If the matcher is strict, this saves fetching details for everything.
            potential_matches = self.matcher.filter_jobs(summaries)
            log.info(f"Found {len(potential_matches)} potential matches after summary filter.")
            
            new_matches = []
            
            # 3. For each potential match, fetch full details and re-verify
            for summary in potential_matches:
                job_hash = summary.get("job_hash")
                
                # Check if we already processed this job
                if not force_notify and self.db.job_exists(job_hash):
                    log.debug(f"Job {job_hash} already in database. Skipping details.")
                    continue
                    
                # Fetch full details
                url = summary.get("job_url")
                if not url:
                    continue
                    
                details = scraper.parse_job_detail_page(url)
                if not details:
                    log.warning(f"Failed to fetch details for {url}")
                    continue
                    
                # Merge summary and details
                full_job = {**summary, **details}
                
                # Re-verify with full details (especially Eligibility and Salary Grade)
                if self.matcher.is_match(full_job):
                    # Insert to DB
                    if self.db.insert_job(full_job) or force_notify:
                        new_matches.append(full_job)
                        
            # 4. Notify about new matches
            if new_matches:
                log.info(f"Found {len(new_matches)} NEW valid job postings!")
                await self._dispatch_notifications(new_matches)
            else:
                log.info("No new job postings to notify.")
                
            log.info("Job check cycle completed.")

    async def _dispatch_notifications(self, jobs: List[Dict]):
        """Send notifications to all configured channels."""
        for job in jobs:
            for name, notifier in self.notifiers:
                success = False
                try:
                    if name == "telegram":
                        success = await notifier.send_job_alert(job)
                    elif name == "discord":
                        # discord is synchronous using requests under the hood in our implementation
                        success = notifier.send_embed(job)
                except Exception as e:
                    log.error(f"Error sending {name} notification: {str(e)}")
                    
                # Record the notification attempt
                self.db.mark_as_notified(job.get("job_hash"), name, success)
                
                if not success:
                    log.warning(f"Failed to send {name} notification for job {job.get('job_hash')}")

    async def send_daily_summary(self):
        """Send a daily summary of newly found jobs."""
        log.info("Generating daily summary...")
        unnotified_jobs = self.db.get_unnotified_jobs("telegram_summary")
        
        if not unnotified_jobs:
            log.info("No unnotified jobs for daily summary.")
            # We can still send an empty summary if configured, but default skip
            return
            
        for name, notifier in self.notifiers:
            if name == "telegram":
                success = await notifier.send_daily_summary(unnotified_jobs)
                if success:
                    for job in unnotified_jobs:
                        self.db.mark_as_notified(job.get("job_hash"), "telegram_summary", True)

