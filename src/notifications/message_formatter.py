"""
message_formatter.py — Rich message templates for Telegram and Discord.

Implemented in Phase 6 & 7: Notification Integrations.
"""


def format_telegram_message(job_data: dict) -> str:
    """Format a job posting as a Telegram HTML message."""
    raise NotImplementedError("Implemented in Phase 6.")


def format_discord_embed(job_data: dict) -> dict:
    """Format a job posting as a Discord embed payload."""
    raise NotImplementedError("Implemented in Phase 7.")


def format_daily_summary(jobs: list) -> str:
    """Format a daily summary of all new jobs found."""
    raise NotImplementedError("Implemented in Phase 6.")
