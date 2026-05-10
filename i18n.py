"""Bilingual EN/SK string tables and Translator class."""
from __future__ import annotations

LANGUAGES: dict[str, dict[str, str]] = {
    "sk": {
        # Window / tabs
        "WINDOW_TITLE": "BackupOrim",
        "TAB_MAIN": "Hlavné",
        "TAB_AUTOMATION": "Automatizácia",
        "TAB_SETTINGS": "Nastavenia",
        # Source folders
        "LBL_SOURCES": "Zdrojové priečinky",
        "BTN_ADD_FOLDER": "Pridať priečinok…",
        "BTN_REMOVE_SELECTED": "Odstrániť vybraný",
        # Destination
        "LBL_DESTINATION": "Cieľový priečinok",
        "BTN_BROWSE": "Prehľadávať…",
        # Format
        "LBL_FORMAT": "Formát archívu",
        "LBL_RAR_PATH": "Cesta k rar.exe:",
        "BTN_BROWSE_RAR": "…",
        # Password
        "LBL_PASSWORD": "Heslo (voliteľné)",
        "LBL_PASSWORD_ENTRY": "Heslo:",
        "CHK_SHOW_PASSWORD": "Zobraziť heslo",
        "CHK_REMEMBER_PASSWORD": "Zapamätať heslo",
        "WARN_PASSWORD_PLAINTEXT": "Heslo bude uložené v otvorenej forme v konfiguračnom súbore.",
        # Action buttons
        "BTN_SAVE_SETTINGS": "Uložiť nastavenia",
        "BTN_RUN_BACKUP": "▶   Vytvoriť zálohu",
        "CHK_SHUTDOWN_AFTER": "Vypnúť PC po zálohe",
        "LOG_SHUTDOWN_SCHEDULED": "Záloha dokončená — PC sa vypne o 60 sekúnd. Zrušiť: shutdown /a",
        # Cleanup
        "LBL_CLEANUP": "Čistenie starých záloh",
        "RB_CLEANUP_NONE": "Žiadne",
        "RB_CLEANUP_COUNT": "Ponechať posledných N záloh",
        "RB_CLEANUP_DAYS": "Odstrániť staršie ako N dní",
        "LBL_KEEP_COUNT": "Počet:",
        "LBL_KEEP_DAYS": "Dni:",
        # Exclude patterns
        "LBL_EXCLUDE": "Vylúčené vzory (jeden na riadok)",
        # Autostart
        "LBL_AUTOSTART": "Automatické spustenie",
        "CHK_LOGON": "Spustiť pri prihlásení",
        "CHK_SCHEDULED": "Spustiť podľa plánu",
        "LBL_SCHEDULED_TIME": "Čas:",
        "LBL_SCHEDULED_FREQ": "Frekvencia:",
        "FREQ_DAILY": "Každý deň",
        "FREQ_WEEKDAYS": "Pracovné dni",
        "FREQ_WEEKLY": "Každý týždeň v…",
        "LBL_SCHEDULED_DAYS": "Dni:",
        "DAY_MON": "Po", "DAY_TUE": "Ut", "DAY_WED": "St",
        "DAY_THU": "Št", "DAY_FRI": "Pi", "DAY_SAT": "So", "DAY_SUN": "Ne",
        # Settings tab
        "LBL_TRAY": "Systémová lišta",
        "CHK_MINIMIZE_TO_TRAY": "Minimalizovať do lišty pri zatvorení",
        "CHK_START_MINIMIZED": "Spustiť minimalizované do lišty",
        "LBL_NOTIFICATIONS": "Notifikácie",
        "CHK_NOTIFY_SUCCESS": "Notifikovať pri úspechu",
        "CHK_NOTIFY_FAILURE": "Notifikovať pri chybe",
        "LBL_ABOUT": "O aplikácii",
        "LBL_APP_VERSION": "BackupOrim v1.0",
        "BTN_OPEN_LOG": "Otvoriť priečinok s logmi",
        # Language
        "LBL_LANGUAGE": "Jazyk:",
        # Status bar
        "STATUS_NEVER": "Záloha ešte nebola spustená.",
        "STATUS_OK": "Posledná záloha: {dt} — OK ({size})",
        "STATUS_ERROR": "Posledná záloha: {dt} — CHYBA: {msg}",
        # Log messages (UI-facing)
        "LOG_BACKUP_START": "Spúšťam zálohu…",
        "LOG_BACKUP_DONE": "Záloha dokončená.",
        "LOG_BACKUP_FAILED": "Záloha zlyhala: {err}",
        "LOG_SKIPPING_MISSING": "Priečinok neexistuje, preskakujem: {path}",
        "LOG_CREATING_DEST": "Vytváram cieľový priečinok: {path}",
        "LOG_ARCHIVING": "Archivujem: {src} → {dst}",
        "LOG_INTEGRITY_OK": "Integrita OK: {name}",
        "LOG_INTEGRITY_FAIL": "Chyba integrity: {name}",
        "LOG_CLEANUP": "Čistenie: odstraňujem {name}",
        "LOG_CLEANUP_DONE": "Čistenie dokončené.",
        "LOG_SETTINGS_SAVED": "Nastavenia uložené.",
        # Validation errors
        "ERR_NO_SOURCE": "Pridajte aspoň jeden zdrojový priečinok.",
        "ERR_NO_DEST": "Vyberte cieľový priečinok.",
        "ERR_DEST_IN_SOURCE": "Cieľový priečinok nesmie byť vnútri zdrojového priečinka.",
        "ERR_RAR_NOT_FOUND": "Súbor rar.exe nebol nájdený: {path}",
        "ERR_CLEANUP_COUNT": "Počet záloh musí byť kladné celé číslo.",
        "ERR_CLEANUP_DAYS": "Počet dní musí byť kladné celé číslo.",
        "ERR_AUTOSTART_FAILED": "Chyba pri nastavení automatického spustenia: {err}",
        # Dialogs
        "DLG_SELECT_SOURCE": "Vyberte zdrojový priečinok",
        "DLG_SELECT_DEST": "Vyberte cieľový priečinok",
        "DLG_SELECT_RAR": "Vyberte rar.exe",
        "DLG_RAR_FILTER": "Spustiteľné súbory",
        "DLG_VALIDATION_TITLE": "Chyba overenia",
        "DLG_ERROR_TITLE": "Chyba",
        "DLG_INFO_TITLE": "Informácia",
        # Tray menu
        "TRAY_SHOW": "Zobraziť okno",
        "TRAY_RUN_NOW": "Spustiť zálohu teraz",
        "TRAY_OPEN_LOG": "Otvoriť priečinok s logmi",
        "TRAY_EXIT": "Ukončiť",
        # Toast
        "TOAST_SUCCESS_TITLE": "Záloha dokončená",
        "TOAST_FAILURE_TITLE": "Záloha zlyhala",
    },
    "en": {
        # Window / tabs
        "WINDOW_TITLE": "BackupOrim",
        "TAB_MAIN": "Main",
        "TAB_AUTOMATION": "Automation",
        "TAB_SETTINGS": "Settings",
        # Source folders
        "LBL_SOURCES": "Source folders",
        "BTN_ADD_FOLDER": "Add folder…",
        "BTN_REMOVE_SELECTED": "Remove selected",
        # Destination
        "LBL_DESTINATION": "Destination folder",
        "BTN_BROWSE": "Browse…",
        # Format
        "LBL_FORMAT": "Archive format",
        "LBL_RAR_PATH": "Path to rar.exe:",
        "BTN_BROWSE_RAR": "…",
        # Password
        "LBL_PASSWORD": "Password (optional)",
        "LBL_PASSWORD_ENTRY": "Password:",
        "CHK_SHOW_PASSWORD": "Show password",
        "CHK_REMEMBER_PASSWORD": "Remember password",
        "WARN_PASSWORD_PLAINTEXT": "Password will be stored in plaintext in the config file.",
        # Action buttons
        "BTN_SAVE_SETTINGS": "Save settings",
        "BTN_RUN_BACKUP": "▶   Run Backup",
        "CHK_SHUTDOWN_AFTER": "Shut down PC after backup",
        "LOG_SHUTDOWN_SCHEDULED": "Backup done — PC will shut down in 60 s. To cancel: shutdown /a",
        # Cleanup
        "LBL_CLEANUP": "Old backup cleanup",
        "RB_CLEANUP_NONE": "None",
        "RB_CLEANUP_COUNT": "Keep last N backups",
        "RB_CLEANUP_DAYS": "Delete older than N days",
        "LBL_KEEP_COUNT": "Count:",
        "LBL_KEEP_DAYS": "Days:",
        # Exclude patterns
        "LBL_EXCLUDE": "Exclude patterns (one per line)",
        # Autostart
        "LBL_AUTOSTART": "Autostart",
        "CHK_LOGON": "Run at logon",
        "CHK_SCHEDULED": "Run on schedule",
        "LBL_SCHEDULED_TIME": "Time:",
        "LBL_SCHEDULED_FREQ": "Frequency:",
        "FREQ_DAILY": "Every day",
        "FREQ_WEEKDAYS": "Weekdays",
        "FREQ_WEEKLY": "Weekly on…",
        "LBL_SCHEDULED_DAYS": "Days:",
        "DAY_MON": "Mon", "DAY_TUE": "Tue", "DAY_WED": "Wed",
        "DAY_THU": "Thu", "DAY_FRI": "Fri", "DAY_SAT": "Sat", "DAY_SUN": "Sun",
        # Settings tab
        "LBL_TRAY": "System tray",
        "CHK_MINIMIZE_TO_TRAY": "Minimize to tray on close",
        "CHK_START_MINIMIZED": "Start minimized to tray",
        "LBL_NOTIFICATIONS": "Notifications",
        "CHK_NOTIFY_SUCCESS": "Notify on success",
        "CHK_NOTIFY_FAILURE": "Notify on failure",
        "LBL_ABOUT": "About",
        "LBL_APP_VERSION": "BackupOrim v1.0",
        "BTN_OPEN_LOG": "Open log folder",
        # Language
        "LBL_LANGUAGE": "Language:",
        # Status bar
        "STATUS_NEVER": "No backup has been run yet.",
        "STATUS_OK": "Last backup: {dt} — OK ({size})",
        "STATUS_ERROR": "Last backup: {dt} — ERROR: {msg}",
        # Log messages (UI-facing)
        "LOG_BACKUP_START": "Starting backup…",
        "LOG_BACKUP_DONE": "Backup complete.",
        "LOG_BACKUP_FAILED": "Backup failed: {err}",
        "LOG_SKIPPING_MISSING": "Folder missing, skipping: {path}",
        "LOG_CREATING_DEST": "Creating destination: {path}",
        "LOG_ARCHIVING": "Archiving: {src} → {dst}",
        "LOG_INTEGRITY_OK": "Integrity OK: {name}",
        "LOG_INTEGRITY_FAIL": "Integrity check failed: {name}",
        "LOG_CLEANUP": "Cleanup: removing {name}",
        "LOG_CLEANUP_DONE": "Cleanup complete.",
        "LOG_SETTINGS_SAVED": "Settings saved.",
        # Validation errors
        "ERR_NO_SOURCE": "Add at least one source folder.",
        "ERR_NO_DEST": "Select a destination folder.",
        "ERR_DEST_IN_SOURCE": "Destination must not be inside a source folder.",
        "ERR_RAR_NOT_FOUND": "rar.exe not found: {path}",
        "ERR_CLEANUP_COUNT": "Keep count must be a positive integer.",
        "ERR_CLEANUP_DAYS": "Days must be a positive integer.",
        "ERR_AUTOSTART_FAILED": "Autostart configuration failed: {err}",
        # Dialogs
        "DLG_SELECT_SOURCE": "Select source folder",
        "DLG_SELECT_DEST": "Select destination folder",
        "DLG_SELECT_RAR": "Select rar.exe",
        "DLG_RAR_FILTER": "Executable files",
        "DLG_VALIDATION_TITLE": "Validation error",
        "DLG_ERROR_TITLE": "Error",
        "DLG_INFO_TITLE": "Information",
        # Tray menu
        "TRAY_SHOW": "Show window",
        "TRAY_RUN_NOW": "Run backup now",
        "TRAY_OPEN_LOG": "Open log folder",
        "TRAY_EXIT": "Exit",
        # Toast
        "TOAST_SUCCESS_TITLE": "Backup complete",
        "TOAST_FAILURE_TITLE": "Backup failed",
    },
}

assert LANGUAGES["sk"].keys() == LANGUAGES["en"].keys(), \
    "i18n key mismatch between SK and EN tables"


class Translator:
    """Resolves UI string keys to the active language. Falls back to EN, then to the key."""

    def __init__(self, lang: str = "sk"):
        self.lang = lang if lang in LANGUAGES else "sk"

    def __call__(self, key: str) -> str:
        return LANGUAGES[self.lang].get(key) or LANGUAGES["en"].get(key, key)

    def set_language(self, lang: str) -> None:
        if lang in LANGUAGES:
            self.lang = lang
