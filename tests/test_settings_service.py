"""Tests for the persistent settings service.

Covers default values, persistence, validation, coercion, and reset.
"""

import json
import os
from pathlib import Path

from portfolio_manager.services.settings_service import (
    _THEMES,
    _coerce,
    _validate,
    _validate_single,
    load_settings,
    reset_settings,
    save_settings,
    update_setting,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tmp_settings_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a .settings.json file."""
    # Change working dir for the test
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    return tmp_path


def _restore_cwd(old_cwd: str) -> None:
    os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# load_settings
# ---------------------------------------------------------------------------


class TestLoadSettings:
    """Tests for load_settings()."""

    def test_returns_defaults_when_no_file(self, tmp_path):
        """When no .settings.json exists, returns defaults."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = load_settings()
            assert result["theme"] == "dark"
            assert result["price_refresh_interval"] == 30
            assert result["yfinance_enabled"] is True
            assert result["default_portfolio_id"] == ""
        finally:
            os.chdir(old_cwd)

    def test_returns_persisted_values(self, tmp_path):
        """When a file exists, returns persisted values."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            settings_path = tmp_path / ".settings.json"
            settings_path.write_text(
                json.dumps({
                    "theme": "light",
                    "price_refresh_interval": 60,
                    "yfinance_enabled": False,
                    "default_portfolio_id": "abc-123",
                })
            )
            result = load_settings()
            assert result["theme"] == "light"
            assert result["price_refresh_interval"] == 60
            assert result["yfinance_enabled"] is False
            assert result["default_portfolio_id"] == "abc-123"
        finally:
            os.chdir(old_cwd)

    def test_falls_back_to_defaults_on_corrupt_file(self, tmp_path):
        """When the file is invalid JSON, returns defaults."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            settings_path = tmp_path / ".settings.json"
            settings_path.write_text("not valid json {{{")
            result = load_settings()
            assert result["theme"] == "dark"
            assert result["price_refresh_interval"] == 30
        finally:
            os.chdir(old_cwd)

    def test_falls_back_on_missing_keys(self, tmp_path):
        """When the file has only some keys, missing keys use defaults."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            settings_path = tmp_path / ".settings.json"
            settings_path.write_text(json.dumps({"theme": "light"}))
            result = load_settings()
            assert result["theme"] == "light"
            assert result["price_refresh_interval"] == 30
            assert result["yfinance_enabled"] is True
        finally:
            os.chdir(old_cwd)

    def test_ignores_unknown_keys(self, tmp_path):
        """Extra keys in the file are silently ignored."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            settings_path = tmp_path / ".settings.json"
            settings_path.write_text(
                json.dumps({
                    "theme": "dark",
                    "some_unknown_key": "value",
                })
            )
            result = load_settings()
            assert result["theme"] == "dark"
            assert "some_unknown_key" not in result
        finally:
            os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# save_settings / validation
# ---------------------------------------------------------------------------


class TestSaveSettings:
    """Tests for save_settings() and validation."""

    def test_save_successfully_writes_file(self, tmp_path):
        """Valid settings are written to .settings.json."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            error = save_settings({
                "theme": "light",
                "price_refresh_interval": 120,
                "yfinance_enabled": False,
                "default_portfolio_id": "portfolio-1",
            })
            assert error is None
            settings_path = tmp_path / ".settings.json"
            data = json.loads(settings_path.read_text())
            assert data["theme"] == "light"
            assert data["price_refresh_interval"] == 120
            assert data["yfinance_enabled"] is False
            assert data["default_portfolio_id"] == "portfolio-1"
        finally:
            os.chdir(old_cwd)

    def test_save_rejects_invalid_theme(self, tmp_path):
        """Invalid theme values are rejected and not persisted."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            error = save_settings({
                "theme": "midnight",
                "price_refresh_interval": 30,
                "yfinance_enabled": True,
                "default_portfolio_id": "",
            })
            assert error is not None
            assert "midnight" in error.lower()
            # File should not be created
            assert not (tmp_path / ".settings.json").exists()
        finally:
            os.chdir(old_cwd)

    def test_save_rejects_interval_too_low(self, tmp_path):
        """Interval below 5 seconds is rejected."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            error = save_settings({
                "theme": "dark",
                "price_refresh_interval": 3,
                "yfinance_enabled": True,
                "default_portfolio_id": "",
            })
            assert error is not None
            assert "5" in error
        finally:
            os.chdir(old_cwd)

    def test_save_rejects_interval_too_high(self, tmp_path):
        """Interval above 3600 seconds is rejected."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            error = save_settings({
                "theme": "dark",
                "price_refresh_interval": 5000,
                "yfinance_enabled": True,
                "default_portfolio_id": "",
            })
            assert error is not None
            assert "3600" in error
        finally:
            os.chdir(old_cwd)

    def test_save_rejects_non_integer_interval(self, tmp_path):
        """Non-integer interval is rejected."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            error = save_settings({
                "theme": "dark",
                "price_refresh_interval": "abc",
                "yfinance_enabled": True,
                "default_portfolio_id": "",
            })
            assert error is not None
            assert "integer" in error.lower()
        finally:
            os.chdir(old_cwd)

    def test_save_rejects_float_interval(self, tmp_path):
        """Float interval is rejected."""
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            error = save_settings({
                "theme": "dark",
                "price_refresh_interval": 30.5,
                "yfinance_enabled": True,
                "default_portfolio_id": "",
            })
            assert error is not None
        finally:
            os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# update_setting
# ---------------------------------------------------------------------------


class TestUpdateSetting:
    """Tests for update_setting() - single-key updates with validation."""

    def test_update_theme_validates(self):
        """Theme update validates allowed values."""
        settings = load_settings()
        settings, error = update_setting(settings, "theme", "light")
        assert error is None
        assert settings["theme"] == "light"

        settings, error = update_setting(settings, "theme", "midnight")
        assert error is not None
        # Original value should be preserved
        assert settings["theme"] == "light"

    def test_update_interval_bounds(self):
        """Interval update validates bounds."""
        settings = load_settings()
        settings, error = update_setting(settings, "price_refresh_interval", 10)
        assert error is None
        assert settings["price_refresh_interval"] == 10

        settings, error = update_setting(settings, "price_refresh_interval", 4)
        assert error is not None
        assert settings["price_refresh_interval"] == 10

        settings, error = update_setting(settings, "price_refresh_interval", 3600)
        assert error is None
        assert settings["price_refresh_interval"] == 3600

        settings, error = update_setting(settings, "price_refresh_interval", 3601)
        assert error is not None

    def test_update_yfinance_enabled(self):
        """yfinance_enabled toggle works."""
        settings = load_settings()
        settings, error = update_setting(settings, "yfinance_enabled", False)
        assert error is None
        assert settings["yfinance_enabled"] is False

        settings, error = update_setting(settings, "yfinance_enabled", True)
        assert error is None
        assert settings["yfinance_enabled"] is True

    def test_update_unknown_key_ignored(self):
        """Updating an unknown key does not change anything."""
        settings = load_settings()
        settings, error = update_setting(settings, "nonexistent_key", "value")
        assert error is None  # unknown keys are silently ignored
        assert "nonexistent_key" not in settings


# ---------------------------------------------------------------------------
# _coerce
# ---------------------------------------------------------------------------


class TestCoerce:
    """Tests for the _coerce() helper."""

    def test_coerce_theme_to_str(self):
        assert _coerce("theme", 42) == "42"
        assert _coerce("theme", "dark") == "dark"

    def test_coerce_interval_to_int(self):
        assert _coerce("price_refresh_interval", 30.9) == 30
        assert _coerce("price_refresh_interval", "60") == 60

    def test_coerce_yfinance_bool(self):
        assert _coerce("yfinance_enabled", "true") is True
        assert _coerce("yfinance_enabled", "false") is False
        assert _coerce("yfinance_enabled", 1) is True
        assert _coerce("yfinance_enabled", 0) is False

    def test_coerce_portfolio_id_to_str(self):
        assert _coerce("default_portfolio_id", None) == "None"
        assert _coerce("default_portfolio_id", "") == ""


# ---------------------------------------------------------------------------
# reset_settings
# ---------------------------------------------------------------------------


class TestResetSettings:
    """Tests for reset_settings()."""

    def test_resets_all_fields_to_defaults(self):
        settings = {
            "theme": "light",
            "price_refresh_interval": 999,
            "yfinance_enabled": False,
            "default_portfolio_id": "some-id",
            "extra_key": "extra_value",
        }
        result = reset_settings(settings)
        assert result["theme"] == "dark"
        assert result["price_refresh_interval"] == 30
        assert result["yfinance_enabled"] is True
        assert result["default_portfolio_id"] == ""
        # Extra keys are dropped (defaults-only)
        assert "extra_key" not in result


# ---------------------------------------------------------------------------
# _validate_single
# ---------------------------------------------------------------------------


class TestValidateSingle:
    """Tests for the _validate_single() helper."""

    def test_valid_themes(self):
        for theme in _THEMES:
            assert _validate_single("theme", theme) is None

    def test_invalid_theme(self):
        assert _validate_single("theme", "midnight") is not None

    def test_valid_intervals(self):
        for val in [5, 30, 3600]:
            assert _validate_single("price_refresh_interval", val) is None

    def test_invalid_intervals(self):
        assert _validate_single("price_refresh_interval", 4) is not None
        assert _validate_single("price_refresh_interval", 3601) is not None

    def test_valid_yfinance(self):
        assert _validate_single("yfinance_enabled", True) is None
        assert _validate_single("yfinance_enabled", False) is None

    def test_valid_portfolio_id(self):
        assert _validate_single("default_portfolio_id", "") is None
        assert _validate_single("default_portfolio_id", "abc-123") is None
