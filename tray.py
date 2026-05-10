"""System tray icon via pystray + Pillow."""
from __future__ import annotations
import os
import sys
import threading
from pathlib import Path
from typing import Callable

try:
    import pystray
    from PIL import Image
    _HAS_PYSTRAY = True
except ImportError:
    _HAS_PYSTRAY = False

import app_paths

_ICON_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "img" / "orimslav_logo_blue_transparent.ico"


def _load_icon_image() -> "Image.Image":
    if _ICON_PATH.exists():
        try:
            from PIL import Image as _Image
            return _Image.open(_ICON_PATH).convert("RGBA")
        except Exception:
            pass
    from PIL import Image as _Image
    img = _Image.new("RGBA", (64, 64), color=(30, 80, 160, 255))
    return img


class TrayIcon:
    """Manages the system tray icon lifecycle on its own thread."""

    def __init__(
        self,
        t: "Callable[[str], str]",
        on_show: Callable[[], None],
        on_run_backup: Callable[[], None],
        on_exit: Callable[[], None],
    ):
        self._t = t
        self._on_show = on_show
        self._on_run_backup = on_run_backup
        self._on_exit = on_exit
        self._icon: "pystray.Icon | None" = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not _HAS_PYSTRAY:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        t = self._t
        menu = pystray.Menu(
            pystray.MenuItem(t("TRAY_SHOW"), self._show, default=True),
            pystray.MenuItem(t("TRAY_RUN_NOW"), self._run_backup),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("TRAY_OPEN_LOG"), self._open_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("TRAY_EXIT"), self._exit),
        )
        self._icon = pystray.Icon(
            "OrimslavBackup",
            _load_icon_image(),
            self._t("WINDOW_TITLE"),
            menu,
        )
        self._icon.run()

    def _show(self, icon=None, item=None) -> None:
        self._on_show()

    def _run_backup(self, icon=None, item=None) -> None:
        self._on_run_backup()

    def _open_log(self, icon=None, item=None) -> None:
        try:
            os.startfile(str(app_paths.app_data_dir()))
        except OSError:
            pass

    def _exit(self, icon=None, item=None) -> None:
        self.stop()
        self._on_exit()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def update_tooltip(self, text: str) -> None:
        if self._icon:
            try:
                self._icon.title = text
            except Exception:
                pass
