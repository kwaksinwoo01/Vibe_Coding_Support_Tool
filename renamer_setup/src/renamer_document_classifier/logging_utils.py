from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from .runtime_paths import log_path


MAX_LOG_BYTES = 5 * 1024 * 1024


def _ensure_log_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
        rotated = path.with_suffix(".previous.log")
        try:
            rotated.unlink(missing_ok=True)
            path.replace(rotated)
        except OSError:
            path.write_text("", encoding="utf-8-sig")

    if not path.exists():
        path.write_text("", encoding="utf-8-sig")


def append_log(lines: Iterable[str]) -> Path:
    path = log_path()
    _ensure_log_file(path)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = ["", "[FILE]", f"time={timestamp}"]
    payload.extend(line.rstrip("\r\n") for line in lines)
    payload.append("[/FILE]")

    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(payload) + "\n")
    return path


def clear_log() -> Path:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8-sig")
    return path
