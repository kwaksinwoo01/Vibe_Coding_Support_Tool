from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from typing import Any

import pywintypes

from word_editor.domain.models import (
    PatchOperation,
    StyleDefinition,
    TemplateSnapshot,
    normalize_word_boolean,
)
from word_editor.domain.property_policy import assert_property_editable
from word_editor.domain.validation import validate_snapshot
from word_editor.infrastructure.word_com import (
    WD_DO_NOT_SAVE_CHANGES,
    WordComGateway,
    WordGatewayError,
    ConcurrentTemplateChange,
)

SUPPORTED_WORD_FILES = frozenset({".docx", ".docm", ".dotx", ".dotm"})
RPC_E_DISCONNECTED = -2147417848


class EditableWordComGateway(WordComGateway):
    """Word gateway that can edit Normal.dotm or another Word file safely."""

    @staticmethod
    def _word_bool(value: Any) -> bool | int | None:
        normalized = normalize_word_boolean(value)
        if normalized is None or isinstance(normalized, (bool, int)):
            return normalized
        return None

    def _read_style(self, style: Any) -> StyleDefinition:
        definition = super()._read_style(style)
        original_name = self._safe_get(style, "Name", definition.name)
        if not original_name:
            original_name = definition.name
        raw_id = self._safe_get(style, "ID", None)
        try:
            built_in_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            built_in_id = None
        definition.original_name = str(original_name)
        definition.built_in_id = built_in_id
        return definition

    def _is_normal_path(self, path: Path) -> bool:
        try:
            return path.resolve() == self.normal_path.resolve()
        except OSError:
            return str(path).casefold() == str(self.normal_path).casefold()

    @staticmethod
    def _validate_target(path: Path) -> Path:
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise WordGatewayError(f"Word file not found: {resolved}")
        if resolved.suffix.casefold() not in SUPPORTED_WORD_FILES:
            raise WordGatewayError(
                "Unsupported Word file type. Supported: "
                + ", ".join(sorted(SUPPORTED_WORD_FILES))
            )
        return resolved

    @staticmethod
    def _same_path(left: Path, right: Path) -> bool:
        try:
            return left.resolve() == right.resolve()
        except OSError:
            return str(left).casefold() == str(right).casefold()

    def _find_open_document(self, application: Any, path: Path) -> Any | None:
        try:
            count = int(application.Documents.Count)
        except (pywintypes.com_error, TypeError, ValueError):
            return None
        for index in range(1, count + 1):
            try:
                document = application.Documents.Item(index)
                full_name = str(document.FullName)
                if full_name and self._same_path(Path(full_name), path):
                    return document
            except (pywintypes.com_error, OSError, ValueError):
                continue
        return None

    def _open_target(
        self,
        application: Any,
        path: Path,
        read_only: bool,
    ) -> tuple[Any, bool]:
        if self._is_normal_path(path):
            return application.NormalTemplate.OpenAsDocument(), True
        open_document = self._find_open_document(application, path)
        if open_document is not None:
            if not read_only and bool(self._safe_get(open_document, "ReadOnly", False)):
                raise WordGatewayError(
                    f"The open Word document is read-only: {path}"
                )
            return open_document, False
        document = application.Documents.Open(
            FileName=str(path),
            ReadOnly=read_only,
            AddToRecentFiles=False,
            Visible=False,
        )
        return document, True

    def snapshot_path(self, path: Path) -> TemplateSnapshot:
        target = self._validate_target(path)
        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=True,
            )
            try:
                return self._snapshot_document_object(
                    session.application,
                    document,
                    target,
                )
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error as exc:
                        # Word can disconnect an automation proxy after a
                        # hidden template window has already closed. The
                        # completed snapshot remains valid in that case.
                        if getattr(exc, "hresult", None) != RPC_E_DISCONNECTED:
                            raise

    def _make_target_backup(self, document: Any, target: Path) -> Path:
        del document
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = self.backup_directory / (
            f"{target.stem}.{timestamp}.before-word-editor{target.suffix}"
        )
        try:
            shutil.copy2(target, destination)
        except OSError as exc:
            raise WordGatewayError(
                f"Failed to back up {target.name} to {destination}: {exc}"
            ) from exc
        return destination

    def _rollback_operations(
        self,
        document: Any,
        applied_operations: list[PatchOperation],
        style_index: Any,
    ) -> None:
        for operation in reversed(applied_operations):
            try:
                style = self._resolve_style_object(
                    style_index,
                    operation.style_name,
                    context="Rollback operation",
                )
                self._set_property(
                    style,
                    operation.property_name,
                    operation.expected_old_value,
                    style_index,
                )
            except Exception:
                # The timestamped backup remains available if Word rejects an
                # individual in-memory rollback property.
                continue

    def apply_operations_to_path(
        self,
        target_path: Path,
        operations: list[PatchOperation],
        expected_snapshot_sha256: str,
        expected_styles_sha256: str | None = None,
    ) -> tuple[TemplateSnapshot, Path]:
        target = self._validate_target(target_path)
        if not operations:
            return self.snapshot_path(target), Path()

        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=False,
            )
            backup_path: Path | None = None
            applied_operations: list[PatchOperation] = []
            style_index: Any | None = None
            saved = False
            try:
                if not bool(self._safe_get(document, "Saved", True)):
                    raise WordGatewayError(
                        "Word has unsaved changes in the template or document. "
                        f"Save it in Word before editing styles: {target}"
                    )
                current = self._snapshot_document_object(
                    session.application,
                    document,
                    target,
                )
                current_styles_sha256 = str(
                    current.metadata.get("styles_sha256") or current.sha256
                )
                expected_styles_sha256 = (
                    expected_styles_sha256 or expected_snapshot_sha256
                )
                if current_styles_sha256 != expected_styles_sha256:
                    raise ConcurrentTemplateChange(
                        f"{target.name} changed after the editor loaded it. "
                        "Refresh and merge before applying."
                    )

                style_index = self._build_style_object_index(document.Styles)
                backup_path = self._make_target_backup(document, target)
                for operation in operations:
                    definition = current.styles.get(operation.style_name)
                    if definition is None:
                        raise WordGatewayError(
                            f"Style not found: {operation.style_name}"
                        )
                    assert_property_editable(
                        definition,
                        operation.property_name,
                    )
                    actual_old = definition.properties.get(
                        operation.property_name
                    )
                    if actual_old != operation.expected_old_value:
                        raise ConcurrentTemplateChange(
                            f"{operation.style_name}."
                            f"{operation.property_name} changed concurrently."
                        )
                    style = self._resolve_style_object(
                        style_index,
                        operation.style_name,
                        context="Patch operation",
                    )
                    applied_operations.append(operation)
                    try:
                        self._set_property(
                            style,
                            operation.property_name,
                            operation.value,
                            style_index,
                        )
                    except pywintypes.com_error as exc:
                        raise WordGatewayError(
                            "Word rejected the style update "
                            f"{operation.style_name}.{operation.property_name}="
                            f"{operation.value!r}: {exc}"
                        ) from exc

                provisional = self._snapshot_document_object(
                    session.application,
                    document,
                    target,
                )
                errors = [
                    issue
                    for issue in validate_snapshot(provisional)
                    if issue.severity.value == "error"
                ]
                if errors:
                    messages = "; ".join(issue.message for issue in errors)
                    raise WordGatewayError(
                        "Validation failed before save; changes were rolled back: "
                        + messages
                    )

                document.Save()
                saved = True
                try:
                    provisional.metadata["file_modified_at"] = (
                        target.stat().st_mtime
                    )
                except OSError:
                    pass
                return provisional, backup_path
            except Exception:
                if not saved and applied_operations and style_index is not None:
                    self._rollback_operations(
                        document,
                        applied_operations,
                        style_index,
                    )
                raise
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass

    def restore_backup_to_target(
        self,
        backup_path: Path,
        target_path: Path,
    ) -> None:
        target = self._validate_target(target_path)
        if not backup_path.exists():
            raise WordGatewayError(f"Backup not found: {backup_path}")
        if self._is_normal_path(target):
            super().restore_backup(backup_path)
            return
        shutil.copy2(backup_path, target)

    def inject_styles(
        self,
        source_path: Path,
        destination_path: Path,
        style_names: list[str],
    ) -> None:
        source = self._validate_target(source_path)
        destination = self._validate_target(destination_path)
        if source == destination:
            raise WordGatewayError("Source and destination Word files are identical.")
        with self._session() as session:
            for style_name in style_names:
                session.application.OrganizerCopy(
                    Source=str(source),
                    Destination=str(destination),
                    Name=style_name,
                    Object=3,
                )
