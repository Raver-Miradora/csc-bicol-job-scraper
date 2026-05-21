"""
models.py — Data models and schema definitions for job storage.

These dataclasses mirror the SQLite schema and are used throughout
the application to pass structured data between modules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _now() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class Job:
    """
    Represents a single CSC job posting.

    job_hash is a SHA-256 hex digest computed from a stable unique
    identifier (e.g., job URL or position+agency+deadline composite)
    to guarantee idempotency across scraping runs.
    """

    job_hash: str                           # SHA-256 of unique job identifier
    position_title: str
    location: str
    salary_grade: Optional[str] = None
    monthly_salary: Optional[str] = None
    agency: Optional[str] = None
    eligibility_requirements: Optional[str] = None
    application_deadline: Optional[str] = None
    job_url: Optional[str] = None
    raw_html: Optional[str] = None          # Stored for debugging/re-parsing
    first_seen_at: datetime = field(default_factory=_now)
    last_checked_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict:
        """Serialize the Job to a plain dictionary (for DB insertion)."""
        return {
            "job_hash": self.job_hash,
            "position_title": self.position_title,
            "location": self.location,
            "salary_grade": self.salary_grade,
            "monthly_salary": self.monthly_salary,
            "agency": self.agency,
            "eligibility_requirements": self.eligibility_requirements,
            "application_deadline": self.application_deadline,
            "job_url": self.job_url,
            "raw_html": self.raw_html,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_checked_at": self.last_checked_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Deserialize a Job from a plain dictionary (e.g., a DB row)."""
        return cls(
            job_hash=data["job_hash"],
            position_title=data["position_title"],
            location=data["location"],
            salary_grade=data.get("salary_grade"),
            monthly_salary=data.get("monthly_salary"),
            agency=data.get("agency"),
            eligibility_requirements=data.get("eligibility_requirements"),
            application_deadline=data.get("application_deadline"),
            job_url=data.get("job_url"),
            raw_html=data.get("raw_html"),
            first_seen_at=datetime.fromisoformat(data["first_seen_at"])
            if isinstance(data.get("first_seen_at"), str)
            else data.get("first_seen_at", _now()),
            last_checked_at=datetime.fromisoformat(data["last_checked_at"])
            if isinstance(data.get("last_checked_at"), str)
            else data.get("last_checked_at", _now()),
        )

    def __str__(self) -> str:
        return (
            f"Job({self.position_title!r} | {self.agency!r} | "
            f"SG {self.salary_grade} | {self.location!r})"
        )


@dataclass
class NotificationRecord:
    """
    Represents a single notification delivery attempt.

    Stored in notification_history to prevent duplicate alerts and
    provide a complete audit trail of what was sent and when.
    """

    job_hash: str
    notification_channel: str               # 'telegram' or 'discord'
    success: bool
    sent_at: datetime = field(default_factory=_now)
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize the record to a plain dictionary."""
        return {
            "job_hash": self.job_hash,
            "notification_channel": self.notification_channel,
            "success": self.success,
            "sent_at": self.sent_at.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationRecord":
        """Deserialize a record from a plain dictionary."""
        return cls(
            job_hash=data["job_hash"],
            notification_channel=data["notification_channel"],
            success=bool(data["success"]),
            sent_at=datetime.fromisoformat(data["sent_at"])
            if isinstance(data.get("sent_at"), str)
            else data.get("sent_at", _now()),
            error_message=data.get("error_message"),
        )


@dataclass
class TrackerStats:
    """Aggregated statistics returned by Database.get_statistics()."""

    total_jobs: int = 0
    new_jobs_today: int = 0
    total_notifications_sent: int = 0
    successful_notifications: int = 0
    failed_notifications: int = 0
    last_check_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Notification success rate as a percentage (0–100)."""
        if self.total_notifications_sent == 0:
            return 100.0
        return round(
            (self.successful_notifications / self.total_notifications_sent) * 100, 1
        )
