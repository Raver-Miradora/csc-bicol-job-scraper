"""
test_scraper.py — Unit tests for Phase 3: SessionManager and Parsers.

Uses unittest.mock to avoid real HTTP calls.
Run with:
    pytest tests/test_scraper.py -v
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.scraper.parsers import (
    _extract_date,
    _extract_monthly_salary,
    _extract_salary_grade,
    extract_pagination_urls,
    extract_text,
    parse_job_detail_page,
    parse_job_listing_page,
)
from src.scraper.session_manager import USER_AGENTS, SessionManager

# ─────────────────────────────────────────────────────────────────────────────
# HTML Fixtures
# ─────────────────────────────────────────────────────────────────────────────

TABLE_LISTING_HTML = """
<html><body>
<table>
  <tr>
    <th>Position</th>
    <th>Agency</th>
    <th>Location</th>
    <th>Deadline</th>
  </tr>
  <tr>
    <td><a href="/jobs/admin-officer-iv">Administrative Officer IV</a></td>
    <td>Provincial Government of Camarines Sur</td>
    <td>Camarines Sur</td>
    <td>June 30, 2026</td>
  </tr>
  <tr>
    <td><a href="/jobs/it-officer-i">Information Technology Officer I</a></td>
    <td>Municipality of Goa</td>
    <td>Goa, Camarines Sur</td>
    <td>July 15, 2026</td>
  </tr>
</table>
</body></html>
"""

CARD_LISTING_HTML = """
<html><body>
<div class="views-row">
  <h3><a href="/jobs/nurse-ii">Nurse II</a></h3>
  <div class="views-field-field-location">Sorsogon City</div>
  <div class="views-field-field-agency">Sorsogon Provincial Hospital</div>
  <div class="views-field-field-deadline">August 1, 2026</div>
</div>
<div class="views-row">
  <h3><a href="/jobs/engineer-i">Engineer I</a></h3>
  <div class="views-field-field-location">Albay</div>
  <div class="views-field-field-agency">DPWH Region V</div>
</div>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <h1 class="page-header">Administrative Officer IV</h1>
  <div class="field--name-field-agency">Provincial Government of Camarines Sur</div>
  <div class="field--name-field-location">Camarines Sur</div>
  <div class="field--name-field-salary-grade">Salary Grade 18 — ₱50,820.00/month</div>
  <div class="field--name-field-eligibility">Career Service Professional (Second Level)</div>
  <div class="field--name-field-deadline">June 30, 2026</div>
</body></html>
"""

PAGINATION_HTML = """
<html><body>
<ul class="pager">
  <li><a href="?page=2">2</a></li>
  <li><a href="?page=3">3</a></li>
  <li><a href="?page=4">4</a></li>
</ul>
</body></html>
"""

EMPTY_HTML = "<html><body><p>No jobs available.</p></body></html>"


# ─────────────────────────────────────────────────────────────────────────────
# SessionManager tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionManagerInit:
    def test_default_values(self):
        sm = SessionManager()
        assert sm.rate_limit == 3.0
        assert sm.timeout == 30
        assert sm.max_retries == 3

    def test_custom_values(self):
        sm = SessionManager(rate_limit=1.0, timeout=10, max_retries=2)
        assert sm.rate_limit == 1.0
        assert sm.timeout == 10
        assert sm.max_retries == 2

    def test_repr(self):
        sm = SessionManager(rate_limit=2.0, timeout=15, max_retries=1)
        assert "2.0" in repr(sm)
        assert "15" in repr(sm)


class TestSessionManagerUserAgent:
    def test_rotate_returns_valid_ua(self):
        sm = SessionManager()
        ua = sm.rotate_user_agent()
        assert ua in USER_AGENTS

    def test_rotate_updates_session_header(self):
        sm = SessionManager()
        ua = sm.rotate_user_agent()
        assert sm._session.headers["User-Agent"] == ua


class TestSessionManagerRateLimit:
    def test_no_wait_on_first_request(self):
        sm = SessionManager(rate_limit=5.0)
        # _last_request_time is 0.0 so elapsed is huge — no wait needed
        start = time.monotonic()
        sm._enforce_rate_limit()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # Should be instant

    def test_waits_between_requests(self):
        sm = SessionManager(rate_limit=0.3)
        sm._last_request_time = time.monotonic()  # Simulate a just-completed request
        start = time.monotonic()
        sm._enforce_rate_limit()
        elapsed = time.monotonic() - start
        # Should wait ~0.3s (with ±20% jitter: 0.24–0.36s)
        assert elapsed >= 0.1  # At least some wait


class TestSessionManagerGet:
    @patch("src.scraper.session_manager.requests.Session.get")
    def test_get_returns_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        sm = SessionManager(rate_limit=0)
        response = sm.get("https://example.com/")
        assert response.status_code == 200

    @patch("src.scraper.session_manager.requests.Session.get")
    def test_get_calls_rotate_user_agent(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_get.return_value = mock_response

        sm = SessionManager(rate_limit=0)
        with patch.object(sm, "rotate_user_agent", wraps=sm.rotate_user_agent) as spy:
            sm.get("https://example.com/")
            spy.assert_called_once()

    @patch("src.scraper.session_manager.requests.Session.get")
    def test_timeout_raises(self, mock_get):
        mock_get.side_effect = requests.Timeout("timed out")
        sm = SessionManager(rate_limit=0)
        with pytest.raises(requests.Timeout):
            sm.get("https://example.com/")

    @patch("src.scraper.session_manager.requests.Session.get")
    def test_connection_error_raises(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("no route")
        sm = SessionManager(rate_limit=0)
        with pytest.raises(requests.ConnectionError):
            sm.get("https://example.com/")

    @patch("src.scraper.session_manager.time.sleep")
    @patch("src.scraper.session_manager.requests.Session.get")
    def test_429_calls_handle_rate_limit(self, mock_get, mock_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.content = b""
        mock_response.headers = {"Retry-After": "5"}
        mock_get.return_value = mock_response

        sm = SessionManager(rate_limit=0)
        with patch.object(sm, "handle_rate_limit") as mock_handle:
            sm.get("https://example.com/")
            mock_handle.assert_called_once_with(mock_response)


class TestSessionManagerHandleRateLimit:
    @patch("src.scraper.session_manager.time.sleep")
    def test_uses_retry_after_header(self, mock_sleep):
        sm = SessionManager()
        response = MagicMock()
        response.headers = {"Retry-After": "30"}
        sm.handle_rate_limit(response)
        mock_sleep.assert_called_once_with(30)

    @patch("src.scraper.session_manager.time.sleep")
    def test_defaults_to_60s_without_header(self, mock_sleep):
        sm = SessionManager()
        sm.handle_rate_limit(None)
        mock_sleep.assert_called_once_with(60)

    @patch("src.scraper.session_manager.time.sleep")
    def test_defaults_to_60s_with_invalid_header(self, mock_sleep):
        sm = SessionManager()
        response = MagicMock()
        response.headers = {"Retry-After": "not-a-number"}
        sm.handle_rate_limit(response)
        mock_sleep.assert_called_once_with(60)


class TestSessionManagerContextManager:
    @patch("src.scraper.session_manager.requests.Session.get")
    def test_context_manager_closes(self, mock_get):
        with SessionManager(rate_limit=0) as sm:
            assert sm._session is not None
        # If no error, close() was called successfully


# ─────────────────────────────────────────────────────────────────────────────
# Parser helper function tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractSalaryGrade:
    def test_salary_grade_prefix(self):
        assert _extract_salary_grade("Salary Grade 18") == "18"

    def test_sg_prefix(self):
        assert _extract_salary_grade("SG-24") == "24"

    def test_case_insensitive(self):
        assert _extract_salary_grade("salary grade 11") == "11"

    def test_no_match_returns_none(self):
        assert _extract_salary_grade("Administrative Officer IV") is None


class TestExtractMonthlySalary:
    def test_peso_sign(self):
        assert _extract_monthly_salary("₱50,820.00") == "₱50,820.00"

    def test_P_prefix(self):
        result = _extract_monthly_salary("P 33,515")
        assert result == "₱33,515"

    def test_no_match_returns_none(self):
        assert _extract_monthly_salary("no salary here") is None


class TestExtractDate:
    def test_full_date(self):
        assert _extract_date("Deadline: June 30, 2026") == "June 30, 2026"

    def test_iso_date(self):
        assert _extract_date("closing 2026-06-30") == "2026-06-30"

    def test_slash_format(self):
        result = _extract_date("until 06/30/2026")
        assert result is not None

    def test_no_date_returns_none(self):
        assert _extract_date("No date here") is None


# ─────────────────────────────────────────────────────────────────────────────
# parse_job_listing_page tests
# ─────────────────────────────────────────────────────────────────────────────

class TestParseJobListingPage:
    def test_parses_table_rows(self):
        jobs = parse_job_listing_page(TABLE_LISTING_HTML)
        assert len(jobs) == 2

    def test_table_job_titles(self):
        jobs = parse_job_listing_page(TABLE_LISTING_HTML)
        titles = [j["position_title"] for j in jobs]
        assert any("Administrative Officer" in t for t in titles)
        assert any("Information Technology" in t for t in titles)

    def test_table_job_urls_extracted(self):
        jobs = parse_job_listing_page(TABLE_LISTING_HTML)
        assert any(j.get("job_url") for j in jobs)

    def test_parses_card_layout(self):
        jobs = parse_job_listing_page(CARD_LISTING_HTML)
        assert len(jobs) == 2

    def test_card_job_location(self):
        jobs = parse_job_listing_page(CARD_LISTING_HTML)
        locations = [j["location"] for j in jobs]
        assert any("Sorsogon" in loc for loc in locations)

    def test_empty_page_returns_empty_list(self):
        jobs = parse_job_listing_page(EMPTY_HTML)
        assert jobs == []


# ─────────────────────────────────────────────────────────────────────────────
# parse_job_detail_page tests
# ─────────────────────────────────────────────────────────────────────────────

class TestParseJobDetailPage:
    def setup_method(self):
        self.result = parse_job_detail_page(
            DETAIL_HTML, base_url="https://csc.gov.ph/jobs/admin-officer-iv"
        )

    def test_position_title_extracted(self):
        assert self.result["position_title"] == "Administrative Officer IV"

    def test_location_extracted(self):
        assert "Camarines Sur" in self.result["location"]

    def test_agency_extracted(self):
        assert "Camarines Sur" in (self.result["agency"] or "")

    def test_salary_grade_extracted(self):
        assert self.result["salary_grade"] == "18"

    def test_monthly_salary_extracted(self):
        assert self.result["monthly_salary"] == "₱50,820.00"

    def test_eligibility_extracted(self):
        assert "Career Service Professional" in (self.result["eligibility_requirements"] or "")

    def test_deadline_extracted(self):
        assert "2026" in (self.result["application_deadline"] or "")

    def test_raw_html_stored(self):
        assert self.result["raw_html"] == DETAIL_HTML

    def test_job_url_echoed(self):
        assert self.result["job_url"] == "https://csc.gov.ph/jobs/admin-officer-iv"


# ─────────────────────────────────────────────────────────────────────────────
# extract_pagination_urls tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractPaginationUrls:
    def test_extracts_paginated_links(self):
        urls = extract_pagination_urls(
            PAGINATION_HTML, "https://www.csc.gov.ph/career-opportunities/"
        )
        assert len(urls) == 3

    def test_urls_are_absolute(self):
        urls = extract_pagination_urls(
            PAGINATION_HTML, "https://www.csc.gov.ph/career-opportunities/"
        )
        assert all(u.startswith("https://") for u in urls)

    def test_empty_page_returns_empty(self):
        urls = extract_pagination_urls(EMPTY_HTML, "https://csc.gov.ph/")
        assert urls == []


# ─────────────────────────────────────────────────────────────────────────────
# extract_text tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractText:
    def test_extracts_text_from_element(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<p>  Hello World  </p>", "lxml")
        el = soup.find("p")
        assert extract_text(el) == "Hello World"

    def test_returns_empty_for_none(self):
        assert extract_text(None) == ""
