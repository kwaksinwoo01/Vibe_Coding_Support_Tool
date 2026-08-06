from __future__ import annotations

from contextlib import contextmanager
import threading
from typing import Any, Iterator

import pythoncom
import pywintypes
import win32com.client

from word_editor.infrastructure.robust_word_com import (
    REGDB_E_CLASSNOTREG,
    RPC_E_DISCONNECTED,
    WORD_PROGID,
    format_word_com_diagnostics,
)
from word_editor.infrastructure.verified_style_gateway import VerifiedStyleGateway
from word_editor.infrastructure.word_com import (
    WD_ALERTS_NONE,
    WD_DO_NOT_SAVE_CHANGES,
    WordGatewayError,
    _WordSession,
)


class ProductionWordGateway(VerifiedStyleGateway):
    """Production gateway: fast, verified, safely backed up, and reusable."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owner_thread_id = threading.get_ident()
        self._persistent_application: Any = None
        self._persistent_owns_application = False
        self._persistent_com_initialized = False

    @staticmethod
    def _configure_application(application: Any, owns_application: bool) -> None:
        if owns_application:
            application.Visible = False
        application.DisplayAlerts = WD_ALERTS_NONE
        try:
            application.Options.SaveNormalPrompt = False
        except pywintypes.com_error:
            pass
        try:
            application.ScreenUpdating = False
        except pywintypes.com_error:
            pass

    def _create_application(self) -> tuple[Any, bool]:
        application: Any = None
        owns_application = False
        attempts: list[tuple[str, BaseException]] = []
        try:
            application = win32com.client.GetActiveObject(WORD_PROGID)
        except (pywintypes.com_error, AttributeError) as exc:
            attempts.append(("GetActiveObject", exc))

        if application is None:
            for name, factory in (
                ("DispatchEx", win32com.client.DispatchEx),
                ("Dispatch", win32com.client.Dispatch),
                ("EnsureDispatch", win32com.client.gencache.EnsureDispatch),
            ):
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
            raise WordGatewayError(
                "Microsoft Word COM 서버를 만들지 못했습니다.\n"
                + "\n".join(f"- {name}: {exc}" for name, exc in attempts)
            )
        self._configure_application(application, owns_application)
        return application, owns_application

    @staticmethod
    def _application_alive(application: Any) -> bool:
        try:
            _ = application.Version
            return True
        except (pywintypes.com_error, AttributeError):
            return False

    def _persistent_session(self) -> _WordSession:
        if not self._persistent_com_initialized:
            pythoncom.CoInitialize()
            self._persistent_com_initialized = True
        if (
            self._persistent_application is None
            or not self._application_alive(self._persistent_application)
        ):
            self._persistent_application = None
            self._persistent_owns_application = False
            application, owns_application = self._create_application()
            self._persistent_application = application
            self._persistent_owns_application = owns_application
        return _WordSession(
            self._persistent_application,
            self._persistent_owns_application,
        )

    @contextmanager
    def _session(self) -> Iterator[_WordSession]:
        if threading.get_ident() == self._owner_thread_id:
            yield self._persistent_session()
            return
        pythoncom.CoInitialize()
        application: Any = None
        owns_application = False
        try:
            application, owns_application = self._create_application()
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

    def close(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            return
        application = self._persistent_application
        owns_application = self._persistent_owns_application
        self._persistent_application = None
        self._persistent_owns_application = False
        if application is not None and owns_application:
            try:
                application.Quit(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
            except pywintypes.com_error as exc:
                if getattr(exc, "hresult", None) != RPC_E_DISCONNECTED:
                    try:
                        application.Quit()
                    except pywintypes.com_error:
                        pass
        application = None
        if self._persistent_com_initialized:
            self._persistent_com_initialized = False
            pythoncom.CoUninitialize()
