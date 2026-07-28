from __future__ import annotations

from pathlib import Path
import os
import sys


APP_DIRECTORY_NAME = "ReNamerDocumentClassifier"


def installation_root() -> Path:
    override = os.environ.get("RENAMER_CLASSIFIER_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        if executable_dir.name.casefold() == "classifier":
            return executable_dir.parent
        return executable_dir

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIRECTORY_NAME
    return Path.home() / "AppData" / "Local" / APP_DIRECTORY_NAME


def config_directory() -> Path:
    return installation_root() / "config"


def log_path() -> Path:
    return installation_root() / "logs" / "classification.log"


def tools_directory() -> Path:
    return installation_root() / "tools"


def configure_runtime_environment() -> None:
    tessdata = tools_directory() / "tessdata"
    if tessdata.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(tessdata)


def decode_text_file(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")

    for encoding in ("utf-8", "cp949", "mbcs"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


configure_runtime_environment()
