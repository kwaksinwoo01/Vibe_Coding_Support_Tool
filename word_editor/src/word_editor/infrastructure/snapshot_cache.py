from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Callable

from word_editor.domain.models import TemplateSnapshot


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    size: int
    modified_ns: int
    content_sha256: str

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @classmethod
    def capture(cls, path: Path) -> "FileFingerprint":
        stat = path.stat()
        return cls(
            size=int(stat.st_size),
            modified_ns=int(stat.st_mtime_ns),
            content_sha256=cls._sha256(path),
        )

    def to_dict(self) -> dict[str, int | str]:
        return {
            "size": self.size,
            "modified_ns": self.modified_ns,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "FileFingerprint":
        return cls(
            size=int(value.get("size", -1)),
            modified_ns=int(value.get("modified_ns", -1)),
            content_sha256=str(value.get("content_sha256", "")),
        )


class SnapshotCache:
    """Disk-backed cache verified by path, metadata, and file SHA-256."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _identity(path: Path) -> str:
        resolved = str(path.expanduser().resolve()).casefold()
        return hashlib.sha256(resolved.encode("utf-8")).hexdigest()

    def _path(self, source: Path, mode: str) -> Path:
        return self.directory / f"{self._identity(source)}-{mode}.json"

    def load(self, source: Path, mode: str) -> TemplateSnapshot | None:
        cache_path = self._path(source, mode)
        if not cache_path.exists() or not source.exists():
            return None
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8-sig"))
            cached_fingerprint = FileFingerprint.from_dict(
                dict(payload.get("fingerprint", {}))
            )
            if cached_fingerprint != FileFingerprint.capture(source):
                return None
            return TemplateSnapshot.from_dict(dict(payload["snapshot"]))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def save(
        self,
        source: Path,
        mode: str,
        snapshot: TemplateSnapshot,
    ) -> None:
        if not source.exists():
            return
        cache_path = self._path(source, mode)
        payload = {
            "fingerprint": FileFingerprint.capture(source).to_dict(),
            "snapshot": snapshot.to_dict(),
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="\n",
            dir=cache_path.parent,
            prefix=f".{cache_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        temp_path.replace(cache_path)

    def get_or_capture(
        self,
        source: Path,
        mode: str,
        capture: Callable[[], TemplateSnapshot],
        *,
        force: bool = False,
    ) -> TemplateSnapshot:
        started = time.perf_counter()
        if not force:
            cached = self.load(source, mode)
            if cached is not None:
                cached.metadata["cache_hit"] = True
                cached.metadata["load_source"] = "disk-cache"
                cached.metadata["load_mode"] = mode
                cached.metadata["load_duration_ms"] = round(
                    (time.perf_counter() - started) * 1000,
                    2,
                )
                return cached
        snapshot = capture()
        snapshot.metadata["cache_hit"] = False
        snapshot.metadata["load_source"] = (
            "word-full-scan" if mode == "full" else "word-fast-index"
        )
        snapshot.metadata["load_mode"] = mode
        snapshot.metadata["load_duration_ms"] = round(
            (time.perf_counter() - started) * 1000,
            2,
        )
        self.save(source, mode, snapshot)
        return snapshot

    def invalidate(self, source: Path) -> None:
        identity = self._identity(source)
        for path in self.directory.glob(f"{identity}-*.json"):
            try:
                path.unlink()
            except OSError:
                pass
