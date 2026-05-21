"""
test_integration.py — End-to-End integration tests for Phase 12.

Run with:
    pytest tests/test_integration.py -v
"""

import os
import pytest
import responses
from pathlib import Path
from unittest.mock import patch

from src.core.tracker import JobTracker

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def load_fixture(filename: str) -> str:
    with open(FIXTURE_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture
def mock_csc_server():
    """Mock the CSC portal server using responses."""
    with responses.RequestsMock() as rsps:
        # 1. Main listings page
        rsps.add(
            responses.GET,
            "https://www.csc.gov.ph/career-opportunities/",
            body=load_fixture("sample_listing.html"),
            status=200,
            content_type="text/html"
        )
        
        # We need another mock for pagination discovery (the scraper fetches the page again to find pagination)
        # Actually it's handled by responses if we don't use match_querystring=True, it will match again
        
        # 2. Detail page for Administrative Officer IV
        rsps.add(
            responses.GET,
            "https://csc.gov.ph/career/job/12345",
            body=load_fixture("sample_detail.html"),
            status=200,
            content_type="text/html"
        )
        
        # 3. Detail page for Computer Programmer II (we'll just use the same detail mock for simplicity, or 404 it if not needed)
        # Actually, let's just let it return the same detail page for both since we just want to test the flow
        rsps.add(
            responses.GET,
            "https://csc.gov.ph/career/job/67890",
            body=load_fixture("sample_detail.html"),
            status=200,
            content_type="text/html"
        )
        
        yield rsps

@pytest.mark.asyncio
@patch('src.core.tracker.Database')
@patch('src.core.tracker.load_config')
async def test_end_to_end_scraping_flow(mock_load_config, mock_db, mock_csc_server):
    """
    Test the entire application loop:
    - Scraper fetches listings
    - Matcher filters them
    - Database stores them
    - Notifiers are triggered
    """
    # Mock configuration to enable scraping, matching, and notifications
    mock_load_config.return_value = {
        "scraper": {"max_pages": 1},
        "filters": {
            "provinces": ["Albay", "Camarines Sur"],
            "eligibilities": ["Career Service Professional"],
            "salary_grade_min": 10
        },
        "notifications": {
            "telegram": {"enabled": False}, # We'll mock dispatch instead of actual network calls
            "discord": {"enabled": False}
        }
    }
    
    # Setup mock DB instance
    mock_db_instance = mock_db.return_value
    mock_db_instance.job_exists.return_value = False # New job
    mock_db_instance.insert_job.return_value = True  # Successful insertion
    
    # Initialize Tracker
    tracker = JobTracker()
    
    # Mock dispatch so we can verify if it decided to send alerts
    with patch.object(tracker, '_dispatch_notifications') as mock_dispatch:
        # Run the check cycle
        await tracker.run_check()
        
        # Verify the database was queried to check for existence
        assert mock_db_instance.job_exists.called
        
        # Verify that a job was inserted
        assert mock_db_instance.insert_job.called
        
        # Verify that dispatch was called with the new matches
        assert mock_dispatch.called
        
        # Get the job dict passed to dispatch
        dispatched_jobs = mock_dispatch.call_args[0][0]
        assert len(dispatched_jobs) > 0
        
        # Check that the parsed data matches our fixture
        matched_job = dispatched_jobs[0]
        assert matched_job["position_title"] == "Administrative Officer IV"
        assert "Albay" in matched_job["location"]
        assert matched_job["salary_grade"] == "15"
