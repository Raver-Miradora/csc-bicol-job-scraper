"""
csc_scraper.py — Core scraping logic for the CSC Career Opportunities portal.

Implemented in Phase 4: Core Scraper Logic.
"""


class CSCScraper:
    """Main scraper for the CSC job portal."""

    def __init__(self, config: dict):
        raise NotImplementedError("Implemented in Phase 4.")

    def fetch_job_listings(self) -> list:
        raise NotImplementedError("Implemented in Phase 4.")

    def parse_job_detail_page(self, job_url: str) -> dict:
        raise NotImplementedError("Implemented in Phase 4.")

    def extract_job_metadata(self, html: str) -> dict:
        raise NotImplementedError("Implemented in Phase 4.")

    def handle_pagination(self, base_url: str) -> list:
        raise NotImplementedError("Implemented in Phase 4.")
