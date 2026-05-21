"""
validators.py — Data validation utilities.

Implemented in Phase 8/9: Configuration and Data Validation.
"""

from urllib.parse import urlparse

def validate_job_data(job_data: dict) -> bool:
    """Validate that a job dictionary has all required fields."""
    if not isinstance(job_data, dict):
        return False
        
    required_keys = ['position_title', 'job_url', 'job_hash']
    for key in required_keys:
        if key not in job_data or not job_data[key]:
            return False
            
    return True

def validate_config(config: dict) -> list:
    """Validate the configuration dictionary. Returns a list of error messages."""
    errors = []
    if not isinstance(config, dict):
        return ["Config must be a dictionary."]
        
    if 'filters' not in config:
        errors.append("Missing 'filters' configuration section.")
        
    return errors

def is_valid_url(url: str) -> bool:
    """Check if a URL is well-formed."""
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
