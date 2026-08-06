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
from word_editor.domain.property_policy import (
    assert_property_editable,
    property_policy,
)
from word_editor.domain.style_mutation import (
    CreateStyleRequest,
    CreateStyleType,
    DeleteStyleRequest,
)
from word_editor.domain.validation import validate_snapshot
from word_editor.infrastructure.file_watcher import NormalTemplateWatcher
from word_editor.infrastructure.snapshot_cache import SnapshotCache
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.infrastructure.word_style_sdk import WordStyleSdkGateway
from word_editor.services.fast_style_compare import FastStyleCompareService


class EditorService:
    def __init__(
        self,
        config: EditorConfig,
        gateway: WordStyleSdkGateway,
        store: SnapshotStore,
    ) -> None:
        self.config = config
        self.gateway = gateway
        self.store = store
        self.cache = SnapshotCache(config.state_directory / "snapshot-cache")
        self.fast_compare = FastStyleCompareService(gateway)
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
        current = self.refresh(force=False)
        baseline_path = self._baseline_path_for_target()
        if baseline_path.exists():
            self.baseline = self.store.load(baseline_path)
        else:
            self.accept_as_baseline(current)
        return current

    def select_target(self, path: Path) -> TemplateSnapshot:
        target = path.expanduser().resolve()
        if target == self.target_path:
            return self.refresh(force=False)
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

    def refresh(
        self,
        *,
        force: bool = False,
        full: bool = False,
    ) -> TemplateSnapshot:
        mode = "full" if full else "index"
        if full:
            capture = lambda: self.gateway.snapshot_path(self.target_path)
        else:
            capture = lambda: self.gateway.snapshot_path_index(
                self.target_path
            )
        snapshot = self.cache.get_or_capture(
            self.target_path,
            mode,
            capture,
            force=force,
        )
        self.current = snapshot
        return snapshot

    def ensure_style_details(
        self,
        style_names: list[str] | tuple[str, ...],
    ) -> TemplateSnapshot:
        current = self._require_current()
        requested = list(dict.fromkeys(style_names))
        loaded = set(current.metadata.get("details_loaded", []))
        missing = [
            name
            for name in requested
            if name in current.styles
            and (
                name not in loaded
                or len(current.styles[name].properties) <= 3
            )
        ]
        if not missing:
            return current
        details = self.gateway.read_style_details(self.target_path, missing)
        for name, definition in details.items():
            current.styles[name] = definition
            loaded.add(name)
        current.metadata["details_loaded"] = sorted(loaded, key=str.casefold)
        self.cache.save(self.target_path, "index", current)
        return current

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
        full_snapshot = self.refresh(force=True, full=True)
        safe_stem = "".join(
            character if character.isalnum() or character in "-_" else "-"
            for character in self.target_path.stem
        ).strip("-") or "word-file"
        return self.store.save_timestamped(
            full_snapshot,
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
        if not updates_by_style:
            return self._require_current()
        self.ensure_style_details(list(updates_by_style))
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
        if not operations:
            return current

        updated, backup = self.gateway.apply_operations_fast(
            self.target_path,
            operations,
            expected_file_size=self._metadata_int(current, "file_size"),
            expected_modified_ns=self._metadata_int(
                current,
                "file_modified_ns",
            ),
        )
        self.current = updated
        if backup:
            self._last_backup = backup
        self.cache.invalidate(self.target_path)
        self.cache.save(self.target_path, "index", updated)
        self.accept_as_baseline(updated)
        return updated

    @staticmethod
    def _metadata_int(snapshot: TemplateSnapshot, name: str) -> int | None:
        value = snapshot.metadata.get(name)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def create_style(self, request: CreateStyleRequest) -> TemplateSnapshot:
        current = self._require_current()
        updated, backup = self.gateway.create_style_on_path(
            self.target_path,
            request,
            current,
        )
        self.current = updated
        if backup:
            self._last_backup = backup
        self.cache.invalidate(self.target_path)
        self.cache.save(self.target_path, "index", updated)
        self.accept_as_baseline(updated)
        return updated

    def delete_styles(self, request: DeleteStyleRequest) -> TemplateSnapshot:
        current = self._require_current()
        updated, backup = self.gateway.delete_styles_on_path(
            self.target_path,
            request,
            current,
        )
        self.current = updated
        if backup:
            self._last_backup = backup
        self.cache.invalidate(self.target_path)
        self.cache.save(self.target_path, "index", updated)
        self.accept_as_baseline(updated)
        return updated

    def compare_document(self, document_path: Path) -> MergePlan:
        incoming_path = document_path.expanduser().resolve()
        fast_plan = self.fast_compare.compare_or_none(
            self.target_path,
            incoming_path,
        )
        if fast_plan is not None:
            return fast_plan

        target = self.cache.get_or_capture(
            self.target_path,
            "full",
            lambda: self.gateway.snapshot_path(self.target_path),
        )
        document = self.cache.get_or_capture(
            incoming_path,
            "full",
            lambda: self.gateway.snapshot_path(incoming_path),
        )
        baseline = self.baseline or target
        if baseline.metadata.get("snapshot_mode") == "index":
            baseline = target
        self.current = target
        return three_way_merge(baseline, target, document)

    @staticmethod
    def _create_type(style_type: str) -> CreateStyleType:
        return {
            "Character": CreateStyleType.CHARACTER,
            "Table": CreateStyleType.TABLE,
            "List": CreateStyleType.LIST,
        }.get(style_type, CreateStyleType.PARAGRAPH)

    def apply_merge_plan(self, plan: MergePlan) -> TemplateSnapshot:
        current = self._require_current()
        for style_name in plan.added_styles:
            if style_name in current.styles:
                continue
            definition = plan.added_style_definitions.get(style_name)
            if definition is None:
                continue
            current = self.create_style(
                CreateStyleRequest(
                    name=style_name,
                    style_type=self._create_type(definition.style_type),
                )
            )

        updates: dict[str, dict[str, Any]] = {
            style_name: dict(properties)
            for style_name, properties in plan.automatic_values.items()
            if style_name in self._require_current().styles
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

        if updates:
            self.ensure_style_details(list(updates))
            current = self._require_current()
            safe_updates: dict[str, dict[str, Any]] = {}
            for style_name, properties in updates.items():
                style = current.styles.get(style_name)
                if style is None:
                    continue
                for property_name, value in properties.items():
                    if property_policy(style, property_name).editable:
                        safe_updates.setdefault(style_name, {})[
                            property_name
                        ] = value
            if safe_updates:
                return self.apply_style_updates_many(safe_updates)
        return self._require_current()

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
        self.cache.invalidate(document_path)

    def update_all_document_styles(self, document_path: Path) -> None:
        if self.is_normal_target:
            self.gateway.update_document_from_normal(document_path)
        else:
            self.gateway.inject_styles(
                self.target_path,
                document_path,
                list(self._require_current().styles),
            )
        self.cache.invalidate(document_path)

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

    def close(self) -> None:
        self.stop_watching()
        close_gateway = getattr(self.gateway, "close", None)
        if callable(close_gateway):
            close_gateway()

    def _require_current(self) -> TemplateSnapshot:
        if self.current is None:
            raise RuntimeError("Editor service is not initialized.")
        return self.current
