"""
eligibility_filter.py — Matches job eligibility requirements against CS Professional criteria.

Implemented in Phase 5: Filtering Logic.
"""

import re


class EligibilityFilter:
    """Matches job eligibility requirements against CS Professional criteria."""

    CS_PROFESSIONAL_KEYWORDS = [
        "career service professional",
        "cs professional",
        "second level eligibility",
        "ra 1080",
        "r.a. 1080",
        "csp",
    ]

    def matches_cs_professional(self, requirements: str) -> bool:
        """
        Check if the requirements text matches CS Professional criteria.
        """
        if not requirements:
            # If there's no requirement text at all, we might want to default to False
            return False

        req_lower = requirements.lower()

        # Exact substring matches
        for kw in self.CS_PROFESSIONAL_KEYWORDS:
            if kw in req_lower:
                return True

        # Word boundary match for "professional"
        if re.search(r'\bprofessional\b', req_lower):
            # Exclude sub-professional
            if 'sub-professional' not in req_lower and 'sub professional' not in req_lower:
                return True

        return False

    def extract_eligibility_requirements(self, text: str) -> list:
        """
        Extracts specific eligibilities if multiple exist in the text.
        (Future enhancement/utility if needed, just returns cleaned text as a list item for now)
        """
        if not text:
            return []

        # Simple split by common delimiters if it's a list
        parts = re.split(r'[,/|]|( or )|( and )', text)
        return [p.strip() for p in parts if p and p.strip() and p.strip() not in ('or', 'and')]

    def parse_salary_grade(self, salary_text: str) -> int:
        """
        Extract numeric salary grade from text. Return 0 if not found.
        """
        if not salary_text:
            return 0

        match = re.search(r'(?:salary\s*grade|sg)\s*[-:]?\s*(\d+)', salary_text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

        # Also just look for a number if it's standalone like "18"
        if salary_text.strip().isdigit():
            return int(salary_text.strip())

        return 0
