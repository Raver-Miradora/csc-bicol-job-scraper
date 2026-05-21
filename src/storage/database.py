"""
database.py — SQLite operations wrapper for the CSC Job Tracker.

Handles all database interactions:
  - Schema creation and migration
  - Job insertion and deduplication
  - Notification history tracking
  - Statistics aggregation
  - Runtime config key/value store
"""

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional


# Timezone-aware UTC helper (replaces deprecated datetime.utcnow())
def _now() -> datetime:
    return datetime.now(timezone.utc)

from src.storage.models import Job, NotificationRecord, TrackerStats

# ── Schema DDL ────────────────────────────────────────────────────────────────

SCHEMA_VERSION = 1

CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash                TEXT    UNIQUE NOT NULL,
    position_title          TEXT    NOT NULL,
    salary_grade            TEXT,
    monthly_salary          TEXT,
    location                TEXT    NOT NULL,
    agency                  TEXT,
    eligibility_requirements TEXT,
    application_deadline    TEXT,
    job_url                 TEXT,
    raw_html                TEXT,
    first_seen_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_NOTIFICATION_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS notification_history (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash             TEXT    NOT NULL,
    notification_channel TEXT,
    sent_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success              BOOLEAN,
    error_message        TEXT,
    FOREIGN KEY (job_hash) REFERENCES jobs(job_hash)
);
"""

CREATE_CONFIG_TABLE = """
CREATE TABLE IF NOT EXISTS config (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);",
    "CREATE INDEX IF NOT EXISTS idx_notif_job_hash  ON notification_history(job_hash);",
    "CREATE INDEX IF NOT EXISTS idx_notif_sent_at   ON notification_history(sent_at);",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_job_hash(unique_identifier: str) -> str:
    """Return the SHA-256 hex digest of a unique job identifier string."""
    return hashlib.sha256(unique_identifier.encode("utf-8")).hexdigest()


# ── Database class ────────────────────────────────────────────────────────────

class Database:
    """
    SQLite operations wrapper for the CSC Job Tracker.

    Usage:
        db = Database("data/jobs.db")
        db.initialize()        # create tables / run migrations
        db.insert_job(job)
        jobs = db.get_unnotified_jobs()
        db.mark_as_notified(job_hash, "telegram", success=True)
        stats = db.get_statistics()
    """

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Context manager ────────────────────────────────────────────────────

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a thread-safe SQLite connection with row factory set."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            # Note: PARSE_DECLTYPES removed — its built-in timestamp converter
            # is deprecated in Python 3.12+ and breaks ISO-8601 'T' format.
            # We parse timestamps explicitly in _row_to_job() / _row_to_record().
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")   # Better concurrency
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Schema management ──────────────────────────────────────────────────

    def initialize(self) -> None:
        """Create all tables and indexes. Safe to call multiple times."""
        with self._connect() as conn:
            conn.execute(CREATE_SCHEMA_VERSION_TABLE)
            conn.execute(CREATE_JOBS_TABLE)
            conn.execute(CREATE_NOTIFICATION_HISTORY_TABLE)
            conn.execute(CREATE_CONFIG_TABLE)
            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)
            self._apply_migrations(conn)

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        """Apply any pending schema migrations."""
        row = conn.execute(
            "SELECT MAX(version) AS ver FROM schema_version"
        ).fetchone()
        current_version = row["ver"] if row["ver"] is not None else 0

        if current_version < SCHEMA_VERSION:
            # Future migrations go here:
            # if current_version < 2: conn.execute(MIGRATION_V2)
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )

    def drop_all_tables(self) -> None:
        """Drop all tables — intended for tests only."""
        with self._connect() as conn:
            for table in [
                "notification_history",
                "jobs",
                "config",
                "schema_version",
            ]:
                conn.execute(f"DROP TABLE IF EXISTS {table}")

    # ── Job operations ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_dt(value) -> datetime:
        """Parse an ISO-8601 string (with 'T' or ' ' separator) to datetime."""
        if isinstance(value, datetime):
            return value
        if value is None:
            return _now()
        return datetime.fromisoformat(str(value))

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        """Convert a DB row to a Job dataclass."""
        d = dict(row)
        d["first_seen_at"]   = Database._parse_dt(d.get("first_seen_at"))
        d["last_checked_at"] = Database._parse_dt(d.get("last_checked_at"))
        return Job.from_dict(d)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> NotificationRecord:
        """Convert a DB row to a NotificationRecord dataclass."""
        d = dict(row)
        d["sent_at"] = Database._parse_dt(d.get("sent_at"))
        return NotificationRecord.from_dict(d)

    def insert_job(self, job: Job) -> bool:
        """
        Insert a new job into the database.

        Returns True if inserted, False if it already exists (idempotent).
        Also updates last_checked_at if the job is seen again.
        """
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE job_hash = ?", (job.job_hash,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE jobs SET last_checked_at = ? WHERE job_hash = ?",
                    (_now().isoformat(), job.job_hash),
                )
                return False  # Already known

            conn.execute(
                """
                INSERT INTO jobs (
                    job_hash, position_title, salary_grade, monthly_salary,
                    location, agency, eligibility_requirements,
                    application_deadline, job_url, raw_html,
                    first_seen_at, last_checked_at
                ) VALUES (
                    :job_hash, :position_title, :salary_grade, :monthly_salary,
                    :location, :agency, :eligibility_requirements,
                    :application_deadline, :job_url, :raw_html,
                    :first_seen_at, :last_checked_at
                )
                """,
                job.to_dict(),
            )
            return True  # Newly inserted

    def job_exists(self, job_hash: str) -> bool:
        """Return True if a job with the given hash is already in the DB."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM jobs WHERE job_hash = ?", (job_hash,)
            ).fetchone()
            return row is not None

    def get_job(self, job_hash: str) -> Optional[Job]:
        """Fetch a single job by its hash. Returns None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_hash = ?", (job_hash,)
            ).fetchone()
            return self._row_to_job(row) if row else None

    def get_all_jobs(self, limit: int = 100, offset: int = 0) -> List[Job]:
        """Return all jobs ordered by first_seen_at descending."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY first_seen_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._row_to_job(r) for r in rows]

    # ── Notification operations ────────────────────────────────────────────

    def get_unnotified_jobs(self) -> List[Job]:
        """
        Return jobs that have never had a successful notification sent.

        A job is considered 'notified' if there is at least one
        notification_history row for it with success=1.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT j.* FROM jobs j
                WHERE NOT EXISTS (
                    SELECT 1 FROM notification_history n
                    WHERE n.job_hash = j.job_hash AND n.success = 1
                )
                ORDER BY j.first_seen_at ASC
                """
            ).fetchall()
            return [self._row_to_job(r) for r in rows]

    def mark_as_notified(
        self,
        job_hash: str,
        channel: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a notification attempt in notification_history."""
        record = NotificationRecord(
            job_hash=job_hash,
            notification_channel=channel,
            success=success,
            sent_at=_now(),
            error_message=error_message,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notification_history (
                    job_hash, notification_channel, sent_at, success, error_message
                ) VALUES (
                    :job_hash, :notification_channel, :sent_at, :success, :error_message
                )
                """,
                record.to_dict(),
            )

    def get_notification_history(self, job_hash: str) -> List[NotificationRecord]:
        """Return all notification attempts for a given job hash."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notification_history WHERE job_hash = ? ORDER BY sent_at DESC",
                (job_hash,),
            ).fetchall()
            return [self._row_to_record(r) for r in rows]

    # ── Config key/value store ─────────────────────────────────────────────

    def set_config(self, key: str, value: str) -> None:
        """Upsert a runtime configuration value."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                               updated_at=excluded.updated_at
                """,
                (key, value, _now().isoformat()),
            )

    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a runtime configuration value."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM config WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_statistics(self) -> TrackerStats:
        """Return aggregated tracker statistics."""
        today = date.today().isoformat()

        with self._connect() as conn:
            total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

            new_today = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE DATE(first_seen_at) = ?", (today,)
            ).fetchone()[0]

            total_notif = conn.execute(
                "SELECT COUNT(*) FROM notification_history"
            ).fetchone()[0]

            success_notif = conn.execute(
                "SELECT COUNT(*) FROM notification_history WHERE success = 1"
            ).fetchone()[0]

            failed_notif = conn.execute(
                "SELECT COUNT(*) FROM notification_history WHERE success = 0"
            ).fetchone()[0]

            last_check_row = conn.execute(
                "SELECT MAX(last_checked_at) AS ts FROM jobs"
            ).fetchone()
            last_check = (
                datetime.fromisoformat(last_check_row["ts"])
                if last_check_row["ts"]
                else None
            )

        return TrackerStats(
            total_jobs=total_jobs,
            new_jobs_today=new_today,
            total_notifications_sent=total_notif,
            successful_notifications=success_notif,
            failed_notifications=failed_notif,
            last_check_at=last_check,
        )

    # ── Maintenance ────────────────────────────────────────────────────────

    def vacuum(self) -> None:
        """Run VACUUM to reclaim unused disk space."""
        with self._connect() as conn:
            conn.execute("VACUUM")

    def count_jobs(self) -> int:
        """Return the total number of tracked jobs."""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def __repr__(self) -> str:
        return f"Database(path={self.db_path!r})"
