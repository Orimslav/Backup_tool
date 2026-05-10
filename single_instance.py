"""Lockfile-based single-instance guard."""
from __future__ import annotations
import ctypes
import os
import time

import app_paths

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            return bool(ok) and exit_code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except OSError:
        return False


def acquire() -> bool:
    lock = app_paths.lock_path()
    if lock.exists():
        try:
            existing_pid = int(lock.read_text().strip())
            if _is_pid_alive(existing_pid):
                return False
        except (ValueError, OSError):
            pass
    try:
        lock.write_text(str(os.getpid()))
        return True
    except OSError:
        return False


def release() -> None:
    try:
        app_paths.lock_path().unlink(missing_ok=True)
    except OSError:
        pass


def signal_show_window() -> None:
    try:
        app_paths.show_request_path().write_text(str(time.time()))
    except OSError:
        pass


def poll_show_request() -> bool:
    p = app_paths.show_request_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
        return True
    return False


def signal_backup_request() -> None:
    try:
        app_paths.backup_request_path().write_text(str(time.time()))
    except OSError:
        pass


def poll_backup_request() -> bool:
    p = app_paths.backup_request_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
        return True
    return False
