"""Windows toast notifications via winotify."""
from __future__ import annotations
import os
import sys
from pathlib import Path

try:
    from winotify import Notification, audio
    _HAS_WINOTIFY = True
except ImportError:
    _HAS_WINOTIFY = False

import app_paths

_ICON_PATH = str(Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "img" / "orimslav_logo_blue_transparent.ico")


def _open_log_folder() -> None:
    try:
        os.startfile(str(app_paths.app_data_dir()))
    except OSError:
        pass


def notify_success(title: str, body: str) -> None:
    if not _HAS_WINOTIFY:
        return
    try:
        n = Notification(
            app_id="OrimslavBackup",
            title=title,
            msg=body,
            icon=_ICON_PATH if Path(_ICON_PATH).exists() else "",
        )
        n.set_audio(audio.Default, loop=False)
        n.add_actions(label="Open log folder", launch=str(app_paths.app_data_dir()))
        n.show()
    except Exception:
        pass


def notify_failure(title: str, body: str) -> None:
    if not _HAS_WINOTIFY:
        return
    try:
        n = Notification(
            app_id="OrimslavBackup",
            title=title,
            msg=body,
            icon=_ICON_PATH if Path(_ICON_PATH).exists() else "",
        )
        n.set_audio(audio.Default, loop=False)
        n.add_actions(label="Open log folder", launch=str(app_paths.app_data_dir()))
        n.show()
    except Exception:
        pass
