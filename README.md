# 🏛️ CSC Bicol Job Scraper

> An intelligent, automated monitoring system for Philippine Civil Service Commission (CSC) job postings — laser-focused on **Bicol Region (Region V)** and **Partido district** opportunities.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Discord](https://img.shields.io/badge/Discord-Webhook-5865F2?logo=discord&logoColor=white)](https://discord.com/developers/docs/resources/webhook)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This system acts as a **personal HR assistant** for government job seekers in the Bicol Region. It continuously monitors the [CSC Career Opportunities Portal](https://www.csc.gov.ph/career-opportunities/) and delivers real-time alerts for positions matching:

- 📍 **Geographic Focus**: Bicol Region (Region V) — Camarines Sur, Camarines Norte, Albay, Sorsogon, Catanduanes, Masbate; with special attention to **Partido district** municipalities
- ✅ **Eligibility**: Career Service Professional (CS Professional / Second Level Eligibility / RA 1080)
- 💼 **Any salary grade** (configurable minimum threshold)

---

## Features

| Feature | Description |
|---|---|
| 🔍 **Automated Scraping** | Continuously monitors CSC portal with respectful rate limiting |
| 🎯 **Smart Filtering** | Region, district, and eligibility-based filtering |
| 📲 **Telegram Alerts** | Instant notifications via Telegram Bot |
| 💬 **Discord Embeds** | Rich embed notifications via Discord Webhook |
| 🗄️ **Local Storage** | SQLite database — no data leaves your machine |
| 📊 **Daily Summaries** | Scheduled digest of all new job postings |
| 🔁 **Idempotent** | Never sends duplicate notifications for the same job |
| 📝 **Audit Logging** | Complete logs of all scraping and notification activity |
| ⚙️ **YAML Config** | Easy filter adjustments without touching code |

---

## Prerequisites

- **Python 3.11+**
- A **Telegram Bot Token** (via [@BotFather](https://t.me/BotFather)) — optional
- A **Discord Webhook URL** — optional
- Internet access to reach `csc.gov.ph`

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Raver-Miradora/csc-bicol-job-scraper.git
cd csc-bicol-job-scraper

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp config/.env.example .env
# Edit .env with your bot tokens and webhook URLs

# 5. Initialize the database
python scripts/init_db.py
```

---

## Configuration

All settings live in `config/config.yaml`. Key sections:

```yaml
filters:
  provinces:
    - "Camarines Sur"
    - "Camarines Norte"
    - "Albay"
  eligibilities:
    - "Career Service Professional"
  salary_grade_min: 10  # optional minimum SG

notifications:
  telegram:
    enabled: true
  discord:
    enabled: false
```

Sensitive values (tokens, webhook URLs) are loaded from `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
DISCORD_WEBHOOK_URL=your_webhook_url_here
```

---

## Usage

```bash
# Interactive setup wizard
python main.py config --setup

# Start continuous monitoring (runs every 60 min by default)
python main.py start

# One-time manual check
python main.py check --notify

# View tracking statistics
python main.py stats

# Test notification delivery
python main.py test
```

### Example CLI Output

```
╔══════════════════════════════════════════════════════════════╗
║           CSC JOB TRACKER - Monitoring Started               ║
╚══════════════════════════════════════════════════════════════╝

⏰ Check Interval: Every 60 minutes
📍 Target Region: Bicol Region (Region V)
🎯 District Focus: Partido
✅ Eligibility: Career Service Professional

[14:30:15] 🔍 Starting job check...
[14:30:18] ✓ Fetched 45 job postings
[14:30:22] ✓ Filtered to 3 matching positions
[14:30:23] 🆕 NEW JOB FOUND: Administrative Officer IV
[14:30:24] 📤 Notification sent via Telegram
```

---

## Project Structure

```
csc-bicol-job-scraper/
│
├── src/
│   ├── scraper/        # HTTP session, CSC portal scraping, HTML parsers
│   ├── filters/        # Region, district, and eligibility filters
│   ├── storage/        # SQLite database layer and data models
│   ├── notifications/  # Telegram bot and Discord webhook integrations
│   ├── config/         # YAML config loader and constants
│   └── utils/          # Logger, validators
│
├── config/
│   ├── config.yaml     # User configuration
│   └── .env.example    # Environment variable template
│
├── data/               # SQLite database (gitignored)
├── logs/               # Application logs (gitignored)
├── tests/              # Unit and integration tests
├── scripts/            # DB init and manual run helpers
└── main.py             # CLI entry point
```

---

## How It Works

```
CSC Portal ──► HTTP Scraper ──► HTML Parser ──► Region Filter ──► Eligibility Filter
                                                                         │
                                                                         ▼
                                                               SQLite Database
                                                                         │
                                                              (new job detected)
                                                                         │
                                                     ┌───────────────────┤
                                                     ▼                   ▼
                                              Telegram Bot        Discord Webhook
```

1. The scraper fetches job listings from the CSC portal every N minutes
2. Each job is parsed and hashed (SHA-256) for idempotency
3. New jobs are filtered by region, district, and eligibility
4. Matching jobs are saved to SQLite and notifications are sent
5. A daily summary is delivered at a configurable time

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `No jobs found` | Check `config.yaml` filters; CSC portal structure may have changed |
| `Telegram not sending` | Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` |
| `Database error` | Run `python scripts/init_db.py` to re-initialize |
| `Rate limit hit` | Increase `check_interval_minutes` in `config.yaml` |
| `JS-rendered content` | Set `use_playwright: true` in scraper config (advanced) |

---

## Contributing

Contributions are welcome! Please open an issue first to discuss major changes.

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feat/your-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

<p align="center">
  Built with ❤️ for Bicolano government job seekers 🌋
</p>
