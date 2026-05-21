"""
telegram_notifier.py — Telegram Bot API integration.

Implemented in Phase 6: Telegram Notifications.
"""

from telegram import Bot
from telegram.error import TelegramError

from src.notifications.message_formatter import format_daily_summary, format_telegram_message
from src.utils.logger import get_logger

log = get_logger(__name__)

class TelegramNotifier:
    """Telegram Bot API integration for job alert delivery."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        if not self.bot_token or not self.chat_id:
            log.warning("TelegramNotifier initialized without bot_token or chat_id.")
        self.bot = Bot(token=self.bot_token) if self.bot_token else None

    async def send_job_alert(self, job_data: dict) -> bool:
        """
        Send a single job alert to the configured chat_id.
        Returns True if successful, False otherwise.
        """
        if not self.bot or not self.chat_id:
            log.error("Cannot send Telegram alert: Token or Chat ID is missing.")
            return False

        message = self.format_message(job_data)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            log.info(f"Successfully sent Telegram alert for '{job_data.get('position_title')}'")
            return True
        except TelegramError as e:
            log.error(f"Failed to send Telegram alert: {str(e)}")
            return False
        except Exception as e:
            log.exception(f"Unexpected error sending Telegram alert: {str(e)}")
            return False

    def format_message(self, job_data: dict) -> str:
        """Format a job data dict into an HTML message string."""
        return format_telegram_message(job_data)

    async def send_daily_summary(self, jobs: list) -> bool:
        """
        Send a daily summary message.
        Returns True if successful, False otherwise.
        """
        if not self.bot or not self.chat_id:
            log.error("Cannot send Telegram summary: Token or Chat ID is missing.")
            return False

        message = format_daily_summary(jobs)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            log.info(f"Successfully sent Telegram daily summary ({len(jobs)} jobs)")
            return True
        except TelegramError as e:
            log.error(f"Failed to send Telegram summary: {str(e)}")
            return False
        except Exception as e:
            log.exception(f"Unexpected error sending Telegram summary: {str(e)}")
            return False
