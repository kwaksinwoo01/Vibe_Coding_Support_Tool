from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from word_editor.config import EditorConfig
from word_editor.infrastructure.robust_word_com import RobustWordComGateway
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.services.editor_service import EditorService
from word_editor.ui.main_window import MainWindow


def build_service(normal_path: Path | None = None) -> EditorService:
    config = EditorConfig.default()
    if normal_path is not None:
        config = EditorConfig(
            normal_path=normal_path,
            state_directory=config.state_directory,
            backup_directory=config.backup_directory,
            baseline_path=config.baseline_path,
            debounce_seconds=config.debounce_seconds,
            backup_limit=config.backup_limit,
        )
    config.ensure_directories()
    return EditorService(
        config=config,
        gateway=RobustWordComGateway(
            normal_path=config.normal_path,
            backup_directory=config.backup_directory,
        ),
        store=SnapshotStore(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live editor and merge tool for Microsoft Word Normal.dotm"
    )
    parser.add_argument(
        "--normal-path",
        type=Path,
        help="Override the current user's Normal.dotm path.",
    )
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        parser.error("word-editor requires Windows and desktop Microsoft Word.")

    application = QApplication(sys.argv[:1])
    application.setApplicationName("Word Normal Style Editor")
    window = MainWindow(build_service(args.normal_path))
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
