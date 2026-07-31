from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Lock, Timer

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class _NormalFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        target: Path,
        debounce_seconds: float,
        callback: Callable[[], None],
    ) -> None:
        super().__init__()
        self._target = target.resolve()
        self._debounce_seconds = debounce_seconds
        self._callback = callback
        self._timer: Timer | None = None
        self._lock = Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        candidates = [Path(event.src_path)]
        destination = getattr(event, "dest_path", None)
        if destination:
            candidates.append(Path(destination))
        if not any(path.resolve() == self._target for path in candidates):
            return
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = Timer(self._debounce_seconds, self._callback)
            self._timer.daemon = True
            self._timer.start()

    def close(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class NormalTemplateWatcher:
    def __init__(
        self,
        normal_path: Path,
        debounce_seconds: float,
        callback: Callable[[], None],
    ) -> None:
        self._handler = _NormalFileHandler(
            normal_path,
            debounce_seconds,
            callback,
        )
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(normal_path.parent),
            recursive=False,
        )

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._handler.close()
        self._observer.stop()
        self._observer.join(timeout=5)
