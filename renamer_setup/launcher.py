from __future__ import annotations

import os
import sys
from typing import IO


_NULL_STDIN: IO[str] | None = None


def _attach_null_stdin_on_windows() -> None:
    """Give child processes a valid stdin handle when launched by GUI hosts.

    ReNamer starts classifier.exe through ExecConsoleApp without a usable
    standard-input handle. Python subprocess calls otherwise inherit that
    invalid handle and fail with WinError 6 before Poppler or Tesseract starts.
    The classifier never reads interactive input, so Windows NUL is appropriate.
    """

    global _NULL_STDIN

    if os.name != "nt":
        return

    import ctypes
    import msvcrt
    from ctypes import wintypes

    _NULL_STDIN = open(os.devnull, "r", encoding="utf-8", errors="ignore")
    null_handle = msvcrt.get_osfhandle(_NULL_STDIN.fileno())

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetStdHandle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
    kernel32.SetStdHandle.restype = wintypes.BOOL

    std_input_handle = wintypes.DWORD(-10 & 0xFFFFFFFF)
    if not kernel32.SetStdHandle(
        std_input_handle,
        wintypes.HANDLE(null_handle),
    ):
        raise OSError(
            ctypes.get_last_error(),
            "SetStdHandle(STD_INPUT_HANDLE) failed",
        )

    sys.stdin = _NULL_STDIN


_attach_null_stdin_on_windows()

from renamer_document_classifier.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
