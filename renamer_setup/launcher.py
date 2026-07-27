from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any, IO, Sequence
import uuid


_NULL_STDIN: IO[str] | None = None
_ORIGINAL_SUBPROCESS_RUN = subprocess.run


def _attach_null_stdin_on_windows() -> None:
    """Give classifier.exe a valid stdin handle when launched by a GUI host."""

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


def _runtime_temp_directory() -> Path:
    if getattr(sys, "frozen", False):
        executable_directory = Path(sys.executable).resolve().parent
        if executable_directory.name.casefold() == "classifier":
            root = executable_directory.parent
        else:
            root = executable_directory
        output = root / "temp" / "process"
    else:
        output = Path.cwd() / ".classifier-process-temp"

    output.mkdir(parents=True, exist_ok=True)
    return output


def _run_with_windows_api(
    arguments: Sequence[str | os.PathLike[str]],
    *,
    cwd: str | os.PathLike[str] | None,
    timeout: float | None,
    encoding: str,
    errors: str,
    text_mode: bool,
    check: bool,
    creationflags: int,
) -> subprocess.CompletedProcess[Any]:
    """Run a child with explicit NUL/stdout/stderr handles.

    ReNamer's ExecConsoleApp can start classifier.exe with invalid inherited
    standard handles. CreateProcessW receives new handles here, so Poppler,
    Tesseract and LibreOffice never inherit ReNamer's console handles.
    """

    import ctypes
    import msvcrt
    from ctypes import wintypes

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    token = uuid.uuid4().hex
    temp_directory = _runtime_temp_directory()
    stdout_path = temp_directory / f"stdout-{token}.tmp"
    stderr_path = temp_directory / f"stderr-{token}.tmp"

    stdin_stream = open(os.devnull, "rb")
    stdout_stream = open(stdout_path, "w+b")
    stderr_stream = open(stderr_path, "w+b")

    process_information = PROCESS_INFORMATION()
    command_arguments = [os.fspath(value) for value in arguments]
    command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command_arguments))

    handles: list[int] = []
    try:
        stdin_handle = msvcrt.get_osfhandle(stdin_stream.fileno())
        stdout_handle = msvcrt.get_osfhandle(stdout_stream.fileno())
        stderr_handle = msvcrt.get_osfhandle(stderr_stream.fileno())
        handles = [stdin_handle, stdout_handle, stderr_handle]

        for handle in handles:
            os.set_handle_inheritable(handle, True)

        startup_information = STARTUPINFOW()
        startup_information.cb = ctypes.sizeof(STARTUPINFOW)
        startup_information.dwFlags = 0x00000100 | 0x00000001
        startup_information.wShowWindow = 0
        startup_information.hStdInput = wintypes.HANDLE(stdin_handle)
        startup_information.hStdOutput = wintypes.HANDLE(stdout_handle)
        startup_information.hStdError = wintypes.HANDLE(stderr_handle)

        flags = int(creationflags) | 0x08000000
        created = kernel32.CreateProcessW(
            None,
            command_line,
            None,
            None,
            True,
            flags,
            None,
            os.fspath(cwd) if cwd else None,
            ctypes.byref(startup_information),
            ctypes.byref(process_information),
        )
        if not created:
            raise ctypes.WinError(ctypes.get_last_error())

        for handle in handles:
            os.set_handle_inheritable(handle, False)

        wait_milliseconds = 0xFFFFFFFF
        if timeout is not None:
            wait_milliseconds = max(0, int(float(timeout) * 1000))

        wait_result = kernel32.WaitForSingleObject(
            process_information.hProcess,
            wait_milliseconds,
        )
        if wait_result == 0x00000102:
            kernel32.TerminateProcess(process_information.hProcess, 1)
            kernel32.WaitForSingleObject(process_information.hProcess, 5000)
            raise subprocess.TimeoutExpired(command_arguments, timeout)
        if wait_result == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())

        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(
            process_information.hProcess,
            ctypes.byref(exit_code),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        for handle in handles:
            try:
                os.set_handle_inheritable(handle, False)
            except OSError:
                pass

        if process_information.hThread:
            kernel32.CloseHandle(process_information.hThread)
        if process_information.hProcess:
            kernel32.CloseHandle(process_information.hProcess)

        stdin_stream.close()
        stdout_stream.close()
        stderr_stream.close()

    stdout_bytes = stdout_path.read_bytes() if stdout_path.exists() else b""
    stderr_bytes = stderr_path.read_bytes() if stderr_path.exists() else b""
    stdout_path.unlink(missing_ok=True)
    stderr_path.unlink(missing_ok=True)

    if text_mode:
        stdout_value: str | bytes = stdout_bytes.decode(encoding, errors=errors)
        stderr_value: str | bytes = stderr_bytes.decode(encoding, errors=errors)
    else:
        stdout_value = stdout_bytes
        stderr_value = stderr_bytes

    completed = subprocess.CompletedProcess(
        command_arguments,
        int(exit_code.value),
        stdout_value,
        stderr_value,
    )
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            completed.args,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    return completed


def _install_isolated_windows_runner() -> None:
    if os.name != "nt":
        return

    def isolated_run(
        *popenargs: Any,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[Any]:
        if len(popenargs) != 1 or isinstance(popenargs[0], (str, bytes)):
            return _ORIGINAL_SUBPROCESS_RUN(*popenargs, **kwargs)
        if kwargs.get("shell"):
            return _ORIGINAL_SUBPROCESS_RUN(*popenargs, **kwargs)
        if kwargs.get("input") is not None:
            return _ORIGINAL_SUBPROCESS_RUN(*popenargs, **kwargs)

        capture_output = bool(kwargs.get("capture_output", False))
        stdout = kwargs.get("stdout")
        stderr = kwargs.get("stderr")
        if not capture_output and not (
            stdout == subprocess.PIPE and stderr == subprocess.PIPE
        ):
            return _ORIGINAL_SUBPROCESS_RUN(*popenargs, **kwargs)

        return _run_with_windows_api(
            popenargs[0],
            cwd=kwargs.get("cwd"),
            timeout=kwargs.get("timeout"),
            encoding=kwargs.get("encoding") or "utf-8",
            errors=kwargs.get("errors") or "replace",
            text_mode=bool(kwargs.get("text") or kwargs.get("universal_newlines")),
            check=bool(kwargs.get("check", False)),
            creationflags=int(kwargs.get("creationflags", 0)),
        )

    subprocess.run = isolated_run  # type: ignore[assignment]


_attach_null_stdin_on_windows()
_install_isolated_windows_runner()

from renamer_document_classifier.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
