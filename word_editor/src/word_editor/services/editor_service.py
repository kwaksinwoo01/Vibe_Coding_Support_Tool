from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from word_editor.config import EditorConfig
from word_editor.domain.diff import changed_properties, three_way_merge
from word_editor.domain.models import (
    ConflictChoice,
    MergePlan,
    PatchOperation,
    TemplateSnapshot,
    ValidationIssue,
)
from word_editor.domain.validation import validate_snapshot
from word_editor.infrastructure.file_watcher import NormalTemplateWatcher
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.infrastructure.word_com import WordComGateway


class EditorService:
    def __init__(
        self,
        config: EditorConfig,
        gateway: WordComGateway,
        store: SnapshotStore,
    ) -> None:
        self.config = config
        self.gateway = gateway
        self.store = store
        self.current: TemplateSnapshot | None = None
        self.baseline: TemplateSnapshot | None = None
        self._watcher: NormalTemplateWatcher | None = None
        self._last_backup: Path | None = None

    def initialize(self) -> TemplateSnapshot:
        self.config.ensure_directories()
        current = self.refresh()
        if self.config.baseline_path.exists():
            self.baseline = self.store.load(self.config.baseline_path)
        else:
            self.accept_as_baseline(current)
        return current

    def refresh(self) -> TemplateSnapshot:
        self.current = self.gateway.snapshot_normal()
        return self.current

    def accept_as_baseline(
        self,
        snapshot: TemplateSnapshot | None = None,
    ) -> None:
        accepted = snapshot or self._require_current()
        self.store.save(accepted, self.config.baseline_path)
        self.baseline = accepted

    def validate_current(self) -> list[ValidationIssue]:
        return validate_snapshot(self._require_current())

    def export_snapshot(self, directory: Path) -> Path:
        return self.store.save_timestamped(
            self._require_current(),
            directory,
            prefix="normal-dotm-all-styles",
        )

    def apply_style_updates(
        self,
        style_name: str,
        updates: dict[str, Any],
    ) -> TemplateSnapshot:
        current = self._require_current()
        style = current.styles.get(style_name)
        if style is None:
            raise KeyError(f"Style not found: {style_name}")
        operations = [
            PatchOperation(
                style_name=style_name,
                property_name=property_name,
                value=value,
                expected_old_value=style.properties.get(property_name),
            )
            for property_name, value in updates.items()
            if style.properties.get(property_name) != value
        ]
        updated, backup = self.gateway.apply_operations(
            operations,
            expected_snapshot_sha256=current.sha256,
        )
        self.current = updated
        if backup:
            self._last_backup = backup
        issues = [
            issue
            for issue in validate_snapshot(updated)
            if issue.severity.value == "error"
        ]
        if issues:
            if self._last_backup is not None:
                self.gateway.restore_backup(self._last_backup)
                self.refresh()
            messages = "; ".join(issue.message for issue in issues)
            raise RuntimeError(f"Validation failed; backup restored: {messages}")
        self.accept_as_baseline(updated)
        return updated

    def compare_document(self, document_path: Path) -> MergePlan:
        baseline = self.baseline or self._require_current()
        normal = self.refresh()
        document = self.gateway.snapshot_document(document_path)
        return three_way_merge(baseline, normal, document)

    def apply_merge_plan(self, plan: MergePlan) -> TemplateSnapshot:
        current = self._require_current()
        updates: dict[str, dict[str, Any]] = {
            style_name: dict(properties)
            for style_name, properties in plan.automatic_values.items()
        }
        for conflict in plan.conflicts:
            if conflict.choice is ConflictChoice.USE_DOCUMENT:
                value = conflict.document_value
            elif conflict.choice is ConflictChoice.USE_BASELINE:
                value = conflict.baseline_value
            elif conflict.choice is ConflictChoice.MANUAL:
                value = conflict.manual_value
            else:
                value = conflict.normal_value
            updates.setdefault(conflict.style_name, {})[
                conflict.property_name
            ] = value

        operations: list[PatchOperation] = []
        for style_name, properties in updates.items():
            current_style = current.styles.get(style_name)
            if current_style is None:
                # New-style creation is intentionally separate from property merge.
                continue
            for property_name, value in properties.items():
                old = current_style.properties.get(property_name)
                if old != value:
                    operations.append(
                        PatchOperation(
                            style_name=style_name,
                            property_name=property_name,
                            value=value,
                            expected_old_value=old,
                        )
                    )

        updated, backup = self.gateway.apply_operations(
            operations,
            expected_snapshot_sha256=current.sha256,
        )
        self.current = updated
        if backup:
            self._last_backup = backup
        self.accept_as_baseline(updated)
        return updated

    def inject_selected_styles(
        self,
        document_path: Path,
        style_names: list[str],
    ) -> None:
        self.gateway.inject_styles_into_document(document_path, style_names)

    def update_all_document_styles(self, document_path: Path) -> None:
        self.gateway.update_document_from_normal(document_path)

    def start_watching(self, callback: Callable[[], None]) -> None:
        if self._watcher is not None:
            return
        self._watcher = NormalTemplateWatcher(
            self.config.normal_path,
            self.config.debounce_seconds,
            callback,
        )
        self._watcher.start()

    def stop_watching(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    def changes_since_baseline(self) -> dict[str, dict[str, tuple[Any, Any]]]:
        if self.baseline is None:
            return {}
        return changed_properties(self.baseline, self._require_current())

    def _require_current(self) -> TemplateSnapshot:
        if self.current is None:
            raise RuntimeError("Editor service is not initialized.")
        return self.current
