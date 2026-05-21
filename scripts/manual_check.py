"""
Manual one-time check script.
Useful for testing the scraper without the full scheduler.

Usage:
    python scripts/manual_check.py
"""

import asyncio
import sys

from src.core.tracker import JobTracker
from src.utils.logger import get_logger

log = get_logger(__name__)

async def run_manual_check():
    log.info("Executing manual check...")
    tracker = JobTracker()
    await tracker.run_check(force_notify=True)
    log.info("Manual check completed.")

def main():
    asyncio.run(run_manual_check())

if __name__ == "__main__":
    main()
