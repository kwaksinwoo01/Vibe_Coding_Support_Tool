from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from word_editor.domain.models import TemplateSnapshot


class SnapshotStore:
    def load(self, path: Path) -> TemplateSnapshot:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return TemplateSnapshot.from_dict(payload)

    def save(self, snapshot: TemplateSnapshot, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(
            snapshot.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def save_timestamped(
        self,
        snapshot: TemplateSnapshot,
        directory: Path,
        prefix: str = "normal-dotm-snapshot",
    ) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = directory / f"{prefix}-{timestamp}.json"
        self.save(snapshot, path)
        return path
