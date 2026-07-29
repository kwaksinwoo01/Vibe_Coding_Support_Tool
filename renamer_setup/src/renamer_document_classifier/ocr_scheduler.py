from __future__ import annotations

from configparser import ConfigParser, Error as ConfigParserError
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
import ctypes
import os
import shutil
import time
from typing import BinaryIO

from .runtime_paths import config_directory, installation_root


SCHEDULER_SECTION = "ocr.scheduler"
SCHEDULER_FILE_NAME = "ocr_scheduler.ini"
SCHEDULER_PROFILE_VERSION = 2
SCHEDULER_VALUE_KEYS = (
    "cpu_workers",
    "gpu_workers",
    "max_documents_in_flight",
    "max_attempts_per_document",
    "memory_budget_mb",
    "batch_size",
)


def _default_cpu_workers() -> int:
    logical_cpus = os.cpu_count() or 2
    return max(2, min(8, logical_cpus // 2))


@dataclass(frozen=True, slots=True)
class SystemCapacity:
    logical_processors: int
    total_memory_mb: int


def _windows_total_memory_mb() -> int:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    try:
        succeeded = ctypes.windll.kernel32.GlobalMemoryStatusEx(  # type: ignore[attr-defined]
            ctypes.byref(status)
        )
    except (AttributeError, OSError):
        return 0
    if not succeeded:
        return 0
    return max(0, status.ullTotalPhys // (1024 * 1024))


def _posix_total_memory_mb() -> int:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return 0
    return max(0, (page_size * page_count) // (1024 * 1024))


def detect_system_capacity() -> SystemCapacity:
    total_memory_mb = (
        _windows_total_memory_mb() if os.name == "nt" else _posix_total_memory_mb()
    )
    if total_memory_mb <= 0:
        # Conservative fallback for environments that block memory APIs.
        total_memory_mb = 8 * 1024
    return SystemCapacity(
        logical_processors=max(1, os.cpu_count() or 1),
        total_memory_mb=total_memory_mb,
    )


def recommended_scheduler_config(
    capacity: SystemCapacity | None = None,
) -> "OcrSchedulerConfig":
    system = capacity or detect_system_capacity()
    cpu_workers = max(
        1,
        min(32, round(system.logical_processors * 0.8)),
    )
    memory_budget_mb = max(
        1024,
        min(16 * 1024, system.total_memory_mb // 4),
    )
    memory_budget_mb = max(1024, round(memory_budget_mb / 512) * 512)
    document_capacity = min(
        4,
        max(1, cpu_workers // 3),
        max(1, memory_budget_mb // 2048),
    )
    return OcrSchedulerConfig(
        cpu_workers=cpu_workers,
        gpu_workers=1,
        max_documents_in_flight=document_capacity,
        max_attempts_per_document=6,
        memory_budget_mb=memory_budget_mb,
        batch_size=2 if system.total_memory_mb >= 8 * 1024 else 1,
    ).normalized()


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


def _serialize_auto(
    capacity: SystemCapacity | None = None,
    manual_values: dict[str, int] | None = None,
) -> str:
    system = capacity or detect_system_capacity()
    overrides = manual_values or {}

    def value(key: str) -> str:
        return str(overrides[key]) if key in overrides else "auto"

    return (
        "; auto means that this value is recalculated for the current PC.\n"
        "; Replace an individual auto value with a number to override it.\n"
        f"[{SCHEDULER_SECTION}]\n"
        f"profile_version = {SCHEDULER_PROFILE_VERSION}\n"
        f"detected_logical_processors = {system.logical_processors}\n"
        f"detected_total_memory_mb = {system.total_memory_mb}\n"
        f"cpu_workers = {value('cpu_workers')}\n"
        f"gpu_workers = {value('gpu_workers')}\n"
        "max_documents_in_flight = "
        f"{value('max_documents_in_flight')}\n"
        "max_attempts_per_document = "
        f"{value('max_attempts_per_document')}\n"
        f"memory_budget_mb = {value('memory_budget_mb')}\n"
        f"batch_size = {value('batch_size')}\n"
    )


def _read_parser(path: Path) -> ConfigParser | None:
    parser = ConfigParser()
    try:
        parser.read(path, encoding="utf-8-sig")
    except (ConfigParserError, OSError, UnicodeError):
        return None
    if not parser.has_section(SCHEDULER_SECTION):
        return None
    return parser


def _legacy_manual_values(path: Path) -> dict[str, int] | None:
    parser = _read_parser(path)
    if parser is None or parser.has_option(SCHEDULER_SECTION, "profile_version"):
        return None
    expected = {
        "cpu_workers": _default_cpu_workers(),
        "gpu_workers": 1,
        "max_documents_in_flight": 2,
        "max_attempts_per_document": 6,
        "memory_budget_mb": 2048,
        "batch_size": 2,
    }
    try:
        current = {
            key: parser.getint(SCHEDULER_SECTION, key)
            for key in expected
        }
    except (ConfigParserError, ValueError):
        return None
    return {
        key: value
        for key, value in current.items()
        if value != expected[key]
    }


def ensure_scheduler_file() -> Path:
    path = scheduler_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy_manual_values: dict[str, int] | None = None
    if not path.exists():
        path.write_text(_serialize_auto(), encoding="utf-8-sig")
    else:
        legacy_manual_values = _legacy_manual_values(path)
    if legacy_manual_values is not None:
        backup = path.with_suffix(path.suffix + ".legacy-default.bak")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(
            _serialize_auto(manual_values=legacy_manual_values),
            encoding="utf-8-sig",
        )
    return path


def _read_integer(
    parser: ConfigParser,
    key: str,
    default: int,
) -> int:
    raw_value = parser.get(SCHEDULER_SECTION, key, fallback="auto").strip()
    if raw_value.casefold() == "auto":
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def load_scheduler_config(path: Path | None = None) -> OcrSchedulerConfig:
    source = path or scheduler_path()
    defaults = recommended_scheduler_config()
    if not source.is_file():
        return defaults

    parser = _read_parser(source)
    if parser is None:
        return defaults

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


def scheduler_profile_mode(path: Path | None = None) -> str:
    source = path or scheduler_path()
    if not source.is_file():
        return "AUTO"
    parser = _read_parser(source)
    if parser is None:
        return "AUTO_FALLBACK"
    automatic = sum(
        parser.get(SCHEDULER_SECTION, key, fallback="auto").strip().casefold()
        == "auto"
        for key in SCHEDULER_VALUE_KEYS
    )
    if automatic == len(SCHEDULER_VALUE_KEYS):
        return "AUTO"
    if automatic == 0:
        return "MANUAL"
    return "MIXED"


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
