"""
discord_notifier.py — Discord webhook integration with rich embeds.

Implemented in Phase 7: Discord Notifications.
"""

from discord_webhook import DiscordWebhook, DiscordEmbed
from src.utils.logger import get_logger
from src.notifications.message_formatter import format_discord_embed

log = get_logger(__name__)

class DiscordNotifier:
    """Discord webhook integration for job alert delivery."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        if not self.webhook_url:
            log.warning("DiscordNotifier initialized without a webhook_url.")

    def send_embed(self, job_data: dict) -> bool:
        """
        Send a job alert as a rich Discord embed to the configured webhook.
        Returns True if successful, False otherwise.
        """
        if not self.webhook_url:
            log.error("Cannot send Discord alert: Webhook URL is missing.")
            return False

        embed_data = self.create_embed(job_data)
        
        webhook = DiscordWebhook(url=self.webhook_url)
        
        embed = DiscordEmbed(
            title=embed_data.get('title'),
            description=embed_data.get('description'),
            color=embed_data.get('color')
        )
        if embed_data.get('url'):
            embed.set_url(embed_data.get('url'))
            
        for field in embed_data.get('fields', []):
            embed.add_embed_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False)
            )
            
        webhook.add_embed(embed)
        
        try:
            response = webhook.execute()
            if response.status_code in (200, 204):
                log.info(f"Successfully sent Discord embed for '{job_data.get('position_title')}'")
                return True
            else:
                log.error(f"Failed to send Discord alert, status code: {response.status_code}")
                return False
        except Exception as e:
            log.exception(f"Unexpected error sending Discord alert: {str(e)}")
            return False

    def create_embed(self, job_data: dict) -> dict:
        """Format a job data dict into an embed dictionary for DiscordWebhook."""
        return format_discord_embed(job_data)
