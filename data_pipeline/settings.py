"""Paths and Alpaca keys, loaded from the repo's .env (environment variables win). Never print the keys.

A git worktree has no .env of its own. Set CHRONO_ENV_FILE to the path of the main checkout's .env to use it there,
so the file is never copied."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(os.environ.get("CHRONO_ENV_FILE") or ROOT / ".env")


def _load_env(path):
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_ENV = _load_env(ENV_FILE)
_ENV.update({k: v for k, v in os.environ.items() if k.startswith(("APCA_", "CHRONO_"))})

DATA_DIR = Path(_ENV.get("CHRONO_DATA_DIR", r"D:\chrono-data"))
DATA_URL = _ENV.get("APCA_DATA_URL", "https://data.alpaca.markets").rstrip("/")


def alpaca_headers():
    key, secret = _ENV.get("APCA_API_KEY_ID"), _ENV.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise SystemExit("Alpaca keys are missing: fill in .env (see .env.example).")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
