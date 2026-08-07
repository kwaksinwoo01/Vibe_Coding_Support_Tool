"""Common execution contracts for the ReNamer development SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, Protocol, TypeVar
from uuid import uuid4


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class OperationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    operation_id: str = field(default_factory=lambda: uuid4().hex)
    dry_run: bool = True


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class OperationResult(Generic[T]):
    status: OperationStatus
    value: T | None = None
    messages: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status is OperationStatus.PASSED


class Executable(Protocol[T]):
    def execute(self, context: ExecutionContext) -> OperationResult[T]: ...


class Validator(Protocol[T]):
    def validate(self, value: T) -> OperationResult[T]: ...
