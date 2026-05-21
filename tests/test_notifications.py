"""
test_notifications.py — Unit tests for Phase 6: Telegram Notifications.

Run with:
    pytest tests/test_notifications.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.notifications.message_formatter import format_telegram_message, format_daily_summary, format_discord_embed
from src.notifications.telegram_notifier import TelegramNotifier
from src.notifications.discord_notifier import DiscordNotifier

class TestMessageFormatter:
    def test_format_telegram_message(self):
        job = {
            "position_title": "Developer",
            "agency": "DICT",
            "location": "Legazpi City",
            "salary_grade": "11",
            "monthly_salary": "P27,000",
            "application_deadline": "2026-12-31",
            "job_url": "https://example.com/job"
        }
        msg = format_telegram_message(job)
        assert "<b>Position:</b> Developer" in msg
        assert "<b>Agency:</b> DICT" in msg
        assert "<b>Location:</b> Legazpi City" in msg
        assert "SG 11 - P27,000" in msg
        assert "2026-12-31" in msg
        assert 'href="https://example.com/job"' in msg
        
    def test_format_telegram_message_missing_fields(self):
        job = {}
        msg = format_telegram_message(job)
        assert "Unknown Position" in msg
        assert "Unknown Agency" in msg
        
    def test_format_daily_summary_empty(self):
        msg = format_daily_summary([])
        assert "No new jobs found" in msg
        
    def test_format_daily_summary_with_jobs(self):
        jobs = [
            {"position_title": "Dev", "agency": "DICT"},
            {"position_title": "Admin", "agency": "DOST"}
        ]
        msg = format_daily_summary(jobs)
        assert "Found <b>2</b> new job(s)" in msg
        assert "1. <b>Dev</b> at DICT" in msg
        assert "2. <b>Admin</b> at DOST" in msg

    def test_format_discord_embed(self):
        job = {
            "position_title": "Developer",
            "agency": "DICT",
            "location": "Legazpi City",
            "salary_grade": "11",
            "monthly_salary": "P27,000",
            "application_deadline": "2026-12-31",
            "job_url": "https://example.com/job"
        }
        embed = format_discord_embed(job)
        assert "Developer" in embed['title']
        assert "DICT" in embed['description']
        assert embed['url'] == "https://example.com/job"
        assert embed['color'] == 3447003
        
        # Check fields
        fields = embed['fields']
        assert len(fields) == 3
        assert fields[0]['name'] == '📍 Location'
        assert fields[0]['value'] == 'Legazpi City'
        assert fields[1]['name'] == '💰 Salary'
        assert fields[1]['value'] == 'SG 11 - P27,000'
        assert fields[2]['name'] == '⏳ Deadline'
        assert fields[2]['value'] == '2026-12-31'


class TestTelegramNotifier:
    def setup_method(self):
        self.notifier = TelegramNotifier("fake_token", "fake_chat_id")
        # Replace the actual bot instance with a mock
        self.notifier.bot = MagicMock()
        self.notifier.bot.send_message = AsyncMock()
        
    def test_init_missing_credentials(self):
        notifier = TelegramNotifier("", "")
        assert notifier.bot is None
        
    @pytest.mark.asyncio
    async def test_send_job_alert_success(self):
        self.notifier.bot.send_message.return_value = MagicMock()
        
        job = {"position_title": "Test Job"}
        result = await self.notifier.send_job_alert(job)
        
        assert result is True
        self.notifier.bot.send_message.assert_called_once()
        kwargs = self.notifier.bot.send_message.call_args.kwargs
        assert kwargs["chat_id"] == "fake_chat_id"
        assert "Test Job" in kwargs["text"]
        assert kwargs["parse_mode"] == "HTML"
        
    @pytest.mark.asyncio
    async def test_send_job_alert_failure(self):
        from telegram.error import TelegramError
        self.notifier.bot.send_message.side_effect = TelegramError("Network Error")
        
        job = {"position_title": "Test Job"}
        result = await self.notifier.send_job_alert(job)
        
        assert result is False
        self.notifier.bot.send_message.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_send_job_alert_missing_credentials(self):
        notifier = TelegramNotifier("", "")
        result = await notifier.send_job_alert({"position_title": "Test Job"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_daily_summary_success(self):
        self.notifier.bot.send_message.return_value = MagicMock()
        
        jobs = [{"position_title": "Test Job 1"}, {"position_title": "Test Job 2"}]
        result = await self.notifier.send_daily_summary(jobs)
        
        assert result is True
        self.notifier.bot.send_message.assert_called_once()
        kwargs = self.notifier.bot.send_message.call_args.kwargs
        assert "2" in kwargs["text"]
        assert "Test Job 1" in kwargs["text"]

class TestDiscordNotifier:
    def setup_method(self):
        self.notifier = DiscordNotifier("https://discord.webhook/url")
        
    def test_init_missing_credentials(self):
        notifier = DiscordNotifier("")
        assert notifier.webhook_url == ""
        
    @patch('src.notifications.discord_notifier.DiscordWebhook')
    def test_send_embed_success(self, MockDiscordWebhook):
        # Setup mock
        mock_webhook_instance = MagicMock()
        MockDiscordWebhook.return_value = mock_webhook_instance
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_webhook_instance.execute.return_value = mock_response
        
        job = {"position_title": "Test Job"}
        result = self.notifier.send_embed(job)
        
        assert result is True
        mock_webhook_instance.add_embed.assert_called_once()
        mock_webhook_instance.execute.assert_called_once()
        
    @patch('src.notifications.discord_notifier.DiscordWebhook')
    def test_send_embed_failure_status_code(self, MockDiscordWebhook):
        mock_webhook_instance = MagicMock()
        MockDiscordWebhook.return_value = mock_webhook_instance
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_webhook_instance.execute.return_value = mock_response
        
        job = {"position_title": "Test Job"}
        result = self.notifier.send_embed(job)
        
        assert result is False
        
    @patch('src.notifications.discord_notifier.DiscordWebhook')
    def test_send_embed_exception(self, MockDiscordWebhook):
        mock_webhook_instance = MagicMock()
        MockDiscordWebhook.return_value = mock_webhook_instance
        mock_webhook_instance.execute.side_effect = Exception("Network Error")
        
        job = {"position_title": "Test Job"}
        result = self.notifier.send_embed(job)
        
        assert result is False

    def test_send_embed_missing_webhook(self):
        notifier = DiscordNotifier("")
        result = notifier.send_embed({"position_title": "Test Job"})
        assert result is False
