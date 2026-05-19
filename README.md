# Philippine CSC Job Portal Tracker

An intelligent, automated monitoring system for Philippine Civil Service Commission job postings, focusing on Bicol Region (Region V) and Partido district opportunities.

## Features
- **Automated Monitoring:** Checks the CSC portal for new job postings based on configured intervals.
- **Geographic Filtering:** Focuses on Region V and the Partido district.
- **Eligibility Matching:** Filters specifically for "Career Service Professional" requirements.
- **Real-time Notifications:** Delivers job alerts via Telegram and Discord.
- **Local Storage:** Uses SQLite to track jobs and avoid duplicate notifications.

## Requirements
- Python 3.9+
- See `requirements.txt` for specific dependencies.

## Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials.
4. Review `config/config.yaml` to adjust settings.

## Usage
Start continuous monitoring:
```bash
python main.py start
```

Manual check:
```bash
python main.py check --notify
```
