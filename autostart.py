"""Windows autostart: logon (registry HKCU\\...\\Run), shutdown + scheduled (Task Scheduler)."""
from __future__ import annotations
import subprocess
import winreg
from typing import Sequence

LOGON_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
LOGON_VALUE_NAME = "OrimslavBackup"
SCHEDULED_TASK_NAME = "OrimslavBackup-Scheduled"

_CREATE_NO_WINDOW = 0x08000000


def is_logon_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, LOGON_RUN_KEY) as key:
            winreg.QueryValueEx(key, LOGON_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def _build_cmd(python_exe: str, script_path: str, flags: str) -> str:
    if script_path:
        return f'"{python_exe}" "{script_path}" {flags}'
    return f'"{python_exe}" {flags}'


def enable_logon(python_exe: str, script_path: str) -> None:
    cmd = _build_cmd(python_exe, script_path, "--minimized --autorun")
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, LOGON_RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, LOGON_VALUE_NAME, 0, winreg.REG_SZ, cmd)


def disable_logon() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, LOGON_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, LOGON_VALUE_NAME)
    except FileNotFoundError:
        pass


def _run_schtasks(args: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["schtasks.exe", *args],
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
    )


def _task_exists(name: str) -> bool:
    return _run_schtasks(["/Query", "/TN", name]).returncode == 0


def _require_ok(result: subprocess.CompletedProcess, action: str) -> None:
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"schtasks {action} failed: {msg}")


def is_scheduled_enabled() -> bool:
    return _task_exists(SCHEDULED_TASK_NAME)


def enable_scheduled(
    python_exe: str,
    script_path: str,
    hh: int,
    mm: int,
    frequency: str,
    days: list[str] | None = None,
) -> None:
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("Time must be 00:00 - 23:59")
    tr = _build_cmd(python_exe, script_path, "--autorun")
    st = f"{hh:02d}:{mm:02d}"
    base = ["/Create", "/F", "/TN", SCHEDULED_TASK_NAME,
            "/TR", tr, "/ST", st, "/RL", "LIMITED"]

    if frequency == "daily":
        args = base + ["/SC", "DAILY"]
    elif frequency == "weekdays":
        args = base + ["/SC", "WEEKLY", "/D", "MON,TUE,WED,THU,FRI"]
    elif frequency == "weekly":
        if not days:
            raise ValueError("`days` is required for weekly frequency")
        args = base + ["/SC", "WEEKLY", "/D", ",".join(days)]
    else:
        raise ValueError(f"Unknown frequency: {frequency!r}")

    _require_ok(_run_schtasks(args), "create scheduled task")


def disable_scheduled() -> None:
    if _task_exists(SCHEDULED_TASK_NAME):
        _require_ok(
            _run_schtasks(["/Delete", "/F", "/TN", SCHEDULED_TASK_NAME]),
            "delete scheduled task",
        )


def get_scheduled_time() -> tuple[int, int, list[str]] | None:
    if not _task_exists(SCHEDULED_TASK_NAME):
        return None
    result = _run_schtasks(["/Query", "/TN", SCHEDULED_TASK_NAME, "/FO", "LIST"])
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "Start Time" in line or "Čas spustenia" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                time_str = parts[1].strip()
                try:
                    hh, mm = int(time_str[:2]), int(time_str[3:5])
                    return hh, mm, []
                except (ValueError, IndexError):
                    pass
    return None
