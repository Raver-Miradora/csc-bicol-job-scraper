"""
test_csc_scraper.py — Integration tests for Phase 4: CSCScraper.

All HTTP calls are mocked — no real network traffic.
Run with:
    pytest tests/test_csc_scraper.py -v
"""

from unittest.mock import MagicMock, call, patch

import pytest

from src.scraper.csc_scraper import CAPTCHA_SIGNALS, MIN_VALID_CONTENT_LENGTH, CSCScraper

# ── Shared HTML fixtures ───────────────────────────────────────────────────────

# Padding comment to meet MIN_VALID_CONTENT_LENGTH (500 bytes) ──────────────────
_PAD = "<!-- csc-bicol-job-scraper test fixture padding --" + "-" * 300 + ">"

LISTING_PAGE_HTML = f"""
<html><body>
{_PAD}
<table>
  <tr>
    <th>Position</th><th>Agency</th><th>Location</th><th>Deadline</th>
  </tr>
  <tr>
    <td><a href="/jobs/admin-officer-iv">Administrative Officer IV</a></td>
    <td>Provincial Government of Camarines Sur</td>
    <td>Camarines Sur</td>
    <td>June 30, 2026</td>
  </tr>
  <tr>
    <td><a href="/jobs/it-officer-i">IT Officer I</a></td>
    <td>Municipality of Goa</td>
    <td>Goa, Camarines Sur</td>
    <td>July 15, 2026</td>
  </tr>
</table>
</body></html>
"""

LISTING_WITH_PAGINATION_HTML = f"""
<html><body>
{_PAD}
<table>
  <tr><th>Position</th><th>Agency</th><th>Location</th><th>Deadline</th></tr>
  <tr>
    <td><a href="/jobs/nurse-ii">Nurse II</a></td>
    <td>Sorsogon Provincial Hospital</td>
    <td>Sorsogon City</td>
    <td>August 1, 2026</td>
  </tr>
</table>
<ul class="pager">
  <li><a href="?page=2">2</a></li>
</ul>
</body></html>
"""

PAGE_2_HTML = f"""
<html><body>
{_PAD}
<table>
  <tr><th>Position</th><th>Agency</th><th>Location</th><th>Deadline</th></tr>
  <tr>
    <td><a href="/jobs/engineer-i">Engineer I</a></td>
    <td>DPWH Region V</td>
    <td>Albay</td>
    <td>August 15, 2026</td>
  </tr>
</table>
</body></html>
"""

DETAIL_HTML = f"""
<html><body>
{_PAD}
  <h1 class="page-header">Administrative Officer IV</h1>
  <div class="field--name-field-agency">Provincial Government of Camarines Sur</div>
  <div class="field--name-field-location">Camarines Sur</div>
  <div class="field--name-field-salary-grade">Salary Grade 18 — \u20b150,820.00/month</div>
  <div class="field--name-field-eligibility">Career Service Professional (Second Level)</div>
  <div class="field--name-field-deadline">June 30, 2026</div>
</body></html>
"""

CAPTCHA_HTML = f"""
<html><body>
{_PAD}
  <h1>Please verify you are not a robot</h1>
  <div class="captcha">Complete the CAPTCHA to continue</div>
</body></html>
"""

EMPTY_HTML = f"<html><body>{_PAD}<p>No jobs found.</p></body></html>"

# Intentionally short — used to test the thin-content guard
THIN_HTML = "<html><body><p>Hi</p></body></html>"


# ── Fixtures ───────────────────────────────────────────────────────────────────

def make_config(**overrides) -> dict:
    base = {
        "base_url": "https://www.csc.gov.ph/career-opportunities/",
        "rate_limit_seconds": 0,   # No delay in tests
        "timeout_seconds": 5,
        "max_retries": 1,
        "fetch_details": False,    # Listing-only by default for speed
    }
    base.update(overrides)
    return base


def make_response(html: str, status: int = 200) -> MagicMock:
    """Build a mock requests.Response from an HTML string."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    resp.content = html.encode("utf-8")
    resp.headers = {}
    return resp


def patch_session(scraper: CSCScraper, side_effect=None, return_value=None):
    """
    Patch the scraper's internal session instance directly.
    Returns the mock object so tests can inspect calls.
    """
    mock = MagicMock()
    if side_effect is not None:
        mock.side_effect = side_effect
    elif return_value is not None:
        mock.return_value = return_value
    scraper._session.get = mock
    return mock


# ── Initialisation ─────────────────────────────────────────────────────────────

class TestCSCScraperInit:
    def test_repr(self):
        scraper = CSCScraper(make_config())
        assert "csc.gov.ph" in repr(scraper)

    def test_custom_base_url(self):
        scraper = CSCScraper(make_config(base_url="https://example.com/jobs/"))
        assert scraper.base_url == "https://example.com/jobs/"

    def test_fetch_details_default_true(self):
        cfg = make_config()
        del cfg["fetch_details"]
        scraper = CSCScraper(cfg)
        assert scraper.fetch_details is True

    def test_fetch_details_configurable(self):
        scraper = CSCScraper(make_config(fetch_details=False))
        assert scraper.fetch_details is False


# ── _detect_captcha ────────────────────────────────────────────────────────────

class TestDetectCaptcha:
    def setup_method(self):
        self.scraper = CSCScraper(make_config())

    def test_detects_captcha_keyword(self):
        assert self.scraper._detect_captcha(CAPTCHA_HTML) is True

    def test_no_false_positive_on_normal_html(self):
        assert self.scraper._detect_captcha(LISTING_PAGE_HTML) is False

    def test_case_insensitive_detection(self):
        assert self.scraper._detect_captcha("<html>CAPTCHA required</html>") is True

    def test_detects_cloudflare_signal(self):
        assert self.scraper._detect_captcha("<html>Cloudflare protection</html>") is True

    def test_detects_access_denied(self):
        assert self.scraper._detect_captcha("<html>Access Denied</html>") is True

    def test_all_signals_detected(self):
        for signal in CAPTCHA_SIGNALS:
            html = f"<html><body>{signal}</body></html>"
            assert self.scraper._detect_captcha(html) is True, f"Signal not detected: {signal}"


# ── _resolve_url ───────────────────────────────────────────────────────────────

class TestResolveUrl:
    def setup_method(self):
        self.scraper = CSCScraper(make_config(
            base_url="https://www.csc.gov.ph/career-opportunities/"
        ))

    def test_absolute_url_unchanged(self):
        url = "https://www.csc.gov.ph/jobs/admin-iv"
        assert self.scraper._resolve_url(url) == url

    def test_relative_url_resolved(self):
        result = self.scraper._resolve_url("/jobs/admin-iv")
        assert result == "https://www.csc.gov.ph/jobs/admin-iv"

    def test_empty_returns_empty(self):
        assert self.scraper._resolve_url("") == ""

    def test_none_returns_empty(self):
        assert self.scraper._resolve_url(None) == ""


# ── _attach_hash ───────────────────────────────────────────────────────────────

class TestAttachHash:
    def test_hash_added_from_url(self):
        job = {"job_url": "https://csc.gov.ph/jobs/001", "position_title": "Officer"}
        result = CSCScraper._attach_hash(job)
        assert "job_hash" in result
        assert len(result["job_hash"]) == 64

    def test_hash_deterministic(self):
        job = {"job_url": "https://csc.gov.ph/jobs/001"}
        h1 = CSCScraper._attach_hash(dict(job))["job_hash"]
        h2 = CSCScraper._attach_hash(dict(job))["job_hash"]
        assert h1 == h2

    def test_hash_falls_back_to_composite(self):
        job = {
            "position_title": "Engineer I",
            "agency": "DPWH",
            "application_deadline": "2026-08-01",
        }
        result = CSCScraper._attach_hash(job)
        assert "job_hash" in result
        assert len(result["job_hash"]) == 64

    def test_different_urls_different_hashes(self):
        h1 = CSCScraper._attach_hash({"job_url": "https://csc.gov.ph/jobs/001"})["job_hash"]
        h2 = CSCScraper._attach_hash({"job_url": "https://csc.gov.ph/jobs/002"})["job_hash"]
        assert h1 != h2


# ── _fetch_page ────────────────────────────────────────────────────────────────

class TestFetchPage:
    def setup_method(self):
        self.scraper = CSCScraper(make_config())

    def test_returns_html_on_200(self):
        patch_session(self.scraper, return_value=make_response(LISTING_PAGE_HTML))
        result = self.scraper._fetch_page("https://csc.gov.ph/")
        assert result == LISTING_PAGE_HTML

    def test_returns_none_on_non_200(self):
        patch_session(self.scraper, return_value=make_response("Not Found", status=404))
        result = self.scraper._fetch_page("https://csc.gov.ph/")
        assert result is None

    def test_returns_none_on_captcha(self):
        patch_session(self.scraper, return_value=make_response(CAPTCHA_HTML))
        result = self.scraper._fetch_page("https://csc.gov.ph/")
        assert result is None

    def test_returns_none_on_thin_content(self):
        patch_session(self.scraper, return_value=make_response(THIN_HTML))
        result = self.scraper._fetch_page("https://csc.gov.ph/")
        assert result is None

    def test_returns_none_on_network_error(self):
        import requests
        patch_session(self.scraper, side_effect=[requests.ConnectionError("no route")])
        result = self.scraper._fetch_page("https://csc.gov.ph/")
        assert result is None


# ── fetch_job_listings (listing-only mode) ─────────────────────────────────────

class TestFetchJobListingsNoDetails:
    def setup_method(self):
        self.scraper = CSCScraper(make_config(fetch_details=False))

    def test_returns_jobs_from_single_page(self):
        patch_session(self.scraper, return_value=make_response(LISTING_PAGE_HTML))
        jobs = self.scraper.fetch_job_listings()
        assert len(jobs) == 2

    def test_all_jobs_have_hash(self):
        patch_session(self.scraper, return_value=make_response(LISTING_PAGE_HTML))
        jobs = self.scraper.fetch_job_listings()
        assert all("job_hash" in j for j in jobs)

    def test_all_jobs_have_position_title(self):
        patch_session(self.scraper, return_value=make_response(LISTING_PAGE_HTML))
        jobs = self.scraper.fetch_job_listings()
        assert all(j.get("position_title") for j in jobs)

    def test_returns_empty_on_empty_page(self):
        patch_session(self.scraper, return_value=make_response(EMPTY_HTML))
        jobs = self.scraper.fetch_job_listings()
        assert jobs == []

    def test_returns_empty_on_fetch_failure(self):
        import requests
        patch_session(self.scraper, side_effect=[requests.ConnectionError()])
        jobs = self.scraper.fetch_job_listings()
        assert jobs == []

    def test_handles_pagination(self):
        patch_session(self.scraper, side_effect=[
            make_response(LISTING_WITH_PAGINATION_HTML),  # page 1 (listing + pagination discovery)
            make_response(PAGE_2_HTML),                   # page 2
        ])
        jobs = self.scraper.fetch_job_listings()
        assert len(jobs) >= 1

    def test_job_urls_are_absolute(self):
        patch_session(self.scraper, return_value=make_response(LISTING_PAGE_HTML))
        jobs = self.scraper.fetch_job_listings()
        for job in jobs:
            url = job.get("job_url", "")
            if url:
                assert url.startswith("https://"), f"Non-absolute URL: {url}"


# ── fetch_job_listings (with details) ────────────────────────────────────────

class TestFetchJobListingsWithDetails:
    def setup_method(self):
        self.scraper = CSCScraper(make_config(fetch_details=True))

    def test_fetches_detail_pages(self):
        import requests

        # _collect_listing_urls fetches page 1 once, then _scrape_listing_page
        # fetches it again — so we need two listing responses before the details.
        patch_session(self.scraper, side_effect=[
            make_response(LISTING_PAGE_HTML),   # _collect_listing_urls (page 1)
            make_response(LISTING_PAGE_HTML),   # _scrape_listing_page  (page 1)
            make_response(DETAIL_HTML),          # detail job 1
            make_response(DETAIL_HTML),          # detail job 2
        ])
        jobs = self.scraper.fetch_job_listings()
        assert len(jobs) == 2
        assert any(j.get("salary_grade") == "18" for j in jobs)

    def test_falls_back_to_summary_if_detail_fails(self):
        import requests

        # Same double-fetch pattern for page 1
        patch_session(self.scraper, side_effect=[
            make_response(LISTING_PAGE_HTML),    # _collect_listing_urls
            make_response(LISTING_PAGE_HTML),    # _scrape_listing_page
            requests.ConnectionError(),           # detail 1 fails → fallback to summary
            make_response(DETAIL_HTML),           # detail 2 OK
        ])
        jobs = self.scraper.fetch_job_listings()
        assert len(jobs) == 2

    def test_all_jobs_have_hash_with_details(self):
        patch_session(self.scraper, side_effect=[
            make_response(LISTING_PAGE_HTML),   # _collect_listing_urls
            make_response(LISTING_PAGE_HTML),   # _scrape_listing_page
            make_response(DETAIL_HTML),
            make_response(DETAIL_HTML),
        ])
        jobs = self.scraper.fetch_job_listings()
        assert all("job_hash" in j for j in jobs)


# ── parse_job_detail_page ─────────────────────────────────────────────────────

class TestParseJobDetailPage:
    def setup_method(self):
        self.scraper = CSCScraper(make_config())

    def test_returns_parsed_dict(self):
        patch_session(self.scraper, return_value=make_response(DETAIL_HTML))
        result = self.scraper.parse_job_detail_page(
            "https://csc.gov.ph/jobs/admin-officer-iv"
        )
        assert result is not None
        assert result["position_title"] == "Administrative Officer IV"
        assert result["salary_grade"] == "18"

    def test_returns_none_on_fetch_failure(self):
        import requests
        patch_session(self.scraper, side_effect=[requests.ConnectionError()])
        result = self.scraper.parse_job_detail_page("https://csc.gov.ph/jobs/x")
        assert result is None

    def test_returns_none_on_captcha(self):
        patch_session(self.scraper, return_value=make_response(CAPTCHA_HTML))
        result = self.scraper.parse_job_detail_page("https://csc.gov.ph/jobs/x")
        assert result is None


# ── extract_job_metadata ───────────────────────────────────────────────────────

class TestExtractJobMetadata:
    def setup_method(self):
        self.scraper = CSCScraper(make_config())

    def test_parses_position_title(self):
        result = self.scraper.extract_job_metadata(DETAIL_HTML)
        assert result["position_title"] == "Administrative Officer IV"

    def test_parses_salary_grade(self):
        result = self.scraper.extract_job_metadata(DETAIL_HTML)
        assert result["salary_grade"] == "18"

    def test_parses_eligibility(self):
        result = self.scraper.extract_job_metadata(DETAIL_HTML)
        assert "Career Service Professional" in (result["eligibility_requirements"] or "")


# ── handle_pagination ─────────────────────────────────────────────────────────

class TestHandlePagination:
    def setup_method(self):
        self.scraper = CSCScraper(make_config())

    def test_returns_paginated_urls(self):
        patch_session(self.scraper, return_value=make_response(LISTING_WITH_PAGINATION_HTML))
        urls = self.scraper.handle_pagination(
            "https://www.csc.gov.ph/career-opportunities/"
        )
        assert len(urls) == 1
        assert all(u.startswith("https://") for u in urls)

    def test_returns_empty_on_single_page(self):
        patch_session(self.scraper, return_value=make_response(LISTING_PAGE_HTML))
        urls = self.scraper.handle_pagination(
            "https://www.csc.gov.ph/career-opportunities/"
        )
        assert urls == []

    def test_returns_empty_on_fetch_failure(self):
        import requests
        patch_session(self.scraper, side_effect=[requests.ConnectionError()])
        urls = self.scraper.handle_pagination("https://csc.gov.ph/")
        assert urls == []


# ── Context manager ────────────────────────────────────────────────────────────

class TestContextManager:
    def test_context_manager_works(self):
        with CSCScraper(make_config(fetch_details=False)) as scraper:
            patch_session(scraper, return_value=make_response(LISTING_PAGE_HTML))
            jobs = scraper.fetch_job_listings()
        assert len(jobs) >= 0  # No crash = success
