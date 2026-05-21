"""
job_matcher.py — Combined filtering logic (region + eligibility).

Implemented in Phase 5: Filtering Logic.
"""

from src.filters.region_filter import RegionFilter
from src.filters.eligibility_filter import EligibilityFilter
from src.utils.logger import get_logger

log = get_logger(__name__)

class JobMatcher:
    """Combines region and eligibility filters to find matching job postings."""

    def __init__(self, config: dict):
        """
        Initialize JobMatcher with optional configuration.
        config may contain:
            'salary_grade_min': int (default 0)
            'require_bicol_region': bool (default True)
            'require_partido_district': bool (default False)
            'require_cs_professional': bool (default True)
        """
        self.config = config or {}
        self.region_filter = RegionFilter()
        self.eligibility_filter = EligibilityFilter()
        
        self.min_sg = int(self.config.get("salary_grade_min", 0))
        self.require_bicol = self.config.get("require_bicol_region", True)
        self.require_partido = self.config.get("require_partido_district", False)
        self.require_cs_prof = self.config.get("require_cs_professional", True)

    def is_match(self, job_data: dict) -> bool:
        """Return True if the job passes all configured filters."""
        title = job_data.get("position_title", "Unknown")
        location = job_data.get("location", "")
        eligibility = job_data.get("eligibility_requirements", "")
        salary_grade_str = job_data.get("salary_grade", "")
        
        # 1. Salary Grade Check
        if self.min_sg > 0:
            sg = self.eligibility_filter.parse_salary_grade(salary_grade_str)
            if sg < self.min_sg:
                log.debug(f"Filtered out '{title}': SG {sg} < min {self.min_sg}")
                return False

        # 2. Region Check
        if self.require_bicol:
            if not self.region_filter.is_bicol_region(location):
                log.debug(f"Filtered out '{title}': Location '{location}' not in Bicol")
                return False

        # 3. Partido District Check (Stricter than Bicol)
        if self.require_partido:
            if not self.region_filter.is_partido_district(location):
                log.debug(f"Filtered out '{title}': Location '{location}' not in Partido")
                return False

        # 4. Eligibility Check
        if self.require_cs_prof:
            if not self.eligibility_filter.matches_cs_professional(eligibility):
                log.debug(f"Filtered out '{title}': Eligibility '{eligibility}' not CS Professional")
                return False

        log.info(f"Job Match Found: '{title}' at '{location}'")
        return True

    def filter_jobs(self, jobs: list) -> list:
        """Filter a list of jobs and return only matching ones."""
        matching_jobs = []
        for job in jobs:
            if self.is_match(job):
                matching_jobs.append(job)
        return matching_jobs
