"""Stream redirect guard for windowless (no-console) PyInstaller builds.

On Windows with console=False, sys.stdout and sys.stderr are None.
Any print(), logging, or traceback crashes with AttributeError.
This module detects that condition and redirects streams to a log file.
"""

import os
import sys
from pathlib import Path

_MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB


def is_windowless() -> bool:
    """Return True when running without a console (stdout/stderr are None)."""
    return sys.stdout is None or sys.stderr is None


def redirect_streams() -> None:
    """Redirect stdout/stderr to a log file when running windowless.

    No-op when a console is attached (interactive ``uv run`` dev use).
    Falls back to ``os.devnull`` if the log directory cannot be created.
    The file handle is intentionally never closed — it lives for the
    process lifetime.
    """
    if not is_windowless():
        return

    log_path = _get_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed(log_path)
        log_file = log_path.open("a", encoding="utf-8")
    except OSError:
        log_file = Path(os.devnull).open("w", encoding="utf-8")  # noqa: SIM115

    sys.stdout = log_file
    sys.stderr = log_file


def _get_log_path() -> Path:
    """Return the log file path under %LOCALAPPDATA%."""
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        return Path(local_appdata) / "steelseries-oled" / "steelseries.log"
    # Fallback for non-standard environments
    return Path.home() / ".steelseries-oled" / "steelseries.log"


def _rotate_if_needed(log_path: Path) -> None:
    """Truncate log to last half when exceeding size limit."""
    try:
        if not log_path.exists() or log_path.stat().st_size <= _MAX_LOG_BYTES:
            return
        data = log_path.read_bytes()
        half = len(data) // 2
        # Find next newline after the halfway point to avoid splitting a line
        newline = data.find(b"\n", half)
        if newline != -1:
            log_path.write_bytes(data[newline + 1 :])
        else:
            log_path.write_bytes(data[half:])
    except OSError:
        pass
