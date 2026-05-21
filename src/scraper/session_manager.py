"""
session_manager.py — HTTP session with retry logic and rate limiting.

Features:
  - Exponential backoff with jitter on transient failures (5xx, timeouts)
  - Configurable per-request rate limiting (minimum delay between requests)
  - User-agent rotation to avoid trivial bot detection
  - Timeout and max-retry configuration
  - Structured logging of all requests and errors
"""

import random
import time
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.logger import get_logger

log = get_logger(__name__)

# ── Default user agents ───────────────────────────────────────────────────────

USER_AGENTS = [
    # Chrome on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    # Firefox on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    # Chrome on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    # Edge on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
    ),
]

# ── SessionManager ────────────────────────────────────────────────────────────


class SessionManager:
    """
    Managed HTTP session for the CSC portal scraper.

    Wraps requests.Session with:
      - Automatic retry on transient failures (configurable)
      - Per-request rate limiting (minimum seconds between requests)
      - User-agent rotation on each request
      - Structured request/response logging

    Usage:
        session = SessionManager(rate_limit=3, timeout=30, max_retries=3)
        response = session.get("https://www.csc.gov.ph/career-opportunities/")
    """

    def __init__(
        self,
        rate_limit: float = 3.0,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        """
        Args:
            rate_limit:     Minimum seconds between requests (be a good citizen).
            timeout:        Request timeout in seconds.
            max_retries:    Maximum number of retry attempts on transient errors.
            backoff_factor: Exponential backoff multiplier between retries.
        """
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._last_request_time: float = 0.0
        self._session: requests.Session = self._build_session()

        log.debug(
            "SessionManager initialised — rate_limit={rl}s timeout={t}s retries={r}",
            rl=rate_limit,
            t=timeout,
            r=max_retries,
        )

    # ── Internal setup ────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        """Create a requests.Session with a retry-enabled HTTPAdapter."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            # Retry on these HTTP status codes (server-side transient errors)
            status_forcelist=[429, 500, 502, 503, 504],
            # Retry on these exception types
            allowed_methods=["GET", "HEAD"],
            backoff_factor=self.backoff_factor,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Default headers for all requests
        session.headers.update(
            {
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9,fil;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        return session

    # ── Rate limiting ─────────────────────────────────────────────────────

    def _enforce_rate_limit(self) -> None:
        """
        Block until enough time has passed since the last request.
        Adds ±20 % jitter to avoid predictable request patterns.
        """
        elapsed = time.monotonic() - self._last_request_time
        jitter = random.uniform(-self.rate_limit * 0.2, self.rate_limit * 0.2)
        wait = max(0.0, self.rate_limit + jitter - elapsed)
        if wait > 0:
            log.debug("Rate limiting — waiting {wait:.2f}s", wait=wait)
            time.sleep(wait)

    # ── User-agent rotation ───────────────────────────────────────────────

    def rotate_user_agent(self) -> str:
        """Pick a random user-agent and apply it to the session headers."""
        ua = random.choice(USER_AGENTS)
        self._session.headers["User-Agent"] = ua
        return ua

    # ── Public interface ──────────────────────────────────────────────────

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Perform a rate-limited GET request with automatic user-agent rotation.

        Args:
            url:    The URL to request.
            params: Optional query parameters dict.
            **kwargs: Additional kwargs passed to requests.Session.get().

        Returns:
            requests.Response

        Raises:
            requests.RequestException: On unrecoverable network errors.
        """
        self._enforce_rate_limit()
        self.rotate_user_agent()

        domain = urlparse(url).netloc
        log.debug("GET {domain}{path}", domain=domain, path=urlparse(url).path)

        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )
            self._last_request_time = time.monotonic()

            log.debug(
                "Response {status} — {url} ({size} bytes)",
                status=response.status_code,
                url=url,
                size=len(response.content),
            )

            if response.status_code == 429:
                self.handle_rate_limit(response)

            return response

        except requests.Timeout:
            log.warning("Request timed out after {t}s — {url}", t=self.timeout, url=url)
            raise
        except requests.ConnectionError as exc:
            log.error("Connection error — {url}: {exc}", url=url, exc=exc)
            raise
        except requests.RequestException as exc:
            log.error("Request failed — {url}: {exc}", url=url, exc=exc)
            raise
        finally:
            self._last_request_time = time.monotonic()

    def handle_rate_limit(self, response: Optional[requests.Response] = None) -> None:
        """
        Handle a 429 Too Many Requests response.

        Respects the Retry-After header if present, otherwise backs off
        for a default of 60 seconds.
        """
        wait = 60  # default
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = int(retry_after)
                except ValueError:
                    pass

        log.warning(
            "Rate limited (HTTP 429) — backing off for {wait}s", wait=wait
        )
        time.sleep(wait)

    def close(self) -> None:
        """Close the underlying requests session."""
        self._session.close()
        log.debug("HTTP session closed.")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return (
            f"SessionManager(rate_limit={self.rate_limit}s, "
            f"timeout={self.timeout}s, max_retries={self.max_retries})"
        )
