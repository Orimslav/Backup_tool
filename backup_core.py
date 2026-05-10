"""Archive creation, cleanup, and integrity verification. No tkinter imports."""
from __future__ import annotations
import fnmatch
import os
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

_CREATE_NO_WINDOW = 0x08000000

try:
    import pyzipper
    _HAS_PYZIPPER = True
except ImportError:
    _HAS_PYZIPPER = False


def _zip_write_clamped(zf, file_path: Path, arcname) -> None:
    zi = zipfile.ZipInfo.from_file(str(file_path), str(arcname), strict_timestamps=False)
    zi.compress_type = zipfile.ZIP_DEFLATED
    with open(file_path, "rb") as src, zf.open(zi, "w") as dst:
        shutil.copyfileobj(src, dst)


def _should_exclude(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def make_zip(
    source: str,
    archive_path: str,
    log: Callable[[str], None],
    password: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> None:
    patterns = exclude_patterns or []
    tmp_path = archive_path + ".tmp"
    source_path = Path(source)
    basename = source_path.name or "drive"

    try:
        if password and _HAS_PYZIPPER:
            zf_ctx = pyzipper.AESZipFile(
                tmp_path, "w",
                compression=pyzipper.ZIP_DEFLATED,
                allowZip64=True,
                encryption=pyzipper.WZ_AES,
            )
            zf_ctx.setpassword(password.encode("utf-8"))
        else:
            zf_ctx = zipfile.ZipFile(
                tmp_path, "w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            )

        with zf_ctx as zf:
            for dirpath, dirnames, filenames in os.walk(source):
                rel_dir = Path(dirpath).relative_to(source_path.parent)
                dirnames[:] = [
                    d for d in dirnames
                    if not _should_exclude(d, patterns)
                ]
                for filename in filenames:
                    if _should_exclude(filename, patterns):
                        continue
                    file_path = Path(dirpath) / filename
                    arcname = rel_dir / filename
                    try:
                        _zip_write_clamped(zf, file_path, arcname)
                    except (OSError, PermissionError) as e:
                        log(f"Skipping {file_path}: {e}")

        Path(tmp_path).rename(archive_path)
    except Exception:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def make_rar(
    source: str,
    archive_path: str,
    rar_exe: str,
    password: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> None:
    patterns = exclude_patterns or []
    source_path = Path(source)
    basename = source_path.name or "drive"
    cwd = str(source_path.parent)

    cmd = [rar_exe, "a", "-r", "-y"]
    if password:
        cmd.append(f"-hp{password}")
    for p in patterns:
        cmd.append(f"-x{p}")
    cmd += [archive_path, basename]

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"rar.exe exited with code {result.returncode}: {result.stderr.strip()}")


def _verify_zip(archive_path: str) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"Integrity check failed: first bad file: {bad}")


def _verify_rar(archive_path: str, rar_exe: str) -> None:
    result = subprocess.run(
        [rar_exe, "t", archive_path],
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        raise RuntimeError(f"RAR integrity check failed (exit {result.returncode})")


def verify_archive(archive_path: str, fmt: str, rar_exe: str = "") -> None:
    if fmt == "zip":
        _verify_zip(archive_path)
    elif fmt == "rar":
        _verify_rar(archive_path, rar_exe)


_TS_PATTERN = re.compile(
    r"^(.+)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.(zip|rar)$"
)


def _parse_backup_files(
    destination: str,
    folder_prefix: str,
    extension: str,
) -> list[tuple[datetime, Path]]:
    dest = Path(destination)
    results: list[tuple[datetime, Path]] = []
    for f in dest.iterdir():
        if not f.is_file():
            continue
        m = _TS_PATTERN.match(f.name)
        if not m:
            continue
        prefix, ts_str, ext = m.group(1), m.group(2), m.group(3)
        if prefix != folder_prefix or ext != extension:
            continue
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
            results.append((dt, f))
        except ValueError:
            continue
    return sorted(results, key=lambda x: x[0])


def cleanup_backups(
    destination: str,
    folder_prefix: str,
    extension: str,
    mode: str,
    keep_count: int,
    keep_days: int,
    log: Callable[[str], None],
) -> None:
    if mode == "none":
        return

    backups = _parse_backup_files(destination, folder_prefix, extension)

    if mode == "count":
        to_delete = backups[:-keep_count] if keep_count > 0 else backups
    elif mode == "days":
        cutoff = datetime.now() - timedelta(days=keep_days)
        to_delete = [(dt, p) for dt, p in backups if dt < cutoff]
    else:
        return

    for _, path in to_delete:
        try:
            path.unlink()
            log(f"Cleanup: removed {path.name}")
        except OSError as e:
            log(f"Cleanup: could not remove {path.name}: {e}")
