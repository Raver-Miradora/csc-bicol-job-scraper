"""
parsers.py — HTML parsing utilities for the CSC Career Opportunities portal.

Provides stateless helper functions that take raw HTML strings and return
structured Python dictionaries. The CSCScraper feeds HTML here; the results
feed into the filter and storage layers.

Note on portal structure:
  The CSC portal at https://www.csc.gov.ph/career-opportunities/ renders
  a table/list of job postings. Each row links to a detail page.
  Selectors here target the observed structure as of 2026 — update them
  if the portal layout changes (check raw_html stored in the DB).
"""

import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

from src.utils.logger import get_logger

log = get_logger(__name__)

# ── CSS selectors / patterns ──────────────────────────────────────────────────
# Centralised here so they are easy to update if the portal structure changes.

# Listing page: container that holds each job card/row
LISTING_CONTAINER_SELECTOR = "table.job-listings, div.job-list, div.views-row, table"

# Common date patterns
DATE_PATTERNS = [
    r"\b(\w+ \d{1,2},?\s*\d{4})\b",          # "June 30, 2026"
    r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",   # "06/30/2026" or "30-06-2026"
    r"\b(\d{4}-\d{2}-\d{2})\b",               # "2026-06-30"
]

# Salary grade pattern: "SG-18", "Salary Grade 18", "Grade 18"
SALARY_GRADE_PATTERN = re.compile(
    r"(?:salary\s*grade|sg)[^\d]*(\d{1,2})",
    re.IGNORECASE,
)

# Monthly salary: "₱50,820.00" or "P50,820"
MONTHLY_SALARY_PATTERN = re.compile(
    r"[₱P]\s*([\d,]+(?:\.\d{2})?)",
    re.IGNORECASE,
)


# ── Utility helpers ───────────────────────────────────────────────────────────

def _text(element: Optional[Tag], default: str = "") -> str:
    """Safely extract and strip text from a BeautifulSoup element."""
    if element is None:
        return default
    return element.get_text(separator=" ", strip=True)


def _find_text(soup: BeautifulSoup, *selectors: str, default: str = "") -> str:
    """Try a list of CSS selectors and return text from the first match."""
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            return _text(el)
    return default


def _extract_date(text: str) -> Optional[str]:
    """Extract the first recognisable date string from raw text."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_salary_grade(text: str) -> Optional[str]:
    """Extract salary grade number from free text. Returns e.g. '18'."""
    match = SALARY_GRADE_PATTERN.search(text)
    return match.group(1) if match else None


def _extract_monthly_salary(text: str) -> Optional[str]:
    """Extract formatted monthly salary string. Returns e.g. '₱50,820.00'."""
    match = MONTHLY_SALARY_PATTERN.search(text)
    if match:
        return f"₱{match.group(1)}"
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def parse_job_listing_page(html: str) -> list[dict]:
    """
    Parse the CSC portal job listing page.

    Returns a list of dicts with at minimum:
      - position_title (str)
      - job_url        (str | None)
      - location       (str)
      - agency         (str | None)
      - deadline_raw   (str | None)  — unprocessed deadline text

    Args:
        html: Raw HTML string of the listing page.

    Returns:
        List of job summary dicts (may be empty if page structure changed).
    """
    soup = BeautifulSoup(html, "lxml")
    jobs: list[dict] = []

    # ── Strategy 1: standard <table> rows ────────────────────────────────
    # The CSC portal historically renders jobs in a <table>. Each <tr>
    # (except the header) is one job. Adjust selectors as needed.
    rows = soup.select("table tr")
    if rows and len(rows) > 1:
        # Skip the header row
        header = [th.get_text(strip=True).lower() for th in rows[0].select("th, td")]
        for row in rows[1:]:
            cells = row.select("td")
            if not cells:
                continue
            job = _parse_table_row(cells, header)
            if job:
                jobs.append(job)
        if jobs:
            log.debug("Parsed {n} jobs from table rows", n=len(jobs))
            return jobs

    # ── Strategy 2: card/div layout ───────────────────────────────────────
    cards = soup.select("div.views-row, article.job-card, div.job-item, li.job")
    for card in cards:
        job = _parse_card(card)
        if job:
            jobs.append(job)

    if not jobs:
        log.warning("No jobs found — page structure may have changed.")

    log.debug("Parsed {n} jobs from page", n=len(jobs))
    return jobs


def _parse_table_row(cells: list[Tag], header: list[str]) -> Optional[dict]:
    """
    Parse a single <tr> into a job summary dict.
    Falls back to positional parsing if header mapping fails.
    """
    # Build a header→cell map
    col_map: dict[str, str] = {}
    for i, cell in enumerate(cells):
        key = header[i] if i < len(header) else f"col_{i}"
        col_map[key] = _text(cell)

    # Try to find the anchor link (job detail URL)
    link_tag = None
    for cell in cells:
        link_tag = cell.find("a", href=True)
        if link_tag:
            break

    # Resolve common column name variants
    def col(*names: str) -> str:
        for name in names:
            for k, v in col_map.items():
                if name in k:
                    return v
        return ""

    position = col("position", "title", "job", "post")
    location  = col("location", "office", "place", "station")
    agency    = col("agency", "department", "bureau", "office")
    deadline  = col("deadline", "closing", "date", "until")

    if not position:
        # Last resort: first non-empty cell text
        position = next((v for v in col_map.values() if v), "")

    if not position:
        return None

    return {
        "position_title": position,
        "location":       location or "N/A",
        "agency":         agency or None,
        "deadline_raw":   deadline or None,
        "job_url":        str(link_tag["href"]) if link_tag else None,
    }


def _parse_card(card: Tag) -> Optional[dict]:
    """Parse a div/article card element into a job summary dict."""
    title_el = card.select_one(
        "h2, h3, h4, .job-title, .position-title, .views-field-title a"
    )
    position = _text(title_el)
    if not position:
        return None

    link_tag = card.find("a", href=True)
    location_el = card.select_one(
        ".location, .office, .station, .views-field-field-location"
    )
    agency_el = card.select_one(
        ".agency, .department, .views-field-field-agency"
    )
    deadline_el = card.select_one(
        ".deadline, .closing-date, .views-field-field-deadline"
    )

    return {
        "position_title": position,
        "location":       _text(location_el) or "N/A",
        "agency":         _text(agency_el) or None,
        "deadline_raw":   _text(deadline_el) or None,
        "job_url":        str(link_tag["href"]) if link_tag else None,
    }


def parse_job_detail_page(html: str, base_url: str = "") -> dict:
    """
    Parse an individual CSC job detail page.

    Returns a dict with the full job metadata:
      - position_title
      - salary_grade
      - monthly_salary
      - location
      - agency
      - eligibility_requirements
      - application_deadline
      - job_url  (echo back)
      - raw_html (the original HTML for debugging)

    Args:
        html:     Raw HTML of the job detail page.
        base_url: The URL of this page (stored as job_url).
    """
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text(separator=" ", strip=True)

    # ── Position title ────────────────────────────────────────────────────
    position = _find_text(
        soup,
        "h1.page-header",
        "h1",
        ".field--name-title",
        ".job-title",
        default="",
    )

    # ── Location ──────────────────────────────────────────────────────────
    location = _find_text(
        soup,
        ".field--name-field-location",
        ".location",
        ".office-location",
        ".field-location",
        default="N/A",
    )

    # ── Agency / Department ───────────────────────────────────────────────
    agency = _find_text(
        soup,
        ".field--name-field-agency",
        ".agency",
        ".department",
        default=None,
    )

    # ── Salary grade & monthly salary — from structured fields first ──────
    salary_field = _find_text(
        soup,
        ".field--name-field-salary-grade",
        ".salary-grade",
        ".field-salary",
        default="",
    )
    salary_grade   = _extract_salary_grade(salary_field) or _extract_salary_grade(full_text)
    monthly_salary = _extract_monthly_salary(salary_field) or _extract_monthly_salary(full_text)

    # ── Eligibility ───────────────────────────────────────────────────────
    eligibility = _find_text(
        soup,
        ".field--name-field-eligibility",
        ".eligibility",
        ".qualification-standards",
        default=None,
    )
    if not eligibility:
        eligibility = _extract_eligibility_from_text(full_text)

    # ── Application deadline ──────────────────────────────────────────────
    deadline_raw = _find_text(
        soup,
        ".field--name-field-deadline",
        ".deadline",
        ".closing-date",
        ".application-deadline",
        default="",
    )
    deadline = _extract_date(deadline_raw) or _extract_date(full_text)

    log.debug(
        "Parsed detail: {title!r} | SG {sg} | {loc}",
        title=position[:50] if position else "?",
        sg=salary_grade,
        loc=location,
    )

    return {
        "position_title":          position,
        "salary_grade":            salary_grade,
        "monthly_salary":          monthly_salary,
        "location":                location,
        "agency":                  agency,
        "eligibility_requirements": eligibility,
        "application_deadline":    deadline,
        "job_url":                 base_url,
        "raw_html":                html,
    }


def _extract_eligibility_from_text(text: str) -> Optional[str]:
    """
    Attempt to extract eligibility information from unstructured page text.
    Looks for known patterns near the word 'eligibility'.
    """
    pattern = re.compile(
        r"eligibility[:\s]+([^\n\r]{5,200})",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return None


def extract_text(element: Optional[Tag]) -> str:
    """
    Public alias for _text() — safely extract and strip text from a BS4 element.
    Used by the CSCScraper when it needs direct element text.
    """
    return _text(element)


def extract_pagination_urls(html: str, base_url: str) -> list[str]:
    """
    Extract all pagination page URLs from a listing page.

    Returns a list of absolute URLs for pages 2, 3, … N.
    Page 1 is assumed already fetched and is NOT included.
    """
    from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []

    # Common pagination patterns
    pager_links = soup.select(
        "ul.pager a, nav.pager a, .pagination a, a[href*='page='], a[href*='?page']"
    )

    seen = set()
    for link in pager_links:
        href = link.get("href", "")
        if not href or href == "#":
            continue
        absolute = urljoin(base_url, href)
        if absolute not in seen and absolute != base_url:
            seen.add(absolute)
            urls.append(absolute)

    log.debug("Found {n} pagination URLs", n=len(urls))
    return urls
