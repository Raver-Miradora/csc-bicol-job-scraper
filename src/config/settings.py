"""
settings.py — Configuration loader: reads config.yaml and injects environment variables.

Implemented in Phase 8: Configuration Management.
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.utils.logger import get_logger

log = get_logger(__name__)

class Settings:
    """Loads and validates configuration from config.yaml and .env."""

    def __init__(self, config_path: str = "config/config.yaml", env_path: str = ".env"):
        self.config_path = config_path
        self.env_path = env_path
        self._config = {}
        self.load()

    def load(self):
        """Load .env and parse the YAML config file."""
        # Load environment variables first
        if Path(self.env_path).exists():
            load_dotenv(dotenv_path=self.env_path)
            log.debug(f"Loaded environment variables from {self.env_path}")
        else:
            log.warning(f"Environment file {self.env_path} not found. Relying on system env vars.")

        # Load YAML
        if not Path(self.config_path).exists():
            log.error(f"Configuration file {self.config_path} not found.")
            raise FileNotFoundError(f"Missing config file: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            log.info(f"Successfully loaded configuration from {self.config_path}")
        except Exception as e:
            log.error(f"Failed to parse {self.config_path}: {e}")
            raise

    def get(self, key: str, default=None):
        """
        Get a configuration value using dot notation (e.g., 'filters.salary_grade_min').
        """
        keys = key.split('.')
        val = self._config
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return default

    def validate(self) -> bool:
        """Validate critical configuration settings."""
        valid = True

        # Check basic structure
        if 'filters' not in self._config:
            log.warning("Config missing 'filters' section. Default filters will be used.")

        if 'notifications' not in self._config:
            log.warning("Config missing 'notifications' section.")

        # Check notification tokens if enabled
        telegram_enabled = self.get('notifications.telegram.enabled', False)
        if telegram_enabled and not os.getenv("TELEGRAM_BOT_TOKEN"):
            log.error("Telegram is enabled in config but TELEGRAM_BOT_TOKEN is missing in .env")
            valid = False

        discord_enabled = self.get('notifications.discord.enabled', False)
        if discord_enabled and not os.getenv("DISCORD_WEBHOOK_URL"):
            log.error("Discord is enabled in config but DISCORD_WEBHOOK_URL is missing in .env")
            valid = False

        if not valid:
            log.error("Configuration validation failed.")

        return valid


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load and return the full configuration dictionary."""
    settings = Settings(config_path)
    return settings._config
