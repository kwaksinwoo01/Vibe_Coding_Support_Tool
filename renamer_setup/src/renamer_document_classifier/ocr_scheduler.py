from __future__ import annotations

from configparser import ConfigParser
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
import os
import time
from typing import BinaryIO

from .runtime_paths import config_directory, installation_root


SCHEDULER_SECTION = "ocr.scheduler"
SCHEDULER_FILE_NAME = "ocr_scheduler.ini"


def _default_cpu_workers() -> int:
    logical_cpus = os.cpu_count() or 2
    return max(2, min(8, logical_cpus // 2))


@dataclass(frozen=True, slots=True)
class OcrSchedulerConfig:
    """Total OCR resource budget shared by ReNamer classifier processes."""

    cpu_workers: int = 0
    gpu_workers: int = 1
    max_documents_in_flight: int = 2
    max_attempts_per_document: int = 6
    memory_budget_mb: int = 2048
    batch_size: int = 2

    def normalized(self) -> "OcrSchedulerConfig":
        return OcrSchedulerConfig(
            cpu_workers=max(1, min(64, self.cpu_workers or _default_cpu_workers())),
            gpu_workers=max(0, min(8, self.gpu_workers)),
            max_documents_in_flight=max(
                1, min(16, self.max_documents_in_flight)
            ),
            max_attempts_per_document=max(
                1, min(16, self.max_attempts_per_document)
            ),
            memory_budget_mb=max(256, min(65_536, self.memory_budget_mb)),
            batch_size=max(1, min(32, self.batch_size)),
        )

    @property
    def cpu_workers_per_document(self) -> int:
        active = self.normalized()
        return max(1, active.cpu_workers // active.max_documents_in_flight)

    def max_parallel_attempts(self, *, dpi: int, page_count: int) -> int:
        """Cap simultaneous engines using the per-document memory allowance."""

        active = self.normalized()
        pages = max(1, page_count)
        # A grayscale A4 page is roughly 8.7 MiB at 300 DPI. OCR engines make
        # several working copies, so reserve 64 MiB per page and scale by area.
        estimated_attempt_mb = max(
            64,
            round(64 * pages * (max(100, dpi) / 300) ** 2),
        )
        per_document_mb = max(
            1, active.memory_budget_mb // active.max_documents_in_flight
        )
        memory_slots = max(1, per_document_mb // estimated_attempt_mb)
        engine_slots = active.cpu_workers_per_document + (
            1 if active.gpu_workers > 0 else 0
        )
        return max(
            1,
            min(active.max_attempts_per_document, memory_slots, engine_slots),
        )


def scheduler_path() -> Path:
    return config_directory() / SCHEDULER_FILE_NAME


def _serialize(config: OcrSchedulerConfig) -> str:
    active = config.normalized()
    return (
        f"[{SCHEDULER_SECTION}]\n"
        f"cpu_workers = {active.cpu_workers}\n"
        f"gpu_workers = {active.gpu_workers}\n"
        f"max_documents_in_flight = {active.max_documents_in_flight}\n"
        f"max_attempts_per_document = {active.max_attempts_per_document}\n"
        f"memory_budget_mb = {active.memory_budget_mb}\n"
        f"batch_size = {active.batch_size}\n"
    )


def ensure_scheduler_file() -> Path:
    path = scheduler_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(_serialize(OcrSchedulerConfig()), encoding="utf-8-sig")
    return path


def _read_integer(
    parser: ConfigParser,
    key: str,
    default: int,
) -> int:
    try:
        return parser.getint(SCHEDULER_SECTION, key, fallback=default)
    except ValueError:
        return default


def load_scheduler_config(path: Path | None = None) -> OcrSchedulerConfig:
    source = path or scheduler_path()
    defaults = OcrSchedulerConfig()
    if not source.is_file():
        return defaults.normalized()

    parser = ConfigParser()
    try:
        parser.read(source, encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return defaults.normalized()

    return OcrSchedulerConfig(
        cpu_workers=_read_integer(parser, "cpu_workers", defaults.cpu_workers),
        gpu_workers=_read_integer(parser, "gpu_workers", defaults.gpu_workers),
        max_documents_in_flight=_read_integer(
            parser,
            "max_documents_in_flight",
            defaults.max_documents_in_flight,
        ),
        max_attempts_per_document=_read_integer(
            parser,
            "max_attempts_per_document",
            defaults.max_attempts_per_document,
        ),
        memory_budget_mb=_read_integer(
            parser, "memory_budget_mb", defaults.memory_budget_mb
        ),
        batch_size=_read_integer(parser, "batch_size", defaults.batch_size),
    ).normalized()


class SchedulerSlotLease(AbstractContextManager["SchedulerSlotLease"]):
    """Cross-process slot pool used by document, CPU, and accelerator lanes."""

    def __init__(
        self,
        pool_name: str,
        slots: int,
        timeout_seconds: int,
    ) -> None:
        if not pool_name.replace("-", "").isalnum():
            raise ValueError("scheduler pool name must be alphanumeric")
        self._pool_name = pool_name
        self._slots = max(1, slots)
        self._timeout_seconds = max(1, timeout_seconds)
        self._handle: BinaryIO | None = None

    @staticmethod
    def _try_lock(handle: BinaryIO) -> bool:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    @staticmethod
    def _unlock(handle: BinaryIO) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def __enter__(self) -> "SchedulerSlotLease":
        directory = installation_root() / "temp" / "ocr-scheduler"
        directory.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self._timeout_seconds

        while True:
            for index in range(self._slots):
                handle = (
                    directory / f"{self._pool_name}-{index}.lock"
                ).open("a+b")
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                if self._try_lock(handle):
                    self._handle = handle
                    return self
                handle.close()

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"OCR scheduler pool '{self._pool_name}' timed out"
                )
            time.sleep(0.05)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._handle is not None:
            try:
                self._unlock(self._handle)
            finally:
                self._handle.close()
                self._handle = None


class DocumentSlotLease(SchedulerSlotLease):
    """Cross-process admission gate for concurrent ReNamer PDF documents."""

    def __init__(self, slots: int, timeout_seconds: int) -> None:
        super().__init__("document", slots, timeout_seconds)
