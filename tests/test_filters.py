"""
test_filters.py — Unit tests for Phase 5: Filtering Logic.

Run with:
    pytest tests/test_filters.py -v
"""

import pytest
from src.filters.region_filter import RegionFilter
from src.filters.eligibility_filter import EligibilityFilter
from src.filters.job_matcher import JobMatcher

class TestRegionFilter:
    def setup_method(self):
        self.rf = RegionFilter()

    def test_normalize_location(self):
        assert self.rf.normalize_location("Camarines Sur") == "camarines sur"
        assert self.rf.normalize_location("Sagñay") == "sagnay"
        assert self.rf.normalize_location(" GOA, CAM. SUR ") == "goa cam sur"
        assert self.rf.normalize_location("") == ""
        assert self.rf.normalize_location(None) == ""

    def test_is_bicol_region(self):
        assert self.rf.is_bicol_region("Camarines Sur") is True
        assert self.rf.is_bicol_region("Sorsogon City") is True
        assert self.rf.is_bicol_region("Legazpi, Albay") is True
        assert self.rf.is_bicol_region("Metro Manila") is False
        assert self.rf.is_bicol_region("Cebu") is False
        assert self.rf.is_bicol_region("") is False

    def test_is_partido_district(self):
        assert self.rf.is_partido_district("Tigaon, Camarines Sur") is True
        assert self.rf.is_partido_district("Goa") is True
        assert self.rf.is_partido_district("Naga City") is False
        assert self.rf.is_partido_district("Legazpi") is False


class TestEligibilityFilter:
    def setup_method(self):
        self.ef = EligibilityFilter()

    def test_matches_cs_professional(self):
        assert self.ef.matches_cs_professional("Career Service Professional") is True
        assert self.ef.matches_cs_professional("CS Professional") is True
        assert self.ef.matches_cs_professional("RA 1080") is True
        assert self.ef.matches_cs_professional("R.A. 1080 (Teacher)") is True
        assert self.ef.matches_cs_professional("Professional Eligibility") is True
        assert self.ef.matches_cs_professional("Career Service Sub-Professional") is False
        assert self.ef.matches_cs_professional("Sub Professional") is False
        assert self.ef.matches_cs_professional("None") is False
        assert self.ef.matches_cs_professional("") is False
        assert self.ef.matches_cs_professional(None) is False

    def test_parse_salary_grade(self):
        assert self.ef.parse_salary_grade("Salary Grade 18") == 18
        assert self.ef.parse_salary_grade("SG 12") == 12
        assert self.ef.parse_salary_grade("SG-15") == 15
        assert self.ef.parse_salary_grade("11") == 11
        assert self.ef.parse_salary_grade("Not Applicable") == 0
        assert self.ef.parse_salary_grade("") == 0
        assert self.ef.parse_salary_grade(None) == 0


class TestJobMatcher:
    def setup_method(self):
        # Default config
        self.jm = JobMatcher({
            "salary_grade_min": 10,
            "require_bicol_region": True,
            "require_partido_district": False,
            "require_cs_prof": True
        })

    def test_is_match_perfect(self):
        job = {
            "position_title": "Admin Officer",
            "location": "Camarines Sur",
            "eligibility_requirements": "CS Professional",
            "salary_grade": "18"
        }
        assert self.jm.is_match(job) is True

    def test_is_match_fails_sg(self):
        job = {
            "position_title": "Clerk",
            "location": "Camarines Sur",
            "eligibility_requirements": "CS Professional",
            "salary_grade": "8" # < 10
        }
        assert self.jm.is_match(job) is False

    def test_is_match_fails_region(self):
        job = {
            "position_title": "Admin Officer",
            "location": "Makati City",
            "eligibility_requirements": "CS Professional",
            "salary_grade": "18"
        }
        assert self.jm.is_match(job) is False

    def test_is_match_fails_eligibility(self):
        job = {
            "position_title": "Admin Officer",
            "location": "Camarines Sur",
            "eligibility_requirements": "Sub-Professional",
            "salary_grade": "18"
        }
        assert self.jm.is_match(job) is False

    def test_is_match_partido_strict(self):
        jm_partido = JobMatcher({
            "require_partido_district": True,
            "require_bicol_region": True
        })
        
        job1 = {
            "location": "Tigaon, Camarines Sur",
            "eligibility_requirements": "CS Professional",
        }
        job2 = {
            "location": "Naga City",
            "eligibility_requirements": "CS Professional",
        }
        
        assert jm_partido.is_match(job1) is True
        assert jm_partido.is_match(job2) is False

    def test_filter_jobs(self):
        jobs = [
            {"position_title": "Job 1", "location": "Manila", "eligibility_requirements": "CS Prof", "salary_grade": "15"},
            {"position_title": "Job 2", "location": "Camarines Sur", "eligibility_requirements": "None", "salary_grade": "15"},
            {"position_title": "Job 3", "location": "Albay", "eligibility_requirements": "RA 1080", "salary_grade": "11"},
        ]
        
        filtered = self.jm.filter_jobs(jobs)
        assert len(filtered) == 1
        assert filtered[0]["position_title"] == "Job 3"
