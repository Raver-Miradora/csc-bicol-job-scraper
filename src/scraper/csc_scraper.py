"""
csc_scraper.py — Core scraping logic for the CSC Career Opportunities portal.

Orchestrates the full scraping pipeline:
  1. Fetch the job listing page (with pagination)
  2. Parse each listing into a job summary
  3. Fetch each job's detail page
  4. Return fully-populated job dicts ready for filtering and storage

Design principles:
  - All HTTP goes through SessionManager (rate limiting, retries, UA rotation)
  - All HTML parsing goes through parsers.py (testable, stateless functions)
  - Idempotency is the caller's concern (Database layer deduplicates by hash)
  - CAPTCHA detection triggers a warning + graceful abort (no crash)
  - Absolute URLs are resolved before returning
"""

import hashlib
from typing import Optional
from urllib.parse import urljoin, urlparse

from src.scraper.parsers import (
    extract_pagination_urls,
    parse_job_detail_page,
    parse_job_listing_page,
)
from src.scraper.session_manager import SessionManager
from src.utils.logger import get_logger

log = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://www.csc.gov.ph/career-opportunities/"

# Strings that indicate a CAPTCHA / bot-protection page
CAPTCHA_SIGNALS = [
    "captcha",
    "recaptcha",
    "cloudflare",
    "access denied",
    "bot protection",
    "please verify",
    "i am not a robot",
    "ddos-guard",
]

# Minimum content length for a valid page response (bytes)
MIN_VALID_CONTENT_LENGTH = 500


# ── CSCScraper ────────────────────────────────────────────────────────────────

class CSCScraper:
    """
    Main scraper for the Philippine CSC Career Opportunities portal.

    Usage:
        config = {
            "base_url": "https://www.csc.gov.ph/career-opportunities/",
            "rate_limit_seconds": 3,
            "timeout_seconds": 30,
            "max_retries": 3,
            "fetch_details": True,   # Set False for listing-only (faster)
        }
        scraper = CSCScraper(config)
        jobs = scraper.fetch_job_listings()
        # jobs → list of dicts ready to be filtered and inserted into DB
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Dict loaded from config.yaml (scraper section).
                    Recognised keys:
                      base_url             (str)   Portal listing URL
                      rate_limit_seconds   (float) Seconds between requests
                      timeout_seconds      (int)   Request timeout
                      max_retries          (int)   Retry attempts
                      fetch_details        (bool)  Whether to fetch detail pages
        """
        self.base_url: str = config.get("base_url", DEFAULT_BASE_URL)
        self.fetch_details: bool = config.get("fetch_details", True)

        self._session = SessionManager(
            rate_limit=float(config.get("rate_limit_seconds", 3)),
            timeout=int(config.get("timeout_seconds", 30)),
            max_retries=int(config.get("max_retries", 3)),
        )

        log.info(
            "CSCScraper initialised — base_url={url} fetch_details={fd}",
            url=self.base_url,
            fd=self.fetch_details,
        )

    # ── Public API ────────────────────────────────────────────────────────

    def fetch_job_listings(self) -> list[dict]:
        """
        Full scraping pipeline: listing pages → (optional) detail pages.

        Returns:
            List of job dicts. Each dict contains at minimum:
              job_hash, position_title, location, agency, salary_grade,
              monthly_salary, eligibility_requirements, application_deadline,
              job_url, raw_html.

        Empty list is returned on unrecoverable errors (CAPTCHA, network down).
        """
        log.info("Starting job listing fetch from {url}", url=self.base_url)

        # ── Step 1: Collect all listing-page URLs (page 1 + paginated) ───
        all_listing_urls = self._collect_listing_urls()
        if not all_listing_urls:
            log.warning("No listing URLs collected — aborting.")
            return []

        # ── Step 2: Scrape job summaries from every listing page ──────────
        job_summaries: list[dict] = []
        for url in all_listing_urls:
            summaries = self._scrape_listing_page(url)
            job_summaries.extend(summaries)

        log.info("Collected {n} job summaries across all pages", n=len(job_summaries))

        if not job_summaries:
            return []

        # ── Step 3: (Optional) Fetch detail pages ─────────────────────────
        if not self.fetch_details:
            # Add minimal hashes and return summaries as-is
            return [self._attach_hash(j) for j in job_summaries]

        full_jobs: list[dict] = []
        for i, summary in enumerate(job_summaries, start=1):
            detail_url = self._resolve_url(summary.get("job_url", ""))
            if not detail_url:
                log.warning(
                    "No detail URL for job {i}/{n}: {title!r} — using summary only",
                    i=i,
                    n=len(job_summaries),
                    title=summary.get("position_title", "?"),
                )
                full_jobs.append(self._attach_hash(summary))
                continue

            detail = self.parse_job_detail_page(detail_url)
            if detail:
                # Merge: detail data takes precedence over summary
                merged = {**summary, **detail}
                full_jobs.append(self._attach_hash(merged))
            else:
                # Fall back to summary if detail fetch failed
                log.warning(
                    "Detail fetch failed for [{i}/{n}] {url} — using summary",
                    i=i,
                    n=len(job_summaries),
                    url=detail_url,
                )
                full_jobs.append(self._attach_hash(summary))

        log.info(
            "Scraping complete — {n} jobs collected",
            n=len(full_jobs),
        )
        return full_jobs

    def parse_job_detail_page(self, job_url: str) -> Optional[dict]:
        """
        Fetch and parse a single job detail page.

        Args:
            job_url: Absolute URL of the job detail page.

        Returns:
            Parsed job dict, or None on failure.
        """
        html = self._fetch_page(job_url)
        if html is None:
            return None
        return parse_job_detail_page(html, base_url=job_url)

    def extract_job_metadata(self, html: str) -> dict:
        """
        Parse job metadata from a raw HTML string of a detail page.

        Useful for offline/testing scenarios where HTML is already available.

        Args:
            html: Raw HTML string.

        Returns:
            Parsed job dict (no job_hash — caller must add it).
        """
        return parse_job_detail_page(html)

    def handle_pagination(self, base_url: str) -> list[str]:
        """
        Fetch the first page and extract all paginated page URLs.

        Returns:
            List of page URLs (page 2 onwards). Empty if single-page or error.
        """
        html = self._fetch_page(base_url)
        if html is None:
            return []
        return extract_pagination_urls(html, base_url)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _collect_listing_urls(self) -> list[str]:
        """
        Build the full list of listing page URLs to scrape.

        Returns [base_url, page2_url, page3_url, ...].
        """
        # Always start with page 1
        urls = [self.base_url]

        # Fetch page 1 to discover pagination
        html = self._fetch_page(self.base_url)
        if html is None:
            return []

        paginated = extract_pagination_urls(html, self.base_url)
        urls.extend(paginated)

        log.debug(
            "Found {n} total listing pages to scrape", n=len(urls)
        )
        return urls

    def _scrape_listing_page(self, url: str) -> list[dict]:
        """
        Fetch and parse a single listing page.

        Returns list of job summary dicts (may be empty).
        """
        html = self._fetch_page(url)
        if html is None:
            return []

        summaries = parse_job_listing_page(html)
        log.debug(
            "Parsed {n} summaries from {url}",
            n=len(summaries),
            url=url,
        )

        # Resolve relative URLs to absolute
        for job in summaries:
            if job.get("job_url"):
                job["job_url"] = self._resolve_url(job["job_url"])

        return summaries

    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a URL and return the response HTML as a string.

        Returns None on error, CAPTCHA detection, or thin content.
        """
        try:
            response = self._session.get(url)
        except Exception as exc:
            log.error("Failed to fetch {url}: {exc}", url=url, exc=exc)
            return None

        if response.status_code != 200:
            log.warning(
                "Non-200 response {status} for {url}",
                status=response.status_code,
                url=url,
            )
            return None

        html = response.text

        # Guard: content too short to be a real page
        if len(response.content) < MIN_VALID_CONTENT_LENGTH:
            log.warning(
                "Suspiciously short response ({n} bytes) for {url}",
                n=len(response.content),
                url=url,
            )
            return None

        # Guard: CAPTCHA detection
        if self._detect_captcha(html):
            log.warning(
                "⚠️  CAPTCHA or bot protection detected at {url}. "
                "Consider adding delays or using playwright mode.",
                url=url,
            )
            return None

        return html

    def _detect_captcha(self, html: str) -> bool:
        """
        Return True if the page looks like a CAPTCHA or bot-protection wall.

        Checks for known signal strings in a case-insensitive manner.
        """
        html_lower = html.lower()
        for signal in CAPTCHA_SIGNALS:
            if signal in html_lower:
                return True
        return False

    def _resolve_url(self, url: str) -> str:
        """
        Resolve a relative URL against the base URL.

        Returns empty string if url is empty/None.
        """
        if not url:
            return ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin(self.base_url, url)

    @staticmethod
    def _attach_hash(job: dict) -> dict:
        """
        Compute and attach a SHA-256 job_hash to the job dict.

        Hash source priority:
          1. job_url  (most stable unique identifier)
          2. position_title + agency + application_deadline composite
        """
        source = (
            job.get("job_url")
            or (
                f"{job.get('position_title', '')}|"
                f"{job.get('agency', '')}|"
                f"{job.get('application_deadline', '')}"
            )
        )
        job["job_hash"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return job

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return f"CSCScraper(base_url={self.base_url!r})"
