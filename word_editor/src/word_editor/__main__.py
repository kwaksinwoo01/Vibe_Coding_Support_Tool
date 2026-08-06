from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from word_editor.config import EditorConfig
from word_editor.infrastructure.production_word_gateway import ProductionWordGateway
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.services.company_template_lifecycle_service import (
    CompanyTemplateLifecycleService,
)
from word_editor.services.editor_service import EditorService
from word_editor.services.template_lifecycle_service import TemplateLifecycleService
from word_editor.ui.header_footer_management_window import (
    HeaderFooterManagementWindow,
)


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
    gateway = ProductionWordGateway(
        normal_path=config.normal_path,
        backup_directory=config.backup_directory,
    )
    snapshot_store = SnapshotStore()
    editor_service = EditorService(
        config=config,
        gateway=gateway,
        store=snapshot_store,
    )
    lifecycle_service = CompanyTemplateLifecycleService(
        config=config,
        gateway=gateway,
        snapshot_store=snapshot_store,
    )
    return editor_service, lifecycle_service


def build_service(normal_path: Path | None = None) -> EditorService:
    """Compatibility helper for tests and callers that need only the editor."""

    editor_service, _ = build_services(normal_path)
    return editor_service


def _load_status(service: EditorService) -> str:
    snapshot = service.current
    if snapshot is None:
        return "초기 로드 정보 없음"
    source = str(snapshot.metadata.get("load_source") or "unknown")
    duration = snapshot.metadata.get("load_duration_ms")
    source_label = {
        "disk-cache": "디스크 캐시",
        "word-fast-index": "Word 빠른 인덱스",
        "word-full-scan": "Word 전체 스캔",
    }.get(source, source)
    if duration is None:
        return f"로드 경로: {source_label}"
    return f"로드 경로: {source_label} · {duration} ms"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Company Word template, style, and header/footer asset manager"
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
    window = HeaderFooterManagementWindow(
        editor_service,
        lifecycle_service,
    )
    window.show()
    window.statusBar().showMessage(_load_status(editor_service), 12000)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
