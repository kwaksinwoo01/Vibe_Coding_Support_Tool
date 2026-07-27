from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import traceback


def _write_host_trace(message: str) -> None:
    """Write launcher diagnostics without relying on console handles."""

    try:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return

        path = (
            Path(local_app_data)
            / "ReNamerDocumentClassifier"
            / "logs"
            / "launcher_runtime.log"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {message}\n")
    except OSError:
        pass


_write_host_trace("launcher_start")
_write_host_trace("cli_import_start")
from renamer_document_classifier.cli import main  # noqa: E402
_write_host_trace("cli_import_complete")


if __name__ == "__main__":
    _write_host_trace("cli_main_start")
    try:
        exit_code = main()
    except BaseException:  # noqa: BLE001 - earliest file-only diagnostic boundary
        _write_host_trace("cli_main_exception\n" + traceback.format_exc())
        raise
    _write_host_trace(f"cli_main_return code={exit_code}")
    raise SystemExit(exit_code)
