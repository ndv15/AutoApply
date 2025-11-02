"""Logger helper with secret redaction.

This module defines a simple helper to acquire a ``logging.Logger`` that
redacts values associated with sensitive environment keys.  It ensures
handlers are added only once per logger name and configures a basic format.
"""

import logging
from typing import Iterable


# Keys that should be redacted in log records.
SENSITIVE_KEYS: set[str] = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
    "PERPLEXITY_API_KEY",
}


class RedactFilter(logging.Filter):
    """Logging filter that redacts sensitive values in ``record.args``.

    The filter inspects dictionary arguments passed to logging methods and
    replaces values for keys found in :data:`SENSITIVE_KEYS` with ``"***"``.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        if isinstance(record.args, dict):
            for key in list(record.args.keys()):
                if key in SENSITIVE_KEYS:
                    record.args[key] = "***"
        return True


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a logger configured with a redacting filter and a stream handler.

    :param name: Name of the logger to retrieve or create.
    :param level: Logging level as a string (e.g. ``"DEBUG"``).
    :returns: A configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        handler.addFilter(RedactFilter())
        logger.addHandler(handler)
        logger.setLevel(level.upper())
    return logger