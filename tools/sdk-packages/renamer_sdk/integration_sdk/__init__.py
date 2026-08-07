"""Repository/environment adapters for ReNamer development tooling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepositoryLayout:
    repository_root: Path
    renamer_setup: Path
    installer: Path
    build_script: Path
    pyproject: Path

    @classmethod
    def from_root(cls, repository_root: Path) -> "RepositoryLayout":
        root = repository_root.resolve()
        project = root / "renamer_setup"
        return cls(
            repository_root=root,
            renamer_setup=project,
            installer=project / "installer" / "ReNamer_Setup.nsi",
            build_script=project / "scripts" / "build.ps1",
            pyproject=project / "pyproject.toml",
        )

    def missing_required_paths(self) -> tuple[Path, ...]:
        required = (self.renamer_setup, self.installer, self.build_script, self.pyproject)
        return tuple(path for path in required if not path.exists())
