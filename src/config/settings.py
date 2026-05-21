"""
settings.py — Configuration loader: reads config.yaml and injects environment variables.

Implemented in Phase 8: Configuration Management.
"""


class Settings:
    """Loads and validates configuration from config.yaml and .env."""

    def __init__(self, config_path: str = "config/config.yaml"):
        raise NotImplementedError("Implemented in Phase 8.")

    def get(self, key: str, default=None):
        raise NotImplementedError("Implemented in Phase 8.")

    def validate(self) -> bool:
        raise NotImplementedError("Implemented in Phase 8.")


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load and return the full configuration dictionary."""
    raise NotImplementedError("Implemented in Phase 8.")
