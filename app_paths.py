"""Resolve filesystem paths used by the application.

All persistent data lives under %APPDATA%\\OrimslavBackup\\.
The folder is created on first import.
"""
from __future__ import annotations
import os
from pathlib import Path

APP_NAME = "OrimslavBackup"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return app_data_dir() / "config.json"


def log_path() -> Path:
    return app_data_dir() / "backup.log"


def last_run_path() -> Path:
    return app_data_dir() / "last_run.json"


def lock_path() -> Path:
    return app_data_dir() / "app.lock"


def show_request_path() -> Path:
    return app_data_dir() / "app.show_request"


def backup_request_path() -> Path:
    return app_data_dir() / "app.backup_request"
