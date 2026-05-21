"""
parsers.py — HTML parsing utilities for the CSC portal.

Implemented in Phase 3: HTTP Session & Scraper Foundation.
"""


def parse_job_listing_page(html: str) -> list:
    """Parse the main job listing page and return a list of job summaries."""
    raise NotImplementedError("Implemented in Phase 3.")


def parse_job_detail_page(html: str) -> dict:
    """Parse an individual job detail page and return structured data."""
    raise NotImplementedError("Implemented in Phase 3.")


def extract_text(element) -> str:
    """Safely extract and strip text from a BeautifulSoup element."""
    raise NotImplementedError("Implemented in Phase 3.")
