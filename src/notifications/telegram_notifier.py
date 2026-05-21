"""
telegram_notifier.py — Telegram Bot API integration.

Implemented in Phase 6: Telegram Notifications.
"""


class TelegramNotifier:
    """Telegram Bot API integration for job alert delivery."""

    def __init__(self, bot_token: str, chat_id: str):
        raise NotImplementedError("Implemented in Phase 6.")

    async def send_job_alert(self, job_data: dict) -> bool:
        raise NotImplementedError("Implemented in Phase 6.")

    def format_message(self, job_data: dict) -> str:
        raise NotImplementedError("Implemented in Phase 6.")

    def send_daily_summary(self, jobs: list):
        raise NotImplementedError("Implemented in Phase 6.")
