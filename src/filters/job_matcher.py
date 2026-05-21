"""
job_matcher.py — Combined filtering logic (region + eligibility).

Implemented in Phase 5: Filtering Logic.
"""


class JobMatcher:
    """Combines region and eligibility filters to find matching job postings."""

    def __init__(self, config: dict):
        raise NotImplementedError("Implemented in Phase 5.")

    def is_match(self, job_data: dict) -> bool:
        """Return True if the job passes all configured filters."""
        raise NotImplementedError("Implemented in Phase 5.")

    def filter_jobs(self, jobs: list) -> list:
        """Filter a list of jobs and return only matching ones."""
        raise NotImplementedError("Implemented in Phase 5.")
