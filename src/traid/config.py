"""Deterministic, non-secret application configuration for the C01 baseline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class SettingsError(ValueError):
    """Raised when required or constrained configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Load configuration from a supplied mapping or process environment."""

    values = os.environ if environ is None else environ
    environment = values.get("TRAID_ENV", "development").strip().lower()
    log_level = values.get("TRAID_LOG_LEVEL", "INFO").strip().upper()
    host = values.get("TRAID_HOST", "127.0.0.1").strip()
    raw_port = values.get("TRAID_PORT", "8000").strip()

    if environment not in {"development", "test", "production"}:
        raise SettingsError("TRAID_ENV must be development, test, or production")
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise SettingsError("TRAID_LOG_LEVEL must be a standard logging level")
    if not host:
        raise SettingsError("TRAID_HOST must not be empty")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise SettingsError("TRAID_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise SettingsError("TRAID_PORT must be between 1 and 65535")

    return Settings(environment=environment, log_level=log_level, host=host, port=port)
