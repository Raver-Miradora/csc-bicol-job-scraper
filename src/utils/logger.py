"""
logger.py — Application logging setup using loguru.

Provides a single pre-configured logger instance for the entire application.
Import `logger` from this module everywhere instead of using loguru directly.

Usage:
    from src.utils.logger import logger, setup_logger

    setup_logger(log_file="logs/tracker.log", level="INFO")
    logger.info("Scraper started")
    logger.warning("Rate limit approaching")
    logger.error("Failed to fetch page: {url}", url=url)
"""

import sys
from pathlib import Path

from loguru import logger as _loguru_logger

# Re-export the configured logger
logger = _loguru_logger

_is_configured = False


def setup_logger(
    log_file: str = "logs/tracker.log",
    level: str = "INFO",
    colorize: bool = True,
    rotation: str = "10 MB",
    retention: int = 5,
) -> None:
    """
    Configure loguru with console + rotating file sinks.

    Call this once at application startup (main.py or scripts).
    Subsequent calls are no-ops to prevent duplicate handlers.

    Args:
        log_file:  Path to the log file.
        level:     Minimum log level (DEBUG / INFO / WARNING / ERROR).
        colorize:  Enable ANSI colour codes in console output.
        rotation:  When to rotate the log file (loguru size/time string).
        retention: Number of rotated files to keep.
    """
    global _is_configured
    if _is_configured:
        return

    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Remove the default loguru handler
    logger.remove()

    # ── Console sink ─────────────────────────────────────────────────────
    console_fmt = (
        "<green>{time:HH:mm:ss}</green> "
        "<level>{level: <8}</level> "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stdout,
        format=console_fmt,
        level=level,
        colorize=colorize,
        enqueue=True,          # Thread-safe
    )

    # ── File sink ─────────────────────────────────────────────────────────
    file_fmt = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} — "
        "{message}"
    )
    logger.add(
        log_file,
        format=file_fmt,
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
        encoding="utf-8",
    )

    # ── Structured JSON File sink ─────────────────────────────────────────
    json_log_file = str(Path(log_file).with_suffix(".json.log"))
    logger.add(
        json_log_file,
        format="{message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
        serialize=True,
    )

    _is_configured = True
    logger.info(
        "Logger initialised — level={level} file={file}",
        level=level,
        file=log_file,
    )


def get_logger(name: str = "csc_tracker"):
    """
    Return a logger bound to a specific module name.

    Usage:
        log = get_logger(__name__)
        log.info("doing something")
    """
    return logger.bind(name=name)

import time
from contextlib import contextmanager

@contextmanager
def time_operation(operation_name: str):
    """
    Context manager to collect performance metrics for an operation.
    Logs the execution time with structured data.
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        logger.info(
            f"Metrics: Operation '{operation_name}' completed in {elapsed:.3f}s",
            metric_operation=operation_name,
            metric_duration_s=elapsed
        )
