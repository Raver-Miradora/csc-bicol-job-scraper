# Test Documentation

## Overview
This repository uses `pytest` for all unit and integration testing. We use `pytest-cov` for code coverage reporting and `responses` to mock out external CSC portal network calls.

## Running Tests
To run the full test suite with coverage reporting:

```bash
pytest tests/ -v
```

This will output the test results and a terminal-based code coverage report. An HTML report will also be generated in `htmlcov/index.html`.

## Test Structure
- `test_filters.py`: Tests the Region and Eligibility filtering logic.
- `test_scraper.py`: Tests parsing logic and the session manager.
- `test_database.py`: Tests SQLite storage, initialization, and statistics retrieval.
- `test_notifications.py`: Tests Discord and Telegram formatters and API clients.
- `test_tracker.py`: Tests the core orchestration loop without network calls.
- `test_integration.py`: End-to-end integration tests using `responses` and sample HTML fixtures.

## Fixtures
Sample HTML from the CSC portal is stored in `tests/fixtures/`.
- `sample_listing.html`: Represents the portal's main job listing page.
- `sample_detail.html`: Represents an individual job's detailed metadata page.
