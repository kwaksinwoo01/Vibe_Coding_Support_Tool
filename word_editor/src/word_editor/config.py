from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class EditorConfig:
    normal_path: Path
    state_directory: Path
    backup_directory: Path
    baseline_path: Path
    debounce_seconds: float = 0.8
    backup_limit: int = 30

    @classmethod
    def default(cls) -> "EditorConfig":
        appdata = Path(os.environ.get("APPDATA", Path.home()))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        normal_path = appdata / "Microsoft" / "Templates" / "Normal.dotm"
        state_directory = local_appdata / "WordNormalStyleEditor"
        return cls(
            normal_path=normal_path,
            state_directory=state_directory,
            backup_directory=state_directory / "backups",
            baseline_path=state_directory / "baseline.json",
        )

    def ensure_directories(self) -> None:
        self.state_directory.mkdir(parents=True, exist_ok=True)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
