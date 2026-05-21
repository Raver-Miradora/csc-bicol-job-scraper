"""
eligibility_filter.py — Matches job eligibility requirements against CS Professional criteria.

Implemented in Phase 5: Filtering Logic.
"""


class EligibilityFilter:
    """Matches job eligibility requirements against CS Professional criteria."""

    CS_PROFESSIONAL_KEYWORDS = [
        "Career Service Professional",
        "CS Professional",
        "Second Level Eligibility",
        "RA 1080",
    ]

    def matches_cs_professional(self, requirements: str) -> bool:
        raise NotImplementedError("Implemented in Phase 5.")

    def extract_eligibility_requirements(self, text: str) -> list:
        raise NotImplementedError("Implemented in Phase 5.")

    def parse_salary_grade(self, salary_text: str) -> int:
        raise NotImplementedError("Implemented in Phase 5.")
