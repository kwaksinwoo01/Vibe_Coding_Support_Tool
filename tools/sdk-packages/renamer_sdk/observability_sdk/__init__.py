"""In-memory observability primitives for SDK orchestration and tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from renamer_sdk.core_sdk import Severity


@dataclass(frozen=True, slots=True)
class SdkEvent:
    name: str
    message: str
    severity: Severity
    timestamp_utc: datetime


class EventRecorder:
    def __init__(self) -> None:
        self._events: list[SdkEvent] = []

    def emit(
        self,
        name: str,
        message: str,
        severity: Severity = Severity.INFO,
    ) -> None:
        self._events.append(
            SdkEvent(
                name=name,
                message=message,
                severity=severity,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )

    @property
    def events(self) -> tuple[SdkEvent, ...]:
        return tuple(self._events)
