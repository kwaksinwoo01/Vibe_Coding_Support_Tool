from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from word_editor.config import EditorConfig
from word_editor.infrastructure.robust_word_com import RobustWordComGateway
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.services.editor_service import EditorService
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleService,
)
from word_editor.ui.company_template_window import CompanyTemplateWindow


def build_services(
    normal_path: Path | None = None,
) -> tuple[EditorService, TemplateLifecycleService]:
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
    gateway = RobustWordComGateway(
        normal_path=config.normal_path,
        backup_directory=config.backup_directory,
    )
    snapshot_store = SnapshotStore()
    editor_service = EditorService(
        config=config,
        gateway=gateway,
        store=snapshot_store,
    )
    lifecycle_service = TemplateLifecycleService(
        config=config,
        gateway=gateway,
        snapshot_store=snapshot_store,
    )
    return editor_service, lifecycle_service


def build_service(normal_path: Path | None = None) -> EditorService:
    """Compatibility helper for tests and callers that need only the editor."""

    editor_service, _ = build_services(normal_path)
    return editor_service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live editor and lifecycle manager for Microsoft Word templates"
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
    application.setApplicationName("Company Word Template Manager")
    editor_service, lifecycle_service = build_services(args.normal_path)
    window = CompanyTemplateWindow(editor_service, lifecycle_service)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
