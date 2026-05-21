"""
test_database.py — Unit tests for the Database layer (Phase 2).

Uses an in-memory SQLite database so tests are fast and leave no files behind.
Run with:
    pytest tests/test_database.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.storage.database import Database, compute_job_hash
from src.storage.models import Job, NotificationRecord, TrackerStats


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    """Provide a fresh, initialized Database backed by a temp file."""
    db_file = tmp_path / "test_jobs.db"
    database = Database(db_path=str(db_file))
    database.initialize()
    return database


def make_job(
    title: str = "Administrative Officer IV",
    location: str = "Camarines Sur",
    agency: str = "Provincial Government of Camarines Sur",
    url: str = "https://csc.gov.ph/jobs/001",
    salary_grade: str = "18",
) -> Job:
    """Helper: create a Job with a deterministic hash based on URL."""
    job_hash = compute_job_hash(url)
    return Job(
        job_hash=job_hash,
        position_title=title,
        location=location,
        agency=agency,
        salary_grade=salary_grade,
        monthly_salary="₱50,820",
        eligibility_requirements="Career Service Professional",
        application_deadline="2026-06-30",
        job_url=url,
    )


# ── compute_job_hash ───────────────────────────────────────────────────────────

class TestComputeJobHash:
    def test_same_input_same_hash(self):
        h1 = compute_job_hash("https://csc.gov.ph/jobs/001")
        h2 = compute_job_hash("https://csc.gov.ph/jobs/001")
        assert h1 == h2

    def test_different_inputs_different_hashes(self):
        h1 = compute_job_hash("https://csc.gov.ph/jobs/001")
        h2 = compute_job_hash("https://csc.gov.ph/jobs/002")
        assert h1 != h2

    def test_hash_is_hex_string(self):
        h = compute_job_hash("test")
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_64_chars(self):
        h = compute_job_hash("test")
        assert len(h) == 64


# ── Database.initialize ────────────────────────────────────────────────────────

class TestDatabaseInitialize:
    def test_initialize_creates_tables(self, db):
        # Should not raise; tables already created by fixture
        stats = db.get_statistics()
        assert stats.total_jobs == 0

    def test_initialize_is_idempotent(self, db):
        db.initialize()  # Second call — should not raise or duplicate
        assert db.count_jobs() == 0

    def test_drop_all_tables(self, db):
        job = make_job()
        db.insert_job(job)
        db.drop_all_tables()
        db.initialize()  # Re-create
        assert db.count_jobs() == 0


# ── Database.insert_job ────────────────────────────────────────────────────────

class TestInsertJob:
    def test_insert_returns_true_for_new_job(self, db):
        job = make_job()
        result = db.insert_job(job)
        assert result is True

    def test_insert_returns_false_for_duplicate(self, db):
        job = make_job()
        db.insert_job(job)
        result = db.insert_job(job)
        assert result is False

    def test_count_after_insert(self, db):
        db.insert_job(make_job(url="https://csc.gov.ph/jobs/001"))
        db.insert_job(make_job(url="https://csc.gov.ph/jobs/002"))
        assert db.count_jobs() == 2

    def test_duplicate_does_not_increase_count(self, db):
        job = make_job()
        db.insert_job(job)
        db.insert_job(job)
        assert db.count_jobs() == 1

    def test_insert_updates_last_checked_on_duplicate(self, db):
        job = make_job()
        db.insert_job(job)
        original = db.get_job(job.job_hash)
        db.insert_job(job)  # second insert
        updated = db.get_job(job.job_hash)
        assert updated is not None
        # last_checked_at should have advanced
        assert updated.last_checked_at >= original.last_checked_at


# ── Database.job_exists ────────────────────────────────────────────────────────

class TestJobExists:
    def test_returns_false_when_not_present(self, db):
        assert db.job_exists("nonexistent_hash") is False

    def test_returns_true_after_insert(self, db):
        job = make_job()
        db.insert_job(job)
        assert db.job_exists(job.job_hash) is True


# ── Database.get_job ───────────────────────────────────────────────────────────

class TestGetJob:
    def test_returns_none_for_missing(self, db):
        assert db.get_job("missing") is None

    def test_returns_job_after_insert(self, db):
        job = make_job()
        db.insert_job(job)
        fetched = db.get_job(job.job_hash)
        assert fetched is not None
        assert fetched.position_title == job.position_title
        assert fetched.location == job.location
        assert fetched.salary_grade == job.salary_grade


# ── Database.get_all_jobs ──────────────────────────────────────────────────────

class TestGetAllJobs:
    def test_returns_empty_list_when_no_jobs(self, db):
        assert db.get_all_jobs() == []

    def test_returns_all_inserted_jobs(self, db):
        for i in range(3):
            db.insert_job(make_job(url=f"https://csc.gov.ph/jobs/{i}"))
        jobs = db.get_all_jobs()
        assert len(jobs) == 3

    def test_respects_limit(self, db):
        for i in range(5):
            db.insert_job(make_job(url=f"https://csc.gov.ph/jobs/{i}"))
        jobs = db.get_all_jobs(limit=2)
        assert len(jobs) == 2


# ── Database.get_unnotified_jobs ───────────────────────────────────────────────

class TestGetUnnotifiedJobs:
    def test_new_job_is_unnotified(self, db):
        job = make_job()
        db.insert_job(job)
        unnotified = db.get_unnotified_jobs()
        assert any(j.job_hash == job.job_hash for j in unnotified)

    def test_notified_job_not_in_list(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "telegram", success=True)
        unnotified = db.get_unnotified_jobs()
        assert all(j.job_hash != job.job_hash for j in unnotified)

    def test_failed_notification_stays_unnotified(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "telegram", success=False, error_message="timeout")
        unnotified = db.get_unnotified_jobs()
        assert any(j.job_hash == job.job_hash for j in unnotified)


# ── Database.mark_as_notified ──────────────────────────────────────────────────

class TestMarkAsNotified:
    def test_success_record_stored(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "telegram", success=True)
        history = db.get_notification_history(job.job_hash)
        assert len(history) == 1
        assert history[0].success is True
        assert history[0].notification_channel == "telegram"

    def test_failure_record_stores_error(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "discord", success=False, error_message="404")
        history = db.get_notification_history(job.job_hash)
        assert history[0].success is False
        assert history[0].error_message == "404"

    def test_multiple_records_for_same_job(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "telegram", success=False)
        db.mark_as_notified(job.job_hash, "telegram", success=True)
        history = db.get_notification_history(job.job_hash)
        assert len(history) == 2


# ── Database config store ──────────────────────────────────────────────────────

class TestConfigStore:
    def test_set_and_get(self, db):
        db.set_config("last_run", "2026-01-01T00:00:00")
        assert db.get_config("last_run") == "2026-01-01T00:00:00"

    def test_get_missing_returns_default(self, db):
        assert db.get_config("nonexistent", default="fallback") == "fallback"

    def test_update_existing_key(self, db):
        db.set_config("key", "value1")
        db.set_config("key", "value2")
        assert db.get_config("key") == "value2"


# ── Database.get_statistics ────────────────────────────────────────────────────

class TestGetStatistics:
    def test_empty_db_stats(self, db):
        stats = db.get_statistics()
        assert stats.total_jobs == 0
        assert stats.total_notifications_sent == 0
        assert stats.success_rate == 100.0

    def test_stats_counts_jobs(self, db):
        db.insert_job(make_job(url="https://csc.gov.ph/jobs/001"))
        db.insert_job(make_job(url="https://csc.gov.ph/jobs/002"))
        stats = db.get_statistics()
        assert stats.total_jobs == 2

    def test_stats_counts_notifications(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "telegram", success=True)
        db.mark_as_notified(job.job_hash, "discord", success=False)
        stats = db.get_statistics()
        assert stats.total_notifications_sent == 2
        assert stats.successful_notifications == 1
        assert stats.failed_notifications == 1

    def test_success_rate_calculation(self, db):
        job = make_job()
        db.insert_job(job)
        db.mark_as_notified(job.job_hash, "telegram", success=True)
        db.mark_as_notified(job.job_hash, "telegram", success=True)
        db.mark_as_notified(job.job_hash, "telegram", success=False)
        stats = db.get_statistics()
        assert stats.success_rate == pytest.approx(66.7, rel=0.01)


# ── Models ────────────────────────────────────────────────────────────────────

class TestJobModel:
    def test_to_dict_and_from_dict_roundtrip(self):
        job = make_job()
        restored = Job.from_dict(job.to_dict())
        assert restored.job_hash == job.job_hash
        assert restored.position_title == job.position_title
        assert restored.location == job.location

    def test_str_representation(self):
        job = make_job()
        s = str(job)
        assert "Administrative Officer IV" in s
        assert "Camarines Sur" in s


class TestNotificationRecordModel:
    def test_to_dict_and_from_dict_roundtrip(self):
        record = NotificationRecord(
            job_hash="abc123",
            notification_channel="telegram",
            success=True,
        )
        restored = NotificationRecord.from_dict(record.to_dict())
        assert restored.job_hash == "abc123"
        assert restored.success is True


class TestTrackerStats:
    def test_success_rate_100_when_no_notifications(self):
        stats = TrackerStats()
        assert stats.success_rate == 100.0

    def test_success_rate_50_percent(self):
        stats = TrackerStats(
            total_notifications_sent=4,
            successful_notifications=2,
            failed_notifications=2,
        )
        assert stats.success_rate == 50.0
