"""
test_config.py — Unit tests for Phase 8: Configuration Management.

Run with:
    pytest tests/test_config.py -v
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from src.config.settings import Settings, load_config

class TestSettings:
    
    @patch("src.config.settings.Path.exists")
    @patch("src.config.settings.load_dotenv")
    @patch("builtins.open", new_callable=mock_open, read_data="filters:\n  salary_grade_min: 15\nnotifications:\n  telegram:\n    enabled: true")
    def test_settings_load_success(self, mock_file, mock_load_dotenv, mock_exists):
        # exists() returns True for both .env and config.yaml
        mock_exists.return_value = True
        
        settings = Settings("dummy_config.yaml", "dummy.env")
        
        mock_load_dotenv.assert_called_once_with(dotenv_path="dummy.env")
        assert settings.get("filters.salary_grade_min") == 15
        assert settings.get("notifications.telegram.enabled") is True
        assert settings.get("invalid.key") is None
        assert settings.get("invalid.key", "default_val") == "default_val"

    @patch("src.config.settings.Path.exists")
    def test_settings_missing_config_raises(self, mock_exists):
        # First call (env) returns False, second call (config) returns False
        mock_exists.side_effect = [False, False]
        
        with pytest.raises(FileNotFoundError):
            Settings("missing_config.yaml", "missing.env")

    @patch("src.config.settings.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid: [yaml: content")
    def test_settings_invalid_yaml_raises(self, mock_file, mock_exists):
        mock_exists.side_effect = [False, True] # env missing, config exists
        
        with pytest.raises(Exception):
            Settings("invalid_config.yaml", "missing.env")

    @patch("src.config.settings.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="filters:\n  salary_grade_min: 15\nnotifications:\n  telegram:\n    enabled: true\n  discord:\n    enabled: true")
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token", "DISCORD_WEBHOOK_URL": "url"})
    def test_validate_success(self, mock_file, mock_exists):
        mock_exists.return_value = True
        settings = Settings()
        assert settings.validate() is True

    @patch("src.config.settings.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="notifications:\n  telegram:\n    enabled: true")
    @patch.dict(os.environ, clear=True)
    def test_validate_failure_missing_env(self, mock_file, mock_exists):
        mock_exists.return_value = True
        settings = Settings()
        # Missing TELEGRAM_BOT_TOKEN
        assert settings.validate() is False

    @patch("src.config.settings.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="notifications:\n  discord:\n    enabled: true")
    @patch.dict(os.environ, clear=True)
    def test_validate_failure_missing_discord_webhook(self, mock_file, mock_exists):
        mock_exists.return_value = True
        settings = Settings()
        assert settings.validate() is False

    @patch("src.config.settings.Settings")
    def test_load_config_helper(self, mock_settings_cls):
        mock_instance = mock_settings_cls.return_value
        mock_instance._config = {"test": "val"}
        
        config = load_config("path")
        assert config == {"test": "val"}
        mock_settings_cls.assert_called_once_with("path")
