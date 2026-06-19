"""Persistent settings service backed by a JSON file.

Reads/writes user preferences (theme, refresh interval, yfinance toggle,
default portfolio) to a ``.settings.json`` file in the working directory.
Validates all values before persisting; invalid values are rejected with
a clear error message and the old value is preserved.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "price_refresh_interval": 30,
    "yfinance_enabled": True,
    "default_portfolio_id": "",
}

# Allowed themes
_THEMES = ("dark", "light")

# Valid refresh interval range (seconds)
_INTERVAL_MIN = 5
_INTERVAL_MAX = 3600  # 1 hour

SETTINGS_FILE = ".settings.json"


def _settings_path() -> Path:
    """Return the path to the settings JSON file."""
    return Path(SETTINGS_FILE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_settings() -> dict[str, Any]:
    """Load persisted settings, falling back to defaults.

    Returns a flat dict with keys: ``theme``, ``price_refresh_interval``,
    ``yfinance_enabled``, ``default_portfolio_id``.
    """
    path = _settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only keep known keys; extra keys from the file are ignored
            return {k: data.get(k, v) for k, v in _DEFAULTS.items()}
        except (json.JSONDecodeError, OSError):
            # Corrupt file — fall back to defaults
            pass
    return {**_DEFAULTS}


def save_settings(settings: dict[str, Any]) -> str | None:
    """Persist settings to disk after validation.

    Returns ``None`` on success, or an error string on validation failure.
    """
    error = _validate(settings)
    if error:
        return error

    path = _settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return None
    except OSError:
        return "Failed to write settings file"


def update_setting(
    settings: dict[str, Any], key: str, value: Any
) -> tuple[dict[str, Any], str | None]:
    """Update a single setting with validation.

    Returns ``(updated_settings, error)`` — error is ``None`` on success.
    If the value is invalid, the setting is NOT changed.
    """
    error = _validate_single(key, value)
    if error:
        return settings, error

    # Only update known keys; unknown keys are silently ignored
    if key not in _DEFAULTS:
        return settings, None

    settings[key] = _coerce(key, value)
    return settings, None


def reset_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Reset all settings to defaults."""
    return {**_DEFAULTS}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate(settings: dict[str, Any]) -> str | None:
    """Validate all settings fields. Returns an error string or None."""
    for key, value in settings.items():
        if key not in _DEFAULTS:
            continue  # unknown keys are silently ignored
        error = _validate_single(key, value)
        if error:
            return error
    return None


def _validate_single(key: str, value: Any) -> str | None:
    """Validate a single setting key/value pair."""
    if key == "theme":
        if value not in _THEMES:
            return f"Invalid theme: {value!r}. Must be one of {_THEMES}"
        return None
    if key == "price_refresh_interval":
        # Reject floats explicitly (e.g. 30.5) before int conversion
        if isinstance(value, float):
            return (
                f"Invalid refresh interval: {value!r}. "
                f"Must be an integer."
            )
        try:
            interval = int(value)
        except (ValueError, TypeError):
            return f"Invalid refresh interval: {value!r}. Must be an integer."
        if interval < _INTERVAL_MIN or interval > _INTERVAL_MAX:
            return (
                f"Invalid interval: {interval}s. "
                f"Must be between {_INTERVAL_MIN}s and {_INTERVAL_MAX}s."
            )
        return None
    if key == "yfinance_enabled":
        if not isinstance(value, bool):
            try:
                if isinstance(value, str):
                    return (
                        f"Invalid yfinance_enabled: {value!r}. "
                        f"Must be true or false."
                    )
            except Exception:
                pass
        return None
    if key == "default_portfolio_id":
        # Empty string means "no default" — always valid
        return None
    return None


def _coerce(key: str, value: Any) -> Any:
    """Coerce a value to the correct type for a given key."""
    if key == "theme":
        return str(value)
    if key == "price_refresh_interval":
        return int(value)
    if key == "yfinance_enabled":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    if key == "default_portfolio_id":
        return str(value)
    return value
