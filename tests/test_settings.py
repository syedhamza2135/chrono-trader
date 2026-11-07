"""Where the settings come from. These tests use made-up keys in a temporary file and never read the real .env.

Run with: python -m pytest tests
"""
import importlib

import pytest

from data_pipeline import settings


@pytest.fixture
def reload_settings(monkeypatch):
    """Reload settings under a changed environment, and reload them again afterwards as they were."""
    for name in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "CHRONO_ENV_FILE", "CHRONO_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)
    yield lambda: importlib.reload(settings)
    monkeypatch.undo()
    importlib.reload(settings)


def test_chrono_env_file_names_the_env_to_load(tmp_path, monkeypatch, reload_settings):
    env = tmp_path / "other.env"
    env.write_text("APCA_API_KEY_ID=made-up-id\nAPCA_API_SECRET_KEY='made-up-secret'\nCHRONO_DATA_DIR=X:\\data\n",
                   encoding="utf-8")
    monkeypatch.setenv("CHRONO_ENV_FILE", str(env))
    s = reload_settings()
    assert s.ENV_FILE == env
    assert s.alpaca_headers() == {"APCA-API-KEY-ID": "made-up-id", "APCA-API-SECRET-KEY": "made-up-secret"}
    assert str(s.DATA_DIR) == "X:\\data"


def test_environment_variables_win_over_the_file(tmp_path, monkeypatch, reload_settings):
    env = tmp_path / "other.env"
    env.write_text("APCA_API_KEY_ID=from-file\nAPCA_API_SECRET_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("CHRONO_ENV_FILE", str(env))
    monkeypatch.setenv("APCA_API_KEY_ID", "from-environment")
    assert reload_settings().alpaca_headers()["APCA-API-KEY-ID"] == "from-environment"


def test_a_missing_file_means_no_keys(tmp_path, monkeypatch, reload_settings):
    monkeypatch.setenv("CHRONO_ENV_FILE", str(tmp_path / "missing.env"))
    with pytest.raises(SystemExit):
        reload_settings().alpaca_headers()
