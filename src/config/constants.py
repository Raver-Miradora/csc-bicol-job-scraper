"""
constants.py — Static values and constants used across the application.

Implemented in Phase 8: Configuration Management.
"""

# Application metadata
APP_NAME = "CSC Bicol Job Scraper"
APP_VERSION = "0.1.0"

# CSC Portal
CSC_BASE_URL = "https://www.csc.gov.ph/career-opportunities/"

# Bicol Region
BICOL_REGION_ALIASES = ["Bicol Region", "Region V", "Region 5", "REGION V"]

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

# Eligibility keywords
CS_PROFESSIONAL_KEYWORDS = [
    "Career Service Professional",
    "CS Professional",
    "Second Level Eligibility",
    "RA 1080",
]

# Notification channels
CHANNEL_TELEGRAM = "telegram"
CHANNEL_DISCORD = "discord"

# Database
DEFAULT_DB_PATH = "data/jobs.db"

# Logging
DEFAULT_LOG_PATH = "logs/tracker.log"
LOG_MAX_BYTES = 10_485_760   # 10 MB
LOG_BACKUP_COUNT = 5
