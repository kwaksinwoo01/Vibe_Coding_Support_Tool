from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import struct
import sys
from typing import Any, Iterator
import winreg

import pythoncom
import pywintypes
import win32com.client

from word_editor.infrastructure.editable_word_com import EditableWordComGateway
from word_editor.infrastructure.word_com import (
    WD_ALERTS_NONE,
    WD_DO_NOT_SAVE_CHANGES,
    WordGatewayError,
    _WordSession,
)

REGDB_E_CLASSNOTREG = -2147221164
WORD_PROGID = "Word.Application"


@dataclass(frozen=True, slots=True)
class ComRegistrationView:
    bits: int
    clsid: str = ""
    local_server: str = ""
    error: str = ""

    @property
    def registered(self) -> bool:
        return bool(self.clsid)


def _read_default_value(path: str, access: int) -> str:
    with winreg.OpenKey(
        winreg.HKEY_CLASSES_ROOT,
        path,
        0,
        winreg.KEY_READ | access,
    ) as key:
        value, _ = winreg.QueryValueEx(key, None)
        return str(value)


def inspect_word_registration(bits: int) -> ComRegistrationView:
    access = winreg.KEY_WOW64_64KEY if bits == 64 else winreg.KEY_WOW64_32KEY
    try:
        clsid = _read_default_value(r"Word.Application\CLSID", access)
    except OSError as exc:
        return ComRegistrationView(bits=bits, error=str(exc))

    local_server = ""
    try:
        local_server = _read_default_value(
            rf"CLSID\{clsid}\LocalServer32",
            access,
        )
    except OSError:
        pass

    return ComRegistrationView(
        bits=bits,
        clsid=clsid,
        local_server=local_server,
    )


def format_word_com_diagnostics(attempts: list[tuple[str, BaseException]]) -> str:
    python_bits = struct.calcsize("P") * 8
    registration_64 = inspect_word_registration(64)
    registration_32 = inspect_word_registration(32)
    current_registration = (
        registration_64 if python_bits == 64 else registration_32
    )
    other_registration = (
        registration_32 if python_bits == 64 else registration_64
    )

    attempt_lines = []
    for name, exc in attempts:
        hresult = getattr(exc, "hresult", None)
        attempt_lines.append(f"- {name}: HRESULT={hresult}, {exc}")

    registration_lines = [
        (
            "- 64비트 등록: "
            + (
                f"있음, CLSID={registration_64.clsid}, "
                f"서버={registration_64.local_server or '(경로 미확인)'}"
                if registration_64.registered
                else f"없음 ({registration_64.error})"
            )
        ),
        (
            "- 32비트 등록: "
            + (
                f"있음, CLSID={registration_32.clsid}, "
                f"서버={registration_32.local_server or '(경로 미확인)'}"
                if registration_32.registered
                else f"없음 ({registration_32.error})"
            )
        ),
    ]

    if not current_registration.registered and other_registration.registered:
        diagnosis = (
            f"현재 Python은 {python_bits}비트이지만 Word.Application은 "
            f"{other_registration.bits}비트 레지스트리 뷰에만 등록되어 있습니다.\n"
            "Office와 같은 비트 수의 Python으로 word_editor 가상환경을 "
            "다시 생성해야 합니다."
        )
    elif not registration_64.registered and not registration_32.registered:
        diagnosis = (
            "Word.Application COM 등록이 32비트와 64비트 레지스트리에서 "
            "모두 발견되지 않았습니다. Word를 /r 옵션으로 다시 등록하거나 "
            "Microsoft 365/Office 빠른 복구를 실행해야 합니다."
        )
    else:
        diagnosis = (
            "현재 Python 비트 수에 Word COM 등록은 보이지만 COM 서버 생성에 "
            "실패했습니다. Word를 완전히 종료한 뒤 WINWORD.EXE /r을 실행하고, "
            "계속 실패하면 Office 빠른 복구를 실행하십시오."
        )

    return "\n".join(
        [
            "Microsoft Word COM 초기화에 실패했습니다.",
            "오류: 0x80040154 REGDB_E_CLASSNOTREG (클래스가 등록되지 않음)",
            "",
            f"Python: {sys.executable}",
            f"Python 비트 수: {python_bits}비트",
            "",
            "Word COM 등록 상태:",
            *registration_lines,
            "",
            "COM 생성 시도:",
            *(attempt_lines or ["- 기록 없음"]),
            "",
            "판정:",
            diagnosis,
            "",
            "먼저 저장소 main을 받은 뒤 다음 명령을 실행하십시오:",
            r"  .\run_word_editor.ps1 -Diagnose",
            r"  .\run_word_editor.ps1 -Install -RecreateVenv",
        ]
    )


class RobustWordComGateway(EditableWordComGateway):
    """Editable Word gateway with architecture-aware COM diagnostics."""

    @contextmanager
    def _session(self) -> Iterator[_WordSession]:
        pythoncom.CoInitialize()
        application: Any = None
        owns_application = False
        attempts: list[tuple[str, BaseException]] = []

        try:
            try:
                application = win32com.client.GetActiveObject(WORD_PROGID)
            except (pywintypes.com_error, AttributeError) as exc:
                attempts.append(("GetActiveObject", exc))

            if application is None:
                factories = (
                    ("DispatchEx", win32com.client.DispatchEx),
                    ("Dispatch", win32com.client.Dispatch),
                    ("EnsureDispatch", win32com.client.gencache.EnsureDispatch),
                )
                for name, factory in factories:
                    try:
                        application = factory(WORD_PROGID)
                        owns_application = True
                        break
                    except (pywintypes.com_error, AttributeError) as exc:
                        attempts.append((name, exc))

            if application is None:
                if any(
                    getattr(exc, "hresult", None) == REGDB_E_CLASSNOTREG
                    for _, exc in attempts
                ):
                    raise WordGatewayError(format_word_com_diagnostics(attempts))
                details = "\n".join(
                    f"- {name}: {exc}" for name, exc in attempts
                )
                raise WordGatewayError(
                    "Microsoft Word COM 서버를 만들지 못했습니다.\n" + details
                )

            if owns_application:
                application.Visible = False
            application.DisplayAlerts = WD_ALERTS_NONE
            try:
                application.Options.SaveNormalPrompt = False
            except pywintypes.com_error:
                pass

            yield _WordSession(application, owns_application)
        finally:
            if application is not None and owns_application:
                try:
                    application.Quit(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                except pywintypes.com_error:
                    try:
                        application.Quit()
                    except pywintypes.com_error:
                        pass
            application = None
            pythoncom.CoUninitialize()
