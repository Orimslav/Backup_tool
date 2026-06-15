"""Folder Backup Tool — main entry point and GUI."""
from __future__ import annotations
import sys
import os
from pathlib import Path


def _res(rel: str) -> Path:
    """Resolve a path relative to the bundle root (works frozen and unfrozen)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / rel


def _early_excepthook(exc_type, exc_value, exc_tb):
    import traceback
    try:
        appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        err_file = Path(appdata) / "OrimslavBackup" / "startup_error.txt"
        err_file.parent.mkdir(parents=True, exist_ok=True)
        err_file.write_text(
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            encoding="utf-8"
        )
    except Exception:
        pass


sys.excepthook = _early_excepthook

import atexit
import logging
import logging.handlers
import threading
import time
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox
from tkinter import ttk
import tkinter as tk
from typing import Any

import app_paths
import autostart
import backup_core
import config as cfg_module
import i18n
import notifications
import single_instance
import tray

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
C_BG       = "#1e2230"
C_HEADER   = "#161b27"
C_STRIPE   = "#4a90d9"
C_BTN      = "#2e5fa3"
C_BTN_FG   = "#ffffff"
C_BTN_HOV  = "#4a90d9"
C_BTN2     = "#2a3a55"
C_BTN2_FG  = "#a0b8d8"
C_LOG_BG   = "#11141d"
C_LOG_FG   = "#cdd6f4"
C_LOG_OK   = "#a6e3a1"
C_LOG_ERR  = "#f38ba8"
C_LOG_INFO = "#89dceb"
C_LOG_TS   = "#4a6080"
C_SEP      = "#2a3347"
C_ENTRY_BG = "#2a3347"
C_ENTRY_FG = "#cdd6f4"
C_LABEL_FG = "#a0b0cc"
C_TITLE_FG = "#89dceb"
C_ACCENT   = "#4a90d9"
C_DIM      = "#6b7a99"

KOFI_URL   = "https://ko-fi.com/orimslav"
GITHUB_URL = "https://github.com/Orimslav"
C_KOFI     = "#29ABE0"
C_GITHUB   = "#24292e"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_file_handler = logging.handlers.RotatingFileHandler(
    app_paths.log_path(), maxBytes=5_000_000, backupCount=3, encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.DEBUG, handlers=[_file_handler])
logger = logging.getLogger("backup")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_RAR_CANDIDATES = [
    r"C:\Program Files\WinRAR\rar.exe",
    r"C:\Program Files (x86)\WinRAR\rar.exe",
]

def _detect_rar() -> str:
    for p in _RAR_CANDIDATES:
        if Path(p).exists():
            return p
    return ""

def _fmt_size(path: str) -> str:
    try:
        b = Path(path).stat().st_size
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
    except OSError:
        return "?"

def _load_image(path_str: str, height: int, composite_bg: tuple = (22, 27, 39)):
    try:
        from PIL import Image, ImageTk
        img = Image.open(path_str).convert("RGBA")
        ratio = height / img.height
        img = img.resize((int(img.width * ratio), height), Image.LANCZOS)
        bg = Image.new("RGBA", img.size, (*composite_bg, 255))
        bg.paste(img, mask=img.split()[3])
        return ImageTk.PhotoImage(bg.convert("RGB"))
    except Exception:
        return None

def _load_flag(path_str: str, height: int = 22):
    try:
        from PIL import Image, ImageTk
        img = Image.open(path_str).convert("RGB")
        ratio = height / img.height
        img = img.resize((int(img.width * ratio), height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def _hover_tint(widget: tk.Widget, normal: str, hover: str) -> None:
    widget.bind("<Enter>", lambda e: widget.config(bg=hover))
    widget.bind("<Leave>", lambda e: widget.config(bg=normal))

# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class BackupApp:
    def __init__(self, root: tk.Tk, translator: i18n.Translator, cfg: dict[str, Any]):
        self.root = root
        self.t = translator
        self.cfg = cfg
        self._translatable: list[tuple[Any, str, str]] = []
        self._backup_running = False
        self._tray: tray.TrayIcon | None = None
        self._img_refs: list = []   # keep PIL images alive

        if not cfg.get("rar_path"):
            cfg["rar_path"] = _detect_rar()

        self._setup_style()
        self._build_ui()
        self._apply_config_to_ui()
        self._refresh_autostart_state()
        self._update_status_bar()
        self._poll_show_request()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tray = tray.TrayIcon(
            t=self.t, on_show=self._show_window,
            on_run_backup=self._trigger_backup_from_tray,
            on_exit=self._quit_app,
        )
        self._tray.start()
        if cfg.get("start_minimized"):
            self.root.withdraw()

    # -----------------------------------------------------------------------
    # Style
    # -----------------------------------------------------------------------
    def _setup_style(self) -> None:
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(".", background=C_BG, foreground=C_LABEL_FG, font=("Segoe UI", 11))


        s.configure("TFrame", background=C_BG)
        s.configure("TScrollbar", background=C_SEP, troughcolor=C_LOG_BG,
                    arrowcolor=C_LABEL_FG, borderwidth=0, relief="flat")
        s.map("TScrollbar", background=[("active", C_BTN)])
        s.configure("Backup.Horizontal.TProgressbar",
                    troughcolor=C_SEP, background=C_STRIPE,
                    borderwidth=0, thickness=8)
        s.configure("TCombobox", fieldbackground=C_ENTRY_BG, background=C_BTN2,
                    foreground=C_ENTRY_FG, selectbackground=C_BTN,
                    selectforeground="#ffffff", bordercolor=C_SEP, arrowcolor=C_LABEL_FG)
        s.map("TCombobox",
              fieldbackground=[("readonly", C_ENTRY_BG)],
              foreground=[("readonly", C_ENTRY_FG)],
              selectbackground=[("readonly", C_ENTRY_BG)])

    # -----------------------------------------------------------------------
    # Widget factories
    # -----------------------------------------------------------------------
    def _make_btn(self, parent, text: str, command,
                  primary: bool = False, outline: bool = False) -> tk.Button:
        if primary:
            bg, fg, abg = C_BTN, "white", C_BTN_HOV
            font, padx, pady = ("Segoe UI", 13, "bold"), 24, 11
            hlt, hlt_bg = 0, C_BTN
        elif outline:
            bg, fg, abg = C_BG, C_STRIPE, C_BTN2
            font, padx, pady = ("Segoe UI", 11), 14, 9
            hlt, hlt_bg = 1, C_STRIPE
        else:
            bg, fg, abg = C_BTN2, C_BTN2_FG, C_BTN_HOV
            font, padx, pady = ("Segoe UI", 11), 10, 5
            hlt, hlt_bg = 0, C_BTN2

        btn = tk.Button(
            parent, text=text, command=command,
            font=font, bg=bg, fg=fg, relief="flat",
            padx=padx, pady=pady, cursor="hand2",
            activebackground=abg, activeforeground="white",
            bd=0, highlightthickness=hlt, highlightbackground=hlt_bg,
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=abg) if str(btn["state"]) != "disabled" else None)
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg) if str(btn["state"]) != "disabled" else None)
        return btn

    def _tr(self, widget, attr: str, key: str) -> None:
        self._translatable.append((widget, attr, key))
        widget.config(**{attr: self.t(key)})

    def _section(self, parent, key: str) -> tuple[tk.Frame, tk.Frame]:
        """Section with left blue accent bar. Returns (outer_to_pack, content_frame)."""
        outer = tk.Frame(parent, bg=C_BG)
        tk.Frame(outer, bg=C_STRIPE, width=3).pack(side=tk.LEFT, fill=tk.Y)
        right = tk.Frame(outer, bg=C_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lbl = tk.Label(right, text=self.t(key), bg=C_BG, fg=C_ACCENT,
                       font=("Segoe UI", 10, "bold"), anchor=tk.W)
        lbl.pack(fill=tk.X, padx=10, pady=(5, 2))
        self._translatable.append((lbl, "text", key))
        content = tk.Frame(right, bg=C_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        return outer, content

    def _entry(self, parent, var: tk.StringVar, **kw) -> tk.Entry:
        return tk.Entry(parent, textvariable=var,
                        bg=C_ENTRY_BG, fg=C_ENTRY_FG, insertbackground=C_ENTRY_FG,
                        font=("Segoe UI", 11), relief="flat", bd=0,
                        highlightthickness=1, highlightbackground=C_SEP,
                        highlightcolor=C_ACCENT,
                        disabledbackground="#1a2030", disabledforeground="#4a5a70",
                        **kw)

    def _chk(self, parent, key: str, var: tk.BooleanVar, cmd=None) -> tk.Checkbutton:
        c = tk.Checkbutton(parent, text=self.t(key), variable=var, command=cmd,
                           bg=C_BG, fg=C_LABEL_FG, selectcolor=C_ENTRY_BG,
                           activebackground=C_BG, activeforeground="#ffffff",
                           font=("Segoe UI", 11))
        self._translatable.append((c, "text", key))
        return c

    def _rb(self, parent, key: str, var: tk.StringVar, value: str, cmd=None) -> tk.Radiobutton:
        r = tk.Radiobutton(parent, text=self.t(key), variable=var, value=value,
                           command=cmd, bg=C_BG, fg=C_LABEL_FG, selectcolor=C_ENTRY_BG,
                           activebackground=C_BG, activeforeground="#ffffff",
                           font=("Segoe UI", 11))
        self._translatable.append((r, "text", key))
        return r

    def _lbl(self, parent, key: str, **kw) -> tk.Label:
        lbl = tk.Label(parent, text=self.t(key), bg=C_BG, fg=C_LABEL_FG,
                       font=("Segoe UI", 11), **kw)
        self._translatable.append((lbl, "text", key))
        return lbl

    # -----------------------------------------------------------------------
    # Build UI
    # -----------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.root.title("BackupOrim")
        self.root.configure(bg=C_BG)
        self.root.minsize(560, 560)
        self.root.geometry("680x760")

        ico = _res("img/orimslav_logo_blue_transparent.ico")
        if ico.exists():
            try:
                self.root.iconbitmap(str(ico))
            except Exception:
                pass

        self._build_header()
        tk.Frame(self.root, bg=C_SEP, height=1).pack(fill=tk.X)

        nb_area = tk.Frame(self.root, bg=C_BG)
        nb_area.pack(fill=tk.BOTH, expand=True)
        self._build_tab_bar(nb_area)

        self._build_tab_main()
        self._build_tab_automation()
        self._build_tab_settings()

        # Status bar
        tk.Frame(self.root, bg=C_SEP, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        sb = tk.Frame(self.root, bg=C_HEADER, pady=4)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_var = tk.StringVar()
        self._status_bar = tk.Label(sb, textvariable=self._status_var,
                                     anchor=tk.W, bg=C_HEADER, fg=C_LABEL_FG,
                                     font=("Segoe UI", 10), padx=12)
        self._status_bar.pack(fill=tk.X)

    # -----------------------------------------------------------------------
    # Custom tab bar — full visual control, no ttk.Notebook quirks
    # -----------------------------------------------------------------------
    def _build_tab_bar(self, parent: tk.Frame) -> None:
        self._active_tab_key: str = "TAB_MAIN"
        self._tab_btns: dict[str, tk.Label] = {}

        bar = tk.Frame(parent, bg=C_HEADER)
        bar.pack(fill=tk.X)

        content = tk.Frame(parent, bg=C_BG)
        content.pack(fill=tk.BOTH, expand=True)

        self._tab_main     = tk.Frame(content, bg=C_BG)
        self._tab_auto     = tk.Frame(content, bg=C_BG)
        self._tab_settings = tk.Frame(content, bg=C_BG)
        self._tab_content_frames = {
            "TAB_MAIN":       self._tab_main,
            "TAB_AUTOMATION": self._tab_auto,
            "TAB_SETTINGS":   self._tab_settings,
        }

        def activate(key: str) -> None:
            self._active_tab_key = key
            for k, btn in self._tab_btns.items():
                btn.config(bg=C_STRIPE if k == key else C_BTN2,
                           fg="#ffffff" if k == key else C_DIM)
            for k, fr in self._tab_content_frames.items():
                if k == key:
                    fr.pack(fill=tk.BOTH, expand=True)
                else:
                    fr.pack_forget()

        self._activate_tab = activate

        # Gap on the left so tabs don't touch the window edge
        tk.Frame(bar, bg=C_HEADER, width=4).pack(side=tk.LEFT)

        for key in ("TAB_MAIN", "TAB_AUTOMATION", "TAB_SETTINGS"):
            btn = tk.Label(
                bar, text=self.t(key),
                bg=C_BTN2, fg=C_DIM,
                font=("Segoe UI", 11, "bold"),
                padx=22, pady=10,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=(0, 3), pady=(6, 0))
            btn.bind("<Button-1>", lambda e, k=key: activate(k))
            btn.bind("<Enter>",    lambda e, b=btn, k=key:
                b.config(bg=C_BTN) if self._active_tab_key != k else None)
            btn.bind("<Leave>",    lambda e, b=btn, k=key:
                b.config(bg=C_BTN2) if self._active_tab_key != k else None)
            self._tab_btns[key] = btn
            self._translatable.append((btn, "text", key))

        activate("TAB_MAIN")

    # -----------------------------------------------------------------------
    # Header — compact: logo+title LEFT | flags+kofi RIGHT
    # -----------------------------------------------------------------------
    def _build_header(self) -> None:
        tk.Frame(self.root, bg=C_STRIPE, height=4).pack(fill=tk.X)

        header = tk.Frame(self.root, bg=C_HEADER)
        header.pack(fill=tk.X)

        # ---- RIGHT side (pack first to anchor) ----
        right_cluster = tk.Frame(header, bg=C_HEADER)
        right_cluster.pack(side=tk.RIGHT, padx=(0, 14), pady=10)

        # Flags
        self._flag_sk_ref = _load_flag(str(_res("img/flag_sk.png")), 20)
        self._flag_en_ref = _load_flag(str(_res("img/flag_en.png")), 20)

        self._flag_sk_btn = tk.Label(right_cluster, image=self._flag_sk_ref, bg=C_HEADER,
                                      cursor="hand2", highlightthickness=2)
        self._flag_sk_btn.pack(side=tk.LEFT, padx=3)
        self._flag_sk_btn.bind("<Button-1>", lambda e: self._set_language("sk"))

        self._flag_en_btn = tk.Label(right_cluster, image=self._flag_en_ref, bg=C_HEADER,
                                      cursor="hand2", highlightthickness=2)
        self._flag_en_btn.pack(side=tk.LEFT, padx=3)
        self._flag_en_btn.bind("<Button-1>", lambda e: self._set_language("en"))

        self._update_flag_highlight()

        # Ko-fi icon
        tk.Frame(right_cluster, bg=C_SEP, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=2, padx=8)
        kofi_ref = _load_flag(str(_res("img/kofi_icon.png")), 24)
        if kofi_ref:
            self._img_refs.append(kofi_ref)
            kofi_lbl = tk.Label(right_cluster, image=kofi_ref, bg=C_HEADER,
                                 cursor="hand2", highlightthickness=0)
            kofi_lbl.pack(side=tk.LEFT, padx=2)
            kofi_lbl.bind("<Button-1>", lambda e: webbrowser.open(KOFI_URL))
            _hover_tint(kofi_lbl, C_HEADER, "#1e3a50")

        # ---- LEFT side: logo + title ----
        left_cluster = tk.Frame(header, bg=C_HEADER)
        left_cluster.pack(side=tk.LEFT, padx=(12, 0), pady=8)

        logo_ref = _load_image(
            str(_res("img/orimslav_logo_blue_transparent.png")),
            height=44,
        )
        if logo_ref:
            self._img_refs.append(logo_ref)
            tk.Label(left_cluster, image=logo_ref, bg=C_HEADER).pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(left_cluster, text="BackupOrim",
                 font=("Segoe UI", 18, "bold"), fg=C_TITLE_FG, bg=C_HEADER).pack(side=tk.LEFT)

    # -----------------------------------------------------------------------
    # Tab — Main
    # -----------------------------------------------------------------------
    def _build_tab_main(self) -> None:
        p = self._tab_main

        # Sources
        s_outer, s_frm = self._section(p, "LBL_SOURCES")
        s_outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        list_wrap = tk.Frame(s_frm, bg=C_BG)
        list_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._src_listbox = tk.Listbox(
            list_wrap, bg=C_LOG_BG, fg=C_LOG_FG, selectbackground=C_BTN,
            selectforeground="#fff", font=("Segoe UI", 11), bd=0, relief="flat",
            highlightthickness=1, highlightbackground=C_SEP, activestyle="none",
            height=4,
        )
        src_sb = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self._src_listbox.yview)
        self._src_listbox.config(yscrollcommand=src_sb.set)
        self._src_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        src_sb.pack(side=tk.LEFT, fill=tk.Y)

        btn_col = tk.Frame(s_frm, bg=C_BG)
        btn_col.pack(side=tk.LEFT, padx=(8, 0), anchor=tk.N)
        b_add = self._make_btn(btn_col, self.t("BTN_ADD_FOLDER"), self._add_source)
        b_add.pack(fill=tk.X, pady=(0, 4))
        self._translatable.append((b_add, "text", "BTN_ADD_FOLDER"))
        b_rm = self._make_btn(btn_col, self.t("BTN_REMOVE_SELECTED"), self._remove_source)
        b_rm.pack(fill=tk.X)
        self._translatable.append((b_rm, "text", "BTN_REMOVE_SELECTED"))

        # Destination
        d_outer, d_frm = self._section(p, "LBL_DESTINATION")
        d_outer.pack(fill=tk.X, padx=8, pady=4)
        dst_row = tk.Frame(d_frm, bg=C_BG)
        dst_row.pack(fill=tk.X)
        self._dst_var = tk.StringVar()
        self._entry(dst_row, self._dst_var).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        b_dst = self._make_btn(dst_row, self.t("BTN_BROWSE"), self._browse_dest)
        b_dst.pack(side=tk.LEFT, padx=(6, 0))
        self._translatable.append((b_dst, "text", "BTN_BROWSE"))

        # Format
        f_outer, f_frm = self._section(p, "LBL_FORMAT")
        f_outer.pack(fill=tk.X, padx=8, pady=4)
        self._fmt_var = tk.StringVar(value="zip")
        rb_kw = dict(variable=self._fmt_var, command=self._on_format_change,
                     bg=C_BG, fg=C_LABEL_FG, selectcolor=C_ENTRY_BG,
                     activebackground=C_BG, activeforeground="#fff", font=("Segoe UI", 11))
        fmt_row = tk.Frame(f_frm, bg=C_BG)
        fmt_row.pack(anchor=tk.W)
        tk.Radiobutton(fmt_row, text="ZIP", value="zip", **rb_kw).pack(side=tk.LEFT, padx=(0, 14))
        tk.Radiobutton(fmt_row, text="RAR", value="rar", **rb_kw).pack(side=tk.LEFT)
        rar_row = tk.Frame(f_frm, bg=C_BG)
        rar_row.pack(fill=tk.X, pady=(4, 0))
        self._lbl(rar_row, "LBL_RAR_PATH").pack(side=tk.LEFT, padx=(0, 6))
        self._rar_var = tk.StringVar()
        self._rar_entry = self._entry(rar_row, self._rar_var)
        self._rar_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        b_rar = self._make_btn(rar_row, self.t("BTN_BROWSE_RAR"), self._browse_rar)
        b_rar.pack(side=tk.LEFT, padx=(6, 0))
        self._translatable.append((b_rar, "text", "BTN_BROWSE_RAR"))

        # Password
        pw_outer, pw_frm = self._section(p, "LBL_PASSWORD")
        pw_outer.pack(fill=tk.X, padx=8, pady=4)
        pwd_row = tk.Frame(pw_frm, bg=C_BG)
        pwd_row.pack(anchor=tk.W)
        self._lbl(pwd_row, "LBL_PASSWORD_ENTRY").pack(side=tk.LEFT, padx=(0, 6))
        self._pwd_var = tk.StringVar()
        self._pwd_entry = self._entry(pwd_row, self._pwd_var, show="*", width=26)
        self._pwd_entry.pack(side=tk.LEFT, ipady=4)
        chk_row = tk.Frame(pw_frm, bg=C_BG)
        chk_row.pack(anchor=tk.W, pady=(4, 0))
        self._show_pwd_var = tk.BooleanVar()
        self._chk(chk_row, "CHK_SHOW_PASSWORD", self._show_pwd_var, self._toggle_show_password).pack(side=tk.LEFT)
        self._remember_pwd_var = tk.BooleanVar()
        self._chk(chk_row, "CHK_REMEMBER_PASSWORD", self._remember_pwd_var, self._on_remember_pwd_toggle).pack(side=tk.LEFT, padx=(14, 0))
        self._pwd_warn_lbl = tk.Label(pw_frm, text=self.t("WARN_PASSWORD_PLAINTEXT"),
                                       bg=C_BG, fg=C_LOG_ERR, wraplength=560,
                                       font=("Segoe UI", 9, "italic"), anchor=tk.W)
        self._translatable.append((self._pwd_warn_lbl, "text", "WARN_PASSWORD_PLAINTEXT"))

        # ---- Action row ----
        tk.Frame(p, bg=C_SEP, height=1).pack(fill=tk.X, padx=8, pady=(6, 0))
        act_row = tk.Frame(p, bg=C_BG)
        act_row.pack(fill=tk.X, padx=8, pady=6)

        b_save = self._make_btn(act_row, self.t("BTN_SAVE_SETTINGS"), self._save_settings, outline=True)
        b_save.pack(side=tk.LEFT)
        self._translatable.append((b_save, "text", "BTN_SAVE_SETTINGS"))

        self._btn_run = self._make_btn(act_row, self.t("BTN_RUN_BACKUP"), self._run_backup, primary=True)
        self._btn_run.pack(side=tk.RIGHT)
        self._translatable.append((self._btn_run, "text", "BTN_RUN_BACKUP"))

        self._shutdown_after_var = tk.BooleanVar()
        chk_sd = tk.Checkbutton(act_row, text=self.t("CHK_SHUTDOWN_AFTER"),
                                 variable=self._shutdown_after_var,
                                 bg=C_BG, fg=C_LABEL_FG, selectcolor=C_ENTRY_BG,
                                 activebackground=C_BG, activeforeground=C_ENTRY_FG,
                                 font=("Segoe UI", 10), bd=0)
        chk_sd.pack(side=tk.RIGHT, padx=(0, 16))
        self._translatable.append((chk_sd, "text", "CHK_SHUTDOWN_AFTER"))

        # Progress bar — shown only during backup
        pb_row = tk.Frame(p, bg=C_BG)
        pb_row.pack(fill=tk.X, padx=8, pady=(2, 0))
        self._progress_lbl_var = tk.StringVar()
        self._progress_lbl = tk.Label(pb_row, textvariable=self._progress_lbl_var,
                                      bg=C_BG, fg=C_DIM, font=("Segoe UI", 9),
                                      anchor=tk.W, width=28)
        self._progress_bar = ttk.Progressbar(pb_row, mode="indeterminate",
                                              style="Backup.Horizontal.TProgressbar")
        # neither packed until backup starts

        # Log
        tk.Label(p, text="Log", bg=C_BG, fg=C_LABEL_FG,
                 font=("Segoe UI", 10, "bold"), anchor=tk.W).pack(fill=tk.X, padx=12, pady=(4, 0))
        log_wrap = tk.Frame(p, bg=C_LOG_BG, highlightthickness=1, highlightbackground=C_SEP)
        log_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._log_widget = tk.Text(
            log_wrap, state="disabled", wrap=tk.WORD, font=("Consolas", 11),
            bg=C_LOG_BG, fg=C_LOG_FG, relief="flat", padx=10, pady=8, bd=0,
            selectbackground=C_BTN,
        )
        log_sb = ttk.Scrollbar(log_wrap, orient=tk.VERTICAL, command=self._log_widget.yview)
        self._log_widget.config(yscrollcommand=log_sb.set)
        self._log_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_widget.tag_configure("ok",   foreground=C_LOG_OK)
        self._log_widget.tag_configure("err",  foreground=C_LOG_ERR)
        self._log_widget.tag_configure("info", foreground=C_LOG_INFO)
        self._log_widget.tag_configure("ts",   foreground=C_LOG_TS)

    # -----------------------------------------------------------------------
    # Tab — Automation
    # -----------------------------------------------------------------------
    def _build_tab_automation(self) -> None:
        p = self._tab_auto

        # Cleanup
        c_outer, c_frm = self._section(p, "LBL_CLEANUP")
        c_outer.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._cleanup_var = tk.StringVar(value="none")
        self._rb(c_frm, "RB_CLEANUP_NONE", self._cleanup_var, "none",
                 self._on_cleanup_change).pack(anchor=tk.W)
        count_row = tk.Frame(c_frm, bg=C_BG)
        count_row.pack(anchor=tk.W, pady=(2, 0))
        self._rb(count_row, "RB_CLEANUP_COUNT", self._cleanup_var, "count",
                 self._on_cleanup_change).pack(side=tk.LEFT)
        self._lbl(count_row, "LBL_KEEP_COUNT").pack(side=tk.LEFT, padx=(10, 4))
        self._keep_count_var = tk.StringVar(value="5")
        self._keep_count_entry = self._entry(count_row, self._keep_count_var, width=5)
        self._keep_count_entry.pack(side=tk.LEFT, ipady=4)
        days_row = tk.Frame(c_frm, bg=C_BG)
        days_row.pack(anchor=tk.W, pady=(2, 0))
        self._rb(days_row, "RB_CLEANUP_DAYS", self._cleanup_var, "days",
                 self._on_cleanup_change).pack(side=tk.LEFT)
        self._lbl(days_row, "LBL_KEEP_DAYS").pack(side=tk.LEFT, padx=(10, 4))
        self._keep_days_var = tk.StringVar(value="30")
        self._keep_days_entry = self._entry(days_row, self._keep_days_var, width=5)
        self._keep_days_entry.pack(side=tk.LEFT, ipady=4)

        # Exclude patterns
        e_outer, e_frm = self._section(p, "LBL_EXCLUDE")
        e_outer.pack(fill=tk.BOTH, padx=8, pady=4)
        excl_wrap = tk.Frame(e_frm, bg=C_LOG_BG)
        excl_wrap.pack(fill=tk.BOTH, expand=True)
        self._excl_text = tk.Text(excl_wrap, height=6, wrap=tk.NONE,
                                   bg=C_LOG_BG, fg=C_LOG_FG, insertbackground=C_LOG_FG,
                                   font=("Consolas", 11), relief="flat", padx=6, pady=4, bd=0)
        excl_sb = ttk.Scrollbar(excl_wrap, orient=tk.VERTICAL, command=self._excl_text.yview)
        self._excl_text.config(yscrollcommand=excl_sb.set)
        self._excl_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        excl_sb.pack(side=tk.LEFT, fill=tk.Y)

        # Autostart
        a_outer, a_frm = self._section(p, "LBL_AUTOSTART")
        a_outer.pack(fill=tk.X, padx=8, pady=4)

        self._logon_var = tk.BooleanVar()
        self._chk(a_frm, "CHK_LOGON", self._logon_var, self._on_logon_toggle).pack(anchor=tk.W)

        sched_row = tk.Frame(a_frm, bg=C_BG)
        sched_row.pack(anchor=tk.W, fill=tk.X, pady=(2, 0))
        self._sched_var = tk.BooleanVar()
        self._chk(sched_row, "CHK_SCHEDULED", self._sched_var, self._on_sched_toggle).pack(side=tk.LEFT)
        self._lbl(sched_row, "LBL_SCHEDULED_TIME").pack(side=tk.LEFT, padx=(12, 4))
        self._sched_hh = tk.StringVar(value="17")
        self._sched_mm = tk.StringVar(value="00")
        spin_kw = dict(bg=C_ENTRY_BG, fg=C_ENTRY_FG, insertbackground=C_ENTRY_FG,
                       relief="flat", bd=0, font=("Segoe UI", 11), buttonbackground=C_BTN2,
                       highlightthickness=1, highlightbackground=C_SEP)
        tk.Spinbox(sched_row, textvariable=self._sched_hh, from_=0, to=23,
                   width=3, format="%02.0f", **spin_kw).pack(side=tk.LEFT)
        tk.Label(sched_row, text=":", bg=C_BG, fg=C_LABEL_FG, font=("Segoe UI", 11)).pack(side=tk.LEFT)
        tk.Spinbox(sched_row, textvariable=self._sched_mm, from_=0, to=59,
                   width=3, format="%02.0f", **spin_kw).pack(side=tk.LEFT)
        self._lbl(sched_row, "LBL_SCHEDULED_FREQ").pack(side=tk.LEFT, padx=(10, 4))
        self._sched_freq_var = tk.StringVar()
        self._freq_combo = ttk.Combobox(sched_row, textvariable=self._sched_freq_var,
                                         state="readonly", width=16)
        self._freq_combo.pack(side=tk.LEFT)
        self._freq_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_freq_changed())
        self._update_freq_values()

        self._sched_days_row = tk.Frame(a_frm, bg=C_BG)
        self._lbl(self._sched_days_row, "LBL_SCHEDULED_DAYS").pack(side=tk.LEFT, padx=(22, 6))
        _day_codes = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        self._sched_day_vars: dict[str, tk.BooleanVar] = {}
        self._sched_day_chks: list[tuple[tk.Checkbutton, str]] = []
        for code in _day_codes:
            var = tk.BooleanVar(value=(code == "MON"))
            self._sched_day_vars[code] = var
            chk = tk.Checkbutton(self._sched_days_row, variable=var,
                                  bg=C_BG, fg=C_LABEL_FG, selectcolor=C_ENTRY_BG,
                                  activebackground=C_BG, activeforeground=C_ENTRY_FG,
                                  font=("Segoe UI", 10), bd=0, padx=2)
            chk.pack(side=tk.LEFT)
            self._sched_day_chks.append((chk, f"DAY_{code}"))
        self._update_day_labels()
        self._on_freq_changed()

        # ---- Action row ----
        tk.Frame(p, bg=C_SEP, height=1).pack(fill=tk.X, padx=8, pady=(8, 0))
        auto_act_row = tk.Frame(p, bg=C_BG)
        auto_act_row.pack(fill=tk.X, padx=8, pady=6)
        b_save_auto = self._make_btn(auto_act_row, self.t("BTN_SAVE_SETTINGS"),
                                     self._save_settings, outline=True)
        b_save_auto.pack(side=tk.LEFT)
        self._translatable.append((b_save_auto, "text", "BTN_SAVE_SETTINGS"))

    # -----------------------------------------------------------------------
    # Tab — Settings
    # -----------------------------------------------------------------------
    def _build_tab_settings(self) -> None:
        p = self._tab_settings

        # Tray
        t_outer, t_frm = self._section(p, "LBL_TRAY")
        t_outer.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._minimize_to_tray_var = tk.BooleanVar()
        self._chk(t_frm, "CHK_MINIMIZE_TO_TRAY", self._minimize_to_tray_var).pack(anchor=tk.W)
        self._start_min_var = tk.BooleanVar()
        self._chk(t_frm, "CHK_START_MINIMIZED", self._start_min_var).pack(anchor=tk.W, pady=(4, 0))

        # Notifications
        n_outer, n_frm = self._section(p, "LBL_NOTIFICATIONS")
        n_outer.pack(fill=tk.X, padx=8, pady=4)
        self._notify_success_var = tk.BooleanVar()
        self._chk(n_frm, "CHK_NOTIFY_SUCCESS", self._notify_success_var).pack(anchor=tk.W)
        self._notify_fail_var = tk.BooleanVar(value=True)
        self._chk(n_frm, "CHK_NOTIFY_FAILURE", self._notify_fail_var).pack(anchor=tk.W, pady=(4, 0))

        # About
        ab_outer, ab_frm = self._section(p, "LBL_ABOUT")
        ab_outer.pack(fill=tk.X, padx=8, pady=4)

        lbl_ver = tk.Label(ab_frm, text=self.t("LBL_APP_VERSION"),
                            bg=C_BG, fg=C_TITLE_FG, font=("Segoe UI", 13, "bold"))
        lbl_ver.pack(anchor=tk.W, pady=(0, 6))
        self._translatable.append((lbl_ver, "text", "LBL_APP_VERSION"))

        b_log = self._make_btn(ab_frm, self.t("BTN_OPEN_LOG"),
                                lambda: os.startfile(str(app_paths.app_data_dir())))
        b_log.pack(anchor=tk.W, pady=(0, 8))
        self._translatable.append((b_log, "text", "BTN_OPEN_LOG"))

        # Ko-fi + GitHub
        support_row = tk.Frame(ab_frm, bg=C_BG)
        support_row.pack(anchor=tk.W, pady=(0, 4))

        kofi_btn = tk.Button(support_row, text="☕  Ko-fi",
                              command=lambda: webbrowser.open(KOFI_URL),
                              font=("Segoe UI", 11, "bold"), bg=C_KOFI, fg="white",
                              relief="flat", padx=16, pady=7, cursor="hand2",
                              activebackground="#1a8fbe", activeforeground="white", bd=0)
        kofi_btn.pack(side=tk.LEFT, padx=(0, 8))
        kofi_btn.bind("<Enter>", lambda e: kofi_btn.config(bg="#1a8fbe"))
        kofi_btn.bind("<Leave>", lambda e: kofi_btn.config(bg=C_KOFI))

        gh_btn = tk.Button(support_row, text="  GitHub",
                            command=lambda: webbrowser.open(GITHUB_URL),
                            font=("Segoe UI", 11), bg=C_GITHUB, fg="white",
                            relief="flat", padx=16, pady=7, cursor="hand2",
                            activebackground="#3a4550", activeforeground="white", bd=0)
        gh_btn.pack(side=tk.LEFT)
        gh_btn.bind("<Enter>", lambda e: gh_btn.config(bg="#3a4550"))
        gh_btn.bind("<Leave>", lambda e: gh_btn.config(bg=C_GITHUB))

        tk.Label(p, text="© ORIMSLAV", bg=C_BG, fg="#3a4a66",
                 font=("Segoe UI", 10)).pack(side=tk.BOTTOM, pady=10)

    # -----------------------------------------------------------------------
    # Config ↔ UI
    # -----------------------------------------------------------------------
    def _apply_config_to_ui(self) -> None:
        c = self.cfg
        for s in c.get("sources", []):
            self._src_listbox.insert(tk.END, s)
        self._dst_var.set(c.get("destination", ""))
        self._fmt_var.set(c.get("format", "zip"))
        self._rar_var.set(c.get("rar_path", ""))
        self._on_format_change()
        self._remember_pwd_var.set(c.get("remember_password", False))
        if c.get("remember_password") and c.get("password"):
            self._pwd_var.set(c["password"])
        self._on_remember_pwd_toggle()
        self._cleanup_var.set(c.get("cleanup", "none"))
        self._keep_count_var.set(c.get("keep_count", "5"))
        self._keep_days_var.set(c.get("keep_days", "30"))
        self._on_cleanup_change()
        patterns = c.get("exclude_patterns", cfg_module.DEFAULT_CONFIG["exclude_patterns"])
        self._excl_text.insert("1.0", "\n".join(patterns))
        try:
            hh, mm = c.get("scheduled_time", "17:00").split(":")
            self._sched_hh.set(hh); self._sched_mm.set(mm)
        except ValueError:
            pass
        freq_map = {"daily": self.t("FREQ_DAILY"), "weekdays": self.t("FREQ_WEEKDAYS"),
                    "weekly": self.t("FREQ_WEEKLY")}
        self._sched_freq_var.set(freq_map.get(c.get("scheduled_frequency", "daily"), self.t("FREQ_DAILY")))
        saved_days = c.get("scheduled_days", ["MON"])
        for code, var in self._sched_day_vars.items():
            var.set(code in saved_days)
        self._on_freq_changed()
        self._minimize_to_tray_var.set(c.get("minimize_to_tray_on_close", True))
        self._start_min_var.set(c.get("start_minimized", False))
        self._notify_success_var.set(c.get("notify_on_success", False))
        self._notify_fail_var.set(c.get("notify_on_failure", True))

    def _collect_config_from_ui(self) -> dict[str, Any]:
        c = dict(self.cfg)
        c["sources"] = list(self._src_listbox.get(0, tk.END))
        c["destination"] = self._dst_var.get().strip()
        c["format"] = self._fmt_var.get()
        c["rar_path"] = self._rar_var.get().strip()
        c["remember_password"] = self._remember_pwd_var.get()
        c["password"] = self._pwd_var.get() if self._remember_pwd_var.get() else ""
        c["cleanup"] = self._cleanup_var.get()
        c["keep_count"] = self._keep_count_var.get().strip()
        c["keep_days"] = self._keep_days_var.get().strip()
        excl = self._excl_text.get("1.0", tk.END).strip()
        c["exclude_patterns"] = [ln.strip() for ln in excl.splitlines() if ln.strip()]
        c["autostart_logon"] = self._logon_var.get()
        c["autostart_scheduled"] = self._sched_var.get()
        c["scheduled_time"] = f"{int(self._sched_hh.get()):02d}:{int(self._sched_mm.get()):02d}"
        freq_rmap = {self.t("FREQ_DAILY"): "daily", self.t("FREQ_WEEKDAYS"): "weekdays",
                     self.t("FREQ_WEEKLY"): "weekly"}
        c["scheduled_frequency"] = freq_rmap.get(self._sched_freq_var.get(), "daily")
        c["scheduled_days"] = [code for code, var in self._sched_day_vars.items() if var.get()] or ["MON"]
        c["minimize_to_tray_on_close"] = self._minimize_to_tray_var.get()
        c["start_minimized"] = self._start_min_var.get()
        c["notify_on_success"] = self._notify_success_var.get()
        c["notify_on_failure"] = self._notify_fail_var.get()
        c["shutdown_after_backup"] = self._shutdown_after_var.get()
        c["language"] = self.t.lang
        return c

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------
    def _add_source(self) -> None:
        f = filedialog.askdirectory(title=self.t("DLG_SELECT_SOURCE"))
        if f and f not in list(self._src_listbox.get(0, tk.END)):
            self._src_listbox.insert(tk.END, f)

    def _remove_source(self) -> None:
        sel = self._src_listbox.curselection()
        if sel:
            self._src_listbox.delete(sel[0])

    def _browse_dest(self) -> None:
        f = filedialog.askdirectory(title=self.t("DLG_SELECT_DEST"))
        if f:
            self._dst_var.set(f)

    def _browse_rar(self) -> None:
        f = filedialog.askopenfilename(
            title=self.t("DLG_SELECT_RAR"),
            filetypes=[(self.t("DLG_RAR_FILTER"), "*.exe"), ("All", "*.*")],
        )
        if f:
            self._rar_var.set(f)

    def _on_format_change(self) -> None:
        self._rar_entry.config(state="normal" if self._fmt_var.get() == "rar" else "disabled")

    def _toggle_show_password(self) -> None:
        self._pwd_entry.config(show="" if self._show_pwd_var.get() else "*")

    def _on_remember_pwd_toggle(self) -> None:
        if self._remember_pwd_var.get():
            self._pwd_warn_lbl.pack(anchor=tk.W, pady=(4, 0))
        else:
            self._pwd_warn_lbl.pack_forget()

    def _on_cleanup_change(self) -> None:
        v = self._cleanup_var.get()
        self._keep_count_entry.config(state="normal" if v == "count" else "disabled")
        self._keep_days_entry.config(state="normal" if v == "days" else "disabled")

    def _set_language(self, lang: str) -> None:
        self.t.set_language(lang)
        self._refresh_all_text()
        self._update_flag_highlight()

    def _update_flag_highlight(self) -> None:
        if self.t.lang == "sk":
            self._flag_sk_btn.config(highlightbackground=C_STRIPE)
            self._flag_en_btn.config(highlightbackground=C_HEADER)
        else:
            self._flag_sk_btn.config(highlightbackground=C_HEADER)
            self._flag_en_btn.config(highlightbackground=C_STRIPE)

    def _refresh_all_text(self) -> None:
        self.root.title("BackupOrim")
        for widget, attr, key in self._translatable:
            try:
                widget.config(**{attr: self.t(key)})
            except Exception:
                pass
        self._update_freq_values()

    def _update_freq_values(self) -> None:
        vals = [self.t("FREQ_DAILY"), self.t("FREQ_WEEKDAYS"), self.t("FREQ_WEEKLY")]
        self._freq_combo.config(values=vals)
        if self._sched_freq_var.get() not in vals:
            self._sched_freq_var.set(vals[0])
        self._update_day_labels()

    def _update_day_labels(self) -> None:
        for chk, key in getattr(self, "_sched_day_chks", []):
            chk.config(text=self.t(key))

    def _on_freq_changed(self) -> None:
        if not hasattr(self, "_sched_days_row"):
            return
        freq_rmap = {self.t("FREQ_DAILY"): "daily", self.t("FREQ_WEEKDAYS"): "weekdays",
                     self.t("FREQ_WEEKLY"): "weekly"}
        if freq_rmap.get(self._sched_freq_var.get()) == "weekly":
            self._sched_days_row.pack(anchor=tk.W, fill=tk.X, pady=(2, 0))
        else:
            self._sched_days_row.pack_forget()

    def _on_logon_toggle(self) -> None:
        self._set_autostart(self._logon_var.get(),
            lambda: autostart.enable_logon(self._pythonw(), self._script_path()),
            autostart.disable_logon)

    def _on_sched_toggle(self) -> None:
        self._set_autostart(self._sched_var.get(), self._enable_scheduled,
                            autostart.disable_scheduled)

    def _enable_scheduled(self) -> None:
        """(Re)create the Windows scheduled task from the current UI values."""
        freq_rmap = {self.t("FREQ_DAILY"): "daily", self.t("FREQ_WEEKDAYS"): "weekdays",
                     self.t("FREQ_WEEKLY"): "weekly"}
        freq = freq_rmap.get(self._sched_freq_var.get(), "daily")
        days = [code for code, var in self._sched_day_vars.items() if var.get()] or ["MON"]
        autostart.enable_scheduled(
            self._pythonw(), self._script_path(),
            int(self._sched_hh.get()), int(self._sched_mm.get()),
            freq, days if freq == "weekly" else None,
        )

    def _set_autostart(self, enabled: bool, enable_fn, disable_fn) -> None:
        try:
            enable_fn() if enabled else disable_fn()
        except (OSError, RuntimeError, ValueError) as e:
            messagebox.showerror(self.t("DLG_ERROR_TITLE"),
                                  self.t("ERR_AUTOSTART_FAILED").format(err=e))
        self._refresh_autostart_state()

    def _refresh_autostart_state(self) -> None:
        for var, fn in [(self._logon_var,  autostart.is_logon_enabled),
                        (self._sched_var,  autostart.is_scheduled_enabled)]:
            try:
                var.set(fn())
            except Exception:
                pass

    def _pythonw(self) -> str:
        if getattr(sys, "frozen", False):
            return sys.executable  # the .exe itself accepts --autorun
        return str(Path(sys.executable).with_name("pythonw.exe"))

    def _script_path(self) -> str:
        if getattr(sys, "frozen", False):
            return ""  # exe is self-contained; no separate script needed
        return str(Path(__file__).resolve())

    # -----------------------------------------------------------------------
    # Save / Validate
    # -----------------------------------------------------------------------
    def _save_settings(self) -> None:
        self.cfg = self._collect_config_from_ui()
        try:
            to_save = {k: v for k, v in self.cfg.items() if k != "shutdown_after_backup"}
            cfg_module.save_config(to_save)
            self._log(self.t("LOG_SETTINGS_SAVED"), "ok")
        except OSError as e:
            messagebox.showerror(self.t("DLG_ERROR_TITLE"), str(e))
            return
        # Keep the Windows scheduled task in sync with the just-saved time /
        # frequency / days. Without this, changing the time after the checkbox
        # was already ticked would leave the task running at its old time.
        if self._sched_var.get():
            try:
                self._enable_scheduled()
                self._log(self.t("LOG_SCHEDULED_UPDATED").format(
                    time=f"{int(self._sched_hh.get()):02d}:{int(self._sched_mm.get()):02d}"), "info")
            except (OSError, RuntimeError, ValueError) as e:
                messagebox.showerror(self.t("DLG_ERROR_TITLE"),
                                     self.t("ERR_AUTOSTART_FAILED").format(err=e))

    def _validate(self) -> str | None:
        sources = list(self._src_listbox.get(0, tk.END))
        if not sources:
            return self.t("ERR_NO_SOURCE")
        dest = self._dst_var.get().strip()
        if not dest:
            return self.t("ERR_NO_DEST")
        for s in sources:
            try:
                Path(dest).resolve().relative_to(Path(s).resolve())
                return self.t("ERR_DEST_IN_SOURCE")
            except ValueError:
                pass
        if self._fmt_var.get() == "rar" and not Path(self._rar_var.get().strip()).exists():
            return self.t("ERR_RAR_NOT_FOUND").format(path=self._rar_var.get().strip())
        if self._cleanup_var.get() == "count":
            try:
                if int(self._keep_count_var.get()) <= 0: raise ValueError
            except ValueError:
                return self.t("ERR_CLEANUP_COUNT")
        if self._cleanup_var.get() == "days":
            try:
                if int(self._keep_days_var.get()) <= 0: raise ValueError
            except ValueError:
                return self.t("ERR_CLEANUP_DAYS")
        return None

    # -----------------------------------------------------------------------
    # Backup execution
    # -----------------------------------------------------------------------
    def _run_backup(self) -> None:
        if self._backup_running:
            return
        err = self._validate()
        if err:
            messagebox.showerror(self.t("DLG_VALIDATION_TITLE"), err)
            return
        self._activate_tab("TAB_MAIN")
        self._btn_run.config(state="disabled", bg="#1a3060")
        self._backup_running = True
        self._progress_lbl_var.set("")
        self._progress_lbl.pack(side=tk.LEFT, pady=(0, 3))
        self._progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        self._progress_bar.start(12)
        threading.Thread(target=self._backup_thread,
                         args=(self._collect_config_from_ui(),), daemon=True).start()

    def _trigger_backup_from_tray(self) -> None:
        self.root.after(0, self._run_backup)

    def _backup_thread(self, c: dict[str, Any]) -> None:
        start = time.time()
        self._log(self.t("LOG_BACKUP_START"), "info")
        logger.info("Backup started")
        dest, fmt = c["destination"], c["format"]
        rar_exe = c["rar_path"]
        password = c.get("password") or None
        exclude = c.get("exclude_patterns", [])
        cleanup_mode = c["cleanup"]
        keep_count = int(c.get("keep_count") or 5)
        keep_days  = int(c.get("keep_days") or 30)
        try:
            Path(dest).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._finish_backup(False, str(e), time.time() - start, c)
            return
        total = len(c["sources"])
        all_ok, last_archive = True, ""
        for idx, source in enumerate(c["sources"]):
            src_path = Path(source)
            basename = src_path.name or "drive"
            self.root.after(0, self._progress_lbl_var.set,
                            f"{basename}  ({idx + 1}/{total})")
            if not src_path.exists():
                self._log(self.t("LOG_SKIPPING_MISSING").format(path=source), "err")
                self.root.after(0, self._progress_bar.config, {"value": idx + 1})
                continue
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            archive_name = f"{basename}_{ts}.{fmt}"
            archive_path = str(Path(dest) / archive_name)
            self._log(self.t("LOG_ARCHIVING").format(src=source, dst=archive_name), "info")
            try:
                if fmt == "zip":
                    backup_core.make_zip(source, archive_path, lambda m: self._log(m, "info"), password, exclude)
                else:
                    backup_core.make_rar(source, archive_path, rar_exe, password, exclude)
                backup_core.verify_archive(archive_path, fmt, rar_exe)
                self._log(self.t("LOG_INTEGRITY_OK").format(name=archive_name), "ok")
                backup_core.cleanup_backups(dest, basename, fmt, cleanup_mode,
                                             keep_count, keep_days, lambda m: self._log(m, "info"))
                last_archive = archive_path
            except Exception as e:
                self._log(self.t("LOG_BACKUP_FAILED").format(err=e), "err")
                logger.error("Backup failed for %s: %s", source, e)
                all_ok = False
        duration = time.time() - start
        if all_ok and last_archive:
            self._finish_backup(True, f"{Path(last_archive).name} ({_fmt_size(last_archive)})", duration, c)
        else:
            self._finish_backup(False, "See log for details", duration, c)

    def _finish_backup(self, success: bool, message: str, duration: float, c: dict) -> None:
        cfg_module.save_last_run("ok" if success else "error", message, duration)
        if success:
            self._log(self.t("LOG_BACKUP_DONE"), "ok")
            if c.get("notify_on_success"):
                notifications.notify_success(self.t("TOAST_SUCCESS_TITLE"), message)
            if c.get("shutdown_after_backup"):
                self._log(self.t("LOG_SHUTDOWN_SCHEDULED"), "info")
                import subprocess
                subprocess.Popen(["shutdown", "/s", "/t", "60"])
        else:
            if c.get("notify_on_failure"):
                notifications.notify_failure(self.t("TOAST_FAILURE_TITLE"), message)
        self.root.after(0, self._on_backup_finished)

    def _on_backup_finished(self) -> None:
        self._backup_running = False
        self._btn_run.config(state="normal", bg=C_BTN)
        self._progress_bar.stop()
        self._progress_bar.pack_forget()
        self._progress_lbl.pack_forget()
        self._progress_lbl_var.set("")
        self._update_status_bar()

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    def _log(self, message: str, hint: str = "") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(message)
        self.root.after(0, self._append_log, f"[{ts}] ", message + "\n", hint)

    def _append_log(self, ts_part: str, msg_part: str, hint: str) -> None:
        self._log_widget.config(state="normal")
        self._log_widget.insert(tk.END, ts_part, "ts")
        m = msg_part.lower()
        if hint in ("ok", "err", "info"):
            tag = hint
        elif any(w in m for w in ("error", "chyba", "fail", "zlyhala", "corrupt")):
            tag = "err"
        elif any(w in m for w in ("ok", "done", "complete", "dokončen", "uložen", "integrity ok")):
            tag = "ok"
        else:
            tag = "info"
        self._log_widget.insert(tk.END, msg_part, tag)
        self._log_widget.see(tk.END)
        self._log_widget.config(state="disabled")

    # -----------------------------------------------------------------------
    # Status bar
    # -----------------------------------------------------------------------
    def _update_status_bar(self) -> None:
        last = cfg_module.load_last_run()
        if not last:
            self._status_var.set(self.t("STATUS_NEVER"))
            self._status_bar.config(fg=C_LABEL_FG)
            return
        try:
            dt = datetime.fromisoformat(last["timestamp"])
            dt_str = dt.strftime("%d.%m.%Y %H:%M") if self.t.lang == "sk" else dt.strftime("%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            dt_str = "?"
        if last.get("result") == "ok":
            self._status_var.set(self.t("STATUS_OK").format(dt=dt_str, size=last.get("message", "")))
            self._status_bar.config(fg=C_LOG_OK)
        else:
            self._status_var.set(self.t("STATUS_ERROR").format(dt=dt_str, msg=last.get("message", "")))
            self._status_bar.config(fg=C_LOG_ERR)

    # -----------------------------------------------------------------------
    # Window / tray lifecycle
    # -----------------------------------------------------------------------
    def _poll_show_request(self) -> None:
        if single_instance.poll_show_request():
            self._show_window()
        if single_instance.poll_backup_request():
            self._run_backup()
        self._poll_after_id = self.root.after(500, self._poll_show_request)

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_close(self) -> None:
        if self._collect_config_from_ui().get("minimize_to_tray_on_close"):
            self.root.withdraw()
        else:
            self._quit_app()

    def _quit_app(self) -> None:
        if hasattr(self, "_poll_after_id"):
            try:
                self.root.after_cancel(self._poll_after_id)
            except Exception:
                pass
        if self._tray:
            self._tray.stop()
        single_instance.release()
        self.root.destroy()


# ---------------------------------------------------------------------------
# --autorun headless mode
# ---------------------------------------------------------------------------
def run_autorun(shutdown_after: bool = False) -> None:
    c = cfg_module.load_config()
    if not c.get("sources"):
        cfg_module.save_last_run("error", "No sources configured", 0)
        sys.exit(1)
    if not c.get("destination"):
        cfg_module.save_last_run("error", "No destination configured", 0)
        sys.exit(1)
    start = time.time()
    def log(msg):
        logger.info(msg)
    dest, fmt = c["destination"], c.get("format", "zip")
    rar_exe = c.get("rar_path", "")
    password = c.get("password") or None
    exclude = c.get("exclude_patterns", [])
    cleanup_mode = c.get("cleanup", "none")
    keep_count, keep_days = int(c.get("keep_count") or 5), int(c.get("keep_days") or 30)
    try:
        Path(dest).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        cfg_module.save_last_run("error", f"Destination unavailable: {e}", time.time() - start)
        if c.get("notify_on_failure"):
            notifications.notify_failure("Backup failed", f"Destination unavailable: {dest}")
        sys.exit(1)
    last_archive = ""
    for source in c["sources"]:
        src_path = Path(source)
        if not src_path.exists():
            logger.warning("Source missing: %s", source); continue
        basename = src_path.name or "drive"
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_path = str(Path(dest) / f"{basename}_{ts}.{fmt}")
        try:
            if fmt == "zip":
                backup_core.make_zip(source, archive_path, log, password, exclude)
            else:
                backup_core.make_rar(source, archive_path, rar_exe, password, exclude)
            backup_core.verify_archive(archive_path, fmt, rar_exe)
            backup_core.cleanup_backups(dest, basename, fmt, cleanup_mode, keep_count, keep_days, log)
            last_archive = archive_path
        except Exception as e:
            print(str(e), file=sys.stderr)
            cfg_module.save_last_run("error", str(e), time.time() - start)
            sys.exit(1)
    duration = time.time() - start
    if last_archive:
        msg = f"{Path(last_archive).name} ({_fmt_size(last_archive)})"
        cfg_module.save_last_run("ok", msg, duration)
        print(last_archive)
        if c.get("notify_on_success"):
            notifications.notify_success("Backup complete", msg)
        if shutdown_after:
            import subprocess
            logger.info("Backup done — shutting down in 60 s. To cancel: shutdown /a")
            subprocess.Popen(["shutdown", "/s", "/t", "60"])
        sys.exit(0)
    else:
        cfg_module.save_last_run("error", "No sources backed up", duration); sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    args = sys.argv[1:]
    autorun        = "--autorun" in args
    shutdown_after = "--shutdown-after" in args
    start_minimized = "--minimized" in args

    if (autorun or shutdown_after) and not start_minimized:
        if not single_instance.acquire():
            single_instance.signal_backup_request()
            sys.exit(0)
        atexit.register(single_instance.release)
        run_autorun(shutdown_after=shutdown_after)
        return

    if not single_instance.acquire():
        single_instance.signal_show_window(); sys.exit(0)
    atexit.register(single_instance.release)

    loaded_cfg = cfg_module.load_config()
    if start_minimized:
        loaded_cfg["start_minimized"] = True

    translator = i18n.Translator(loaded_cfg.get("language", "sk"))
    root = tk.Tk()
    try:
        app = BackupApp(root, translator, loaded_cfg)
        if autorun:
            root.after(3000, app._run_backup)
    except Exception:
        import traceback
        (app_paths.app_data_dir() / "startup_error.txt").write_text(
            traceback.format_exc(), encoding="utf-8")
        raise
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


def _guarded_main() -> None:
    import traceback
    err_path = app_paths.app_data_dir() / "startup_error.txt"
    try:
        main()
    except Exception:
        try:
            err_path.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("BackupOrim — startup error", traceback.format_exc())
        except Exception:
            pass


if __name__ == "__main__":
    _guarded_main()
