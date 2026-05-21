"""
models.py — Data models and schema definitions for job storage.

Implemented in Phase 2: Database Layer.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    """Represents a single CSC job posting."""

    job_hash: str               # SHA-256 of unique job identifier
    position_title: str
    location: str
    salary_grade: Optional[str] = None
    monthly_salary: Optional[str] = None
    agency: Optional[str] = None
    eligibility_requirements: Optional[str] = None
    application_deadline: Optional[str] = None
    job_url: Optional[str] = None
    raw_html: Optional[str] = None
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_checked_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationRecord:
    """Represents a notification delivery record."""

    job_hash: str
    notification_channel: str   # 'telegram' or 'discord'
    success: bool
    sent_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
