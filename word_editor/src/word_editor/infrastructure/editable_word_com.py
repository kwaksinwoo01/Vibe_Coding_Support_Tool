from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from typing import Any

import pywintypes

from word_editor.domain.models import PatchOperation, StyleDefinition, TemplateSnapshot
from word_editor.domain.property_policy import assert_property_editable
from word_editor.infrastructure.word_com import (
    WD_DO_NOT_SAVE_CHANGES,
    WordComGateway,
    WordGatewayError,
    ConcurrentTemplateChange,
)

SUPPORTED_WORD_FILES = frozenset({".docx", ".docm", ".dotx", ".dotm"})


class EditableWordComGateway(WordComGateway):
    """Word gateway that can edit Normal.dotm or another Word file safely."""

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
                    document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)

    def _make_target_backup(self, document: Any, target: Path) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self.backup_directory / (
            f"{target.stem}.{timestamp}.before-word-editor{target.suffix}"
        )
        document.SaveCopyAs(str(destination))
        return destination

    def apply_operations_to_path(
        self,
        target_path: Path,
        operations: list[PatchOperation],
        expected_snapshot_sha256: str,
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
            try:
                current = self._snapshot_document_object(
                    session.application,
                    document,
                    target,
                )
                if current.sha256 != expected_snapshot_sha256:
                    raise ConcurrentTemplateChange(
                        f"{target.name} changed after the editor loaded it. "
                        "Refresh and merge before applying."
                    )

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
                    style = document.Styles.Item(operation.style_name)
                    self._set_property(
                        style,
                        operation.property_name,
                        operation.value,
                    )

                document.Save()
                updated = self._snapshot_document_object(
                    session.application,
                    document,
                    target,
                )
                return updated, backup_path
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
