from __future__ import annotations

import json
from pathlib import Path
import tempfile

from word_editor.domain.template_lifecycle import TemplateRegistry


class TemplateRegistryStore:
    def load(self, path: Path) -> TemplateRegistry:
        if not path.exists():
            return TemplateRegistry()
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return TemplateRegistry.from_dict(payload)

    def save(self, registry: TemplateRegistry, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(
            registry.to_dict(),
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
