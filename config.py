"""Config load/save and last-run status persistence."""
from __future__ import annotations
import json
from datetime import datetime
from typing import Any

import app_paths

DEFAULT_CONFIG: dict[str, Any] = {
    "sources": [],
    "destination": "",
    "format": "zip",
    "cleanup": "none",
    "keep_count": "5",
    "keep_days": "30",
    "rar_path": "",
    "remember_password": False,
    "password": "",
    "language": "sk",
    "autostart_logon": False,
    "autostart_scheduled": False,
    "scheduled_time": "17:00",
    "scheduled_frequency": "daily",
    "scheduled_days": ["MON", "TUE", "WED", "THU", "FRI"],
    "exclude_patterns": [
        "__pycache__", "node_modules", ".venv", ".git",
        "*.tmp", "*.log", "Thumbs.db", ".DS_Store",
    ],
    "minimize_to_tray_on_close": True,
    "start_minimized": False,
    "notify_on_success": False,
    "notify_on_failure": True,
}


def load_config() -> dict[str, Any]:
    path = app_paths.config_path()
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cfg.update(data)
            if not cfg.get("remember_password"):
                cfg["password"] = ""
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    to_save = dict(cfg)
    if not to_save.get("remember_password"):
        to_save.pop("password", None)
    app_paths.config_path().write_text(
        json.dumps(to_save, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_last_run() -> dict[str, Any] | None:
    path = app_paths.last_run_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_last_run(result: str, message: str, duration: float) -> None:
    data = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "result": result,
        "message": message,
        "duration_seconds": round(duration, 1),
    }
    app_paths.last_run_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
