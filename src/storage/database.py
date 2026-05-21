"""
database.py — SQLite operations wrapper.

Implemented in Phase 2: Database Layer.
"""


class Database:
    """SQLite operations wrapper for job tracking storage."""

    def __init__(self, db_path: str):
        raise NotImplementedError("Implemented in Phase 2.")

    def insert_job(self, job_data: dict) -> bool:
        raise NotImplementedError("Implemented in Phase 2.")

    def job_exists(self, job_hash: str) -> bool:
        raise NotImplementedError("Implemented in Phase 2.")

    def get_unnotified_jobs(self) -> list:
        raise NotImplementedError("Implemented in Phase 2.")

    def mark_as_notified(self, job_hash: str, channel: str, success: bool):
        raise NotImplementedError("Implemented in Phase 2.")

    def get_statistics(self) -> dict:
        raise NotImplementedError("Implemented in Phase 2.")
