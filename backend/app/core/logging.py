import logging
import sys


def configure_logging(log_level: str) -> None:
    """Configure process-wide structured-enough console logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the requested module name."""
    return logging.getLogger(name)
