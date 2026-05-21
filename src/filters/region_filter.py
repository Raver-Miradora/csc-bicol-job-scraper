"""
region_filter.py — Geographic filtering for Bicol Region V and Partido district.

Implemented in Phase 5: Filtering Logic.
"""


class RegionFilter:
    """Geographic filtering for Bicol Region V and Partido district."""

    BICOL_PROVINCES = [
        "Camarines Sur",
        "Camarines Norte",
        "Albay",
        "Sorsogon",
        "Catanduanes",
        "Masbate",
    ]

    PARTIDO_MUNICIPALITIES = [
        "Lagonoy",
        "Goa",
        "San Jose",
        "Tigaon",
        "Sagñay",
        "Tinambac",
        "Siruma",
        "Garchitorena",
        "Presentacion",
        "Caramoan",
        "Libmanan",
    ]

    def is_bicol_region(self, location: str) -> bool:
        raise NotImplementedError("Implemented in Phase 5.")

    def is_partido_district(self, location: str) -> bool:
        raise NotImplementedError("Implemented in Phase 5.")

    def normalize_location(self, raw_location: str) -> str:
        raise NotImplementedError("Implemented in Phase 5.")
