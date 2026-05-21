# Internal API Documentation

While the CSC Bicol Job Scraper is primarily a CLI application, it is built with a modular architecture that can be imported and used in other Python projects.

## Core Modules

### `src.core.tracker.JobTracker`
The main orchestrator class that glues the scraper, database, filters, and notifiers together.

- `__init__(config_path: str = "config/config.yaml")`: Initializes all components based on the provided configuration.
- `async run_check(force_notify: bool = False)`: Executes a single scraping cycle. Fetches listings, filters them, downloads details for matches, saves to the database, and dispatches notifications.
- `async send_daily_summary()`: Compiles all newly found jobs and sends a summary notification.

### `src.scraper.csc_scraper.CSCScraper`
Responsible for interacting with the CSC portal.

- `__init__(config: dict)`: Configuration can include `base_url`, `max_pages`, etc.
- `fetch_job_listings() -> list[dict]`: Scrapes the main portal and handles pagination. Returns a list of job summaries.
- `parse_job_detail_page(url: str) -> dict`: Downloads and extracts structured metadata from a specific job posting page.

### `src.filters.job_matcher.JobMatcher`
Evaluates job data against the user's criteria.

- `__init__(config: dict)`: Configuration maps to the `filters` section of `config.yaml`.
- `is_match(job_data: dict) -> bool`: Returns `True` if the job satisfies the region, district, eligibility, and salary grade requirements.
- `filter_jobs(jobs: list) -> list`: Filters a list of job dictionaries, returning only matches.

### `src.storage.database.Database`
Handles local SQLite persistence to prevent duplicate notifications.

- `__init__(db_path: str)`: Connects to the SQLite database file.
- `initialize()`: Creates necessary tables if they do not exist.
- `insert_job(job_data: dict) -> bool`: Inserts a job into the database. Returns `False` if it already existed.
- `job_exists(job_hash: str) -> bool`: Checks idempotency using a SHA-256 hash of the job data.

### `src.notifications`
Contains integration clients for various platforms.

- `TelegramNotifier(bot_token: str, chat_id: str)`: Sends individual alerts and daily summaries using the Telegram Bot API.
- `DiscordNotifier(webhook_url: str)`: Sends rich embedded messages using a Discord Webhook.
