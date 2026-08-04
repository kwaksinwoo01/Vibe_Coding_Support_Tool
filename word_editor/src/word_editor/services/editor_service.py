from __future__ import annotations

from collections.abc import Callable
import hashlib
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
from word_editor.domain.property_policy import assert_property_editable
from word_editor.domain.validation import validate_snapshot
from word_editor.infrastructure.file_watcher import NormalTemplateWatcher
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.infrastructure.editable_word_com import EditableWordComGateway


class EditorService:
    def __init__(
        self,
        config: EditorConfig,
        gateway: EditableWordComGateway,
        store: SnapshotStore,
    ) -> None:
        self.config = config
        self.gateway = gateway
        self.store = store
        self.target_path = config.normal_path.expanduser().resolve()
        self.current: TemplateSnapshot | None = None
        self.baseline: TemplateSnapshot | None = None
        self._watcher: NormalTemplateWatcher | None = None
        self._watch_callback: Callable[[], None] | None = None
        self._last_backup: Path | None = None

    @property
    def is_normal_target(self) -> bool:
        try:
            return self.target_path.resolve() == self.config.normal_path.resolve()
        except OSError:
            return str(self.target_path).casefold() == str(
                self.config.normal_path
            ).casefold()

    @property
    def target_display_name(self) -> str:
        return self.target_path.name

    def _baseline_path_for_target(self) -> Path:
        if self.is_normal_target:
            return self.config.baseline_path
        identity = hashlib.sha256(
            str(self.target_path).casefold().encode("utf-8")
        ).hexdigest()[:16]
        return self.config.state_directory / (
            f"baseline-{self.target_path.stem}-{identity}.json"
        )

    def initialize(self) -> TemplateSnapshot:
        self.config.ensure_directories()
        return self._load_target_state()

    def _load_target_state(self) -> TemplateSnapshot:
        current = self.refresh()
        baseline_path = self._baseline_path_for_target()
        if baseline_path.exists():
            self.baseline = self.store.load(baseline_path)
        else:
            self.accept_as_baseline(current)
        return current

    def select_target(self, path: Path) -> TemplateSnapshot:
        target = path.expanduser().resolve()
        if target == self.target_path:
            return self.refresh()
        was_watching = self._watcher is not None
        callback = self._watch_callback
        self.stop_watching()
        self.target_path = target
        self.current = None
        self.baseline = None
        current = self._load_target_state()
        if was_watching and callback is not None:
            self.start_watching(callback)
        return current

    def select_normal_target(self) -> TemplateSnapshot:
        return self.select_target(self.config.normal_path)

    def refresh(self) -> TemplateSnapshot:
        self.current = self.gateway.snapshot_path(self.target_path)
        return self.current

    def accept_as_baseline(
        self,
        snapshot: TemplateSnapshot | None = None,
    ) -> None:
        accepted = snapshot or self._require_current()
        baseline_path = self._baseline_path_for_target()
        self.store.save(accepted, baseline_path)
        self.baseline = accepted

    def validate_current(self) -> list[ValidationIssue]:
        return validate_snapshot(self._require_current())

    def export_snapshot(self, directory: Path) -> Path:
        safe_stem = "".join(
            character if character.isalnum() or character in "-_" else "-"
            for character in self.target_path.stem
        ).strip("-") or "word-file"
        return self.store.save_timestamped(
            self._require_current(),
            directory,
            prefix=f"{safe_stem}-all-styles",
        )

    def apply_style_updates(
        self,
        style_name: str,
        updates: dict[str, Any],
    ) -> TemplateSnapshot:
        return self.apply_style_updates_many({style_name: updates})

    def apply_style_updates_many(
        self,
        updates_by_style: dict[str, dict[str, Any]],
    ) -> TemplateSnapshot:
        current = self._require_current()
        operations: list[PatchOperation] = []
        for style_name, updates in updates_by_style.items():
            style = current.styles.get(style_name)
            if style is None:
                raise KeyError(f"Style not found: {style_name}")
            for property_name, value in updates.items():
                assert_property_editable(style, property_name)
                old = style.properties.get(property_name)
                if old == value:
                    continue
                operations.append(
                    PatchOperation(
                        style_name=style_name,
                        property_name=property_name,
                        value=value,
                        expected_old_value=old,
                    )
                )

        updated, backup = self.gateway.apply_operations_to_path(
            self.target_path,
            operations,
            expected_snapshot_sha256=current.sha256,
            expected_styles_sha256=str(
                current.metadata.get("styles_sha256") or current.sha256
            ),
        )
        self.current = updated
        if backup:
            self._last_backup = backup

        errors = [
            issue
            for issue in validate_snapshot(updated)
            if issue.severity.value == "error"
        ]
        if errors:
            if self._last_backup is not None:
                self.gateway.restore_backup_to_target(
                    self._last_backup,
                    self.target_path,
                )
                self.refresh()
            messages = "; ".join(issue.message for issue in errors)
            raise RuntimeError(f"Validation failed; backup restored: {messages}")

        self.accept_as_baseline(updated)
        return updated

    def compare_document(self, document_path: Path) -> MergePlan:
        baseline = self.baseline or self._require_current()
        target = self.refresh()
        document = self.gateway.snapshot_document(document_path)
        return three_way_merge(baseline, target, document)

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
        return self.apply_style_updates_many(updates)

    def inject_selected_styles(
        self,
        document_path: Path,
        style_names: list[str],
    ) -> None:
        self.gateway.inject_styles(
            self.target_path,
            document_path,
            style_names,
        )

    def update_all_document_styles(self, document_path: Path) -> None:
        if self.is_normal_target:
            self.gateway.update_document_from_normal(document_path)
            return
        self.gateway.inject_styles(
            self.target_path,
            document_path,
            list(self._require_current().styles),
        )

    def start_watching(self, callback: Callable[[], None]) -> None:
        self._watch_callback = callback
        if self._watcher is not None:
            return
        self._watcher = NormalTemplateWatcher(
            self.target_path,
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
