"""
region_filter.py — Geographic filtering for Bicol Region V and Partido district.

Implemented in Phase 5: Filtering Logic.
"""

import re
import unicodedata


class RegionFilter:
    """Geographic filtering for Bicol Region V and Partido district."""

    BICOL_PROVINCES = [
        "camarines sur",
        "cam sur",
        "camsur",
        "camarines norte",
        "cam norte",
        "camnorte",
        "albay",
        "sorsogon",
        "catanduanes",
        "masbate",
    ]

    PARTIDO_MUNICIPALITIES = [
        "lagonoy",
        "goa",
        "san jose",
        "tigaon",
        "sagñay",
        "sagnay",
        "tinambac",
        "siruma",
        "garchitorena",
        "presentacion",
        "caramoan",
        "libmanan", # Included as requested in blueprint, though technically outside Partido in some definitions
    ]

    def is_bicol_region(self, location: str) -> bool:
        """Check if the normalized location belongs to the Bicol Region."""
        if not location:
            return False
        loc = self.normalize_location(location)
        return any(prov in loc for prov in self.BICOL_PROVINCES)

    def is_partido_district(self, location: str) -> bool:
        """Check if the normalized location belongs to the Partido District."""
        if not location:
            return False
        loc = self.normalize_location(location)
        return any(muni in loc for muni in self.PARTIDO_MUNICIPALITIES)

    def normalize_location(self, raw_location: str) -> str:
        """
        Normalize location string for robust matching.
        Lowercases, removes accents, and cleans up extra whitespace/punctuation.
        """
        if not raw_location:
            return ""
        # Lowercase
        loc = raw_location.lower()
        # Remove accents (e.g. ñ -> n)
        loc = "".join(c for c in unicodedata.normalize('NFD', loc) if unicodedata.category(c) != 'Mn')
        # Also replace remaining ñ explicitly just in case
        loc = loc.replace('ñ', 'n')
        # Remove punctuation
        loc = re.sub(r'[^\w\s]', ' ', loc)
        # Remove extra whitespace
        loc = ' '.join(loc.split())
        return loc
