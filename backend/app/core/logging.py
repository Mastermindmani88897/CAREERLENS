"""
Centralized logging security and sensitive data redaction foundation for CareerLens.
Ensures sensitive tokens, passwords, authorization headers, and database credentials
are never logged in plaintext. Adheres to Phase 8 Security Hardening.
"""

import logging
import re
from typing import Any

# Sensitive field pattern matchers for redaction
_SENSITIVE_PATTERNS = [
    # Key-value pairs: password='...', "token": "...", etc.
    re.compile(
        r'(["\']?(?:password|passwd|pwd|secret|jwt_secret_key|app_secret_key|api_key|access_token|refresh_token)["\']?\s*[:=]\s*["\'])([^"\']+)((?:["\'])?)',
        re.IGNORECASE,
    ),
    # Authorization header: Authorization: Bearer <token>
    re.compile(r"(Authorization:\s*(?:Bearer\s+)?)[^\r\n,]+", re.IGNORECASE),
    # Bearer tokens in text
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    # Basic auth tokens
    re.compile(r"(Basic\s+)[A-Za-z0-9+/=]+", re.IGNORECASE),
    # Database connection URIs containing passwords
    re.compile(r"(postgresql(?:\+asyncpg)?://[^:]+:)([^@]+)(@)", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that intercepts log records and sanitizes sensitive credentials
    such as passwords, tokens, API keys, and connection strings.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_arg(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_arg(arg) for arg in record.args)
            elif isinstance(record.args, list):
                record.args = [self._redact_arg(arg) for arg in record.args]

        return True

    @classmethod
    def redact(cls, text: str) -> str:
        """Apply redaction regex patterns to the input string."""
        if not isinstance(text, str):
            return text

        result = text
        for pattern in _SENSITIVE_PATTERNS:
            if "postgresql" in pattern.pattern:
                result = pattern.sub(r"\g<1>***\g<3>", result)
            elif "Authorization" in pattern.pattern:
                result = pattern.sub(r"\g<1>[REDACTED]", result)
            elif "Bearer" in pattern.pattern:
                result = pattern.sub(r"\g<1>[REDACTED_TOKEN]", result)
            elif "Basic" in pattern.pattern:
                result = pattern.sub(r"\g<1>[REDACTED_CREDENTIALS]", result)
            else:
                result = pattern.sub(r"\g<1>***\g<3>", result)
        return result

    @classmethod
    def _redact_arg(cls, val: Any) -> Any:
        if isinstance(val, str):
            return cls.redact(val)
        return val


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Initialize standard logging with SensitiveDataFilter applied to the root
    and application loggers.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Format string with timestamp, loglevel, logger name, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on re-configuration
    if not any(
        isinstance(h, logging.StreamHandler)
        and any(isinstance(f, SensitiveDataFilter) for f in h.filters)
        for h in root_logger.handlers
    ):
        root_logger.addHandler(console_handler)

    # Configure application logger
    app_logger = logging.getLogger("careerlens")
    app_logger.setLevel(log_level)
    if not any(isinstance(f, SensitiveDataFilter) for f in app_logger.filters):
        app_logger.addFilter(SensitiveDataFilter())

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance under the careerlens namespace."""
    return logging.getLogger(f"careerlens.{name}")
