"""
test_tracker.py — Unit tests for Phase 9: Core Application Loop.

Run with:
    pytest tests/test_tracker.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.tracker import JobTracker


class TestJobTracker:

    @patch('src.core.tracker.Database')
    @patch('src.core.tracker.load_config')
    def test_init_without_notifiers(self, mock_load_config, mock_db):
        mock_load_config.return_value = {
            "scraper": {},
            "filters": {},
            "notifications": {
                "telegram": {"enabled": False},
                "discord": {"enabled": False}
            }
        }
        tracker = JobTracker()
        assert len(tracker.notifiers) == 0
        mock_db.assert_called_once()
        mock_db.return_value.initialize.assert_called_once()

    @patch('src.core.tracker.Database')
    @patch('src.core.tracker.load_config')
    @patch('os.getenv')
    def test_init_with_notifiers_missing_env(self, mock_getenv, mock_load_config, mock_db):
        mock_load_config.return_value = {
            "notifications": {
                "telegram": {"enabled": True},
                "discord": {"enabled": True}
            }
        }
        mock_getenv.return_value = None
        tracker = JobTracker()
        # Should be empty because env vars are missing
        assert len(tracker.notifiers) == 0

    @pytest.mark.asyncio
    @patch('src.core.tracker.Database')
    @patch('src.core.tracker.load_config')
    @patch('src.core.tracker.CSCScraper')
    @patch('src.core.tracker.JobMatcher')
    async def test_run_check_no_jobs(self, mock_matcher, mock_scraper, mock_load_config, mock_db):
        mock_load_config.return_value = {}

        # Setup scraper mock to return empty list
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.__enter__.return_value = mock_scraper_instance
        mock_scraper_instance.fetch_job_listings.return_value = []
        mock_scraper.return_value = mock_scraper_instance

        tracker = JobTracker()
        await tracker.run_check()

        mock_scraper_instance.fetch_job_listings.assert_called_once()
        mock_matcher.return_value.filter_jobs.assert_not_called()

    @pytest.mark.asyncio
    @patch('src.core.tracker.Database')
    @patch('src.core.tracker.load_config')
    @patch('src.core.tracker.CSCScraper')
    @patch('src.core.tracker.JobMatcher')
    async def test_run_check_with_jobs(self, mock_matcher, mock_scraper, mock_load_config, mock_db):
        mock_load_config.return_value = {}

        # Setup mocks
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.__enter__.return_value = mock_scraper_instance
        mock_scraper_instance.fetch_job_listings.return_value = [{"job_hash": "hash1", "job_url": "url1"}]
        mock_scraper_instance.parse_job_detail_page.return_value = {"position_title": "Dev"}
        mock_scraper.return_value = mock_scraper_instance

        mock_matcher_instance = MagicMock()
        mock_matcher_instance.filter_jobs.return_value = [{"job_hash": "hash1", "job_url": "url1"}]
        mock_matcher_instance.is_match.return_value = True
        mock_matcher.return_value = mock_matcher_instance

        mock_db_instance = MagicMock()
        mock_db_instance.job_exists.return_value = False
        mock_db_instance.insert_job.return_value = True
        mock_db.return_value = mock_db_instance

        tracker = JobTracker()
        tracker._dispatch_notifications = AsyncMock()

        await tracker.run_check()

        mock_scraper_instance.parse_job_detail_page.assert_called_once_with("url1")
        mock_db_instance.insert_job.assert_called_once()
        tracker._dispatch_notifications.assert_called_once()
