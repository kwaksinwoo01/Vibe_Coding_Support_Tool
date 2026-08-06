from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pywintypes

from word_editor.domain.models import PatchOperation, StyleDefinition, TemplateSnapshot
from word_editor.domain.property_policy import property_policy
from word_editor.domain.style_mutation import (
    CreateStyleRequest,
    DeleteStyleRequest,
    cloneable_properties,
    delete_style_blockers,
    validate_new_style_name,
)
from word_editor.domain.validation import validate_snapshot
from word_editor.infrastructure.editable_word_com import EditableWordComGateway
from word_editor.infrastructure.word_com import (
    WD_DO_NOT_SAVE_CHANGES,
    ConcurrentTemplateChange,
    WordGatewayError,
)


class WordStyleSdkGateway(EditableWordComGateway):
    """Fast, mutation-capable style gateway.

    The index path reads only fields required by the style browser. Full COM
    properties are loaded only for selected styles or explicit full audits.
    """

    def _read_style_index(self, style: Any) -> StyleDefinition:
        style_type = self._style_type_name(self._safe_get(style, "Type"))
        local_name = str(self._safe_get(style, "NameLocal", ""))
        original_name = str(self._safe_get(style, "Name", local_name) or local_name)
        raw_id = self._safe_get(style, "ID", None)
        try:
            built_in_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            built_in_id = None
        return StyleDefinition(
            name=local_name,
            original_name=original_name,
            built_in_id=built_in_id,
            style_type=style_type,
            built_in=bool(self._word_bool(self._safe_get(style, "BuiltIn"))),
            in_use=bool(self._word_bool(self._safe_get(style, "InUse"))),
            properties={
                "style.priority": self._safe_get(style, "Priority"),
                "style.hidden": self._word_bool(self._safe_get(style, "Hidden")),
                "style.quick_style": self._word_bool(
                    self._safe_get(style, "QuickStyle")
                ),
            },
        )

    @staticmethod
    def _file_metadata(path: Path) -> dict[str, int]:
        try:
            stat = path.stat()
        except OSError:
            return {}
        return {
            "file_size": int(stat.st_size),
            "file_modified_ns": int(stat.st_mtime_ns),
        }

    def _snapshot_style_index_object(
        self,
        application: Any,
        document: Any,
        source_path: Path,
    ) -> TemplateSnapshot:
        styles: dict[str, StyleDefinition] = {}
        try:
            count = int(document.Styles.Count)
        except (pywintypes.com_error, TypeError, ValueError) as exc:
            raise WordGatewayError(f"스타일 목록을 읽지 못했습니다: {exc}") from exc
        for index in range(1, count + 1):
            try:
                definition = self._read_style_index(document.Styles.Item(index))
            except pywintypes.com_error:
                continue
            if definition.name:
                styles[definition.name] = definition
        metadata: dict[str, Any] = {
            "snapshot_mode": "index",
            "details_loaded": [],
            "style_count": len(styles),
            **self._file_metadata(source_path),
        }
        try:
            first_style = document.Paragraphs.Item(1).Range.Style
            metadata["default_paragraph_style"] = str(
                self._safe_get(first_style, "NameLocal", first_style)
            )
        except (pywintypes.com_error, AttributeError):
            pass
        index_hash = self._snapshot_hash(styles, {})
        metadata["styles_sha256"] = index_hash
        return TemplateSnapshot(
            source_path=str(source_path),
            sha256=index_hash,
            captured_at=datetime.now(timezone.utc).isoformat(),
            word_version=str(application.Version),
            styles=styles,
            list_templates={},
            metadata=metadata,
        )

    def snapshot_path_index(self, path: Path) -> TemplateSnapshot:
        target = self._validate_target(path)
        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=True,
            )
            try:
                return self._snapshot_style_index_object(
                    session.application,
                    document,
                    target,
                )
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass

    def read_style_details(
        self,
        path: Path,
        style_names: list[str] | tuple[str, ...],
    ) -> dict[str, StyleDefinition]:
        target = self._validate_target(path)
        requested = list(dict.fromkeys(style_names))
        if not requested:
            return {}
        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=True,
            )
            try:
                style_index = self._build_style_object_index(document.Styles)
                details: dict[str, StyleDefinition] = {}
                for style_name in requested:
                    style = self._resolve_style_object(
                        style_index,
                        style_name,
                        context="Style detail lookup",
                    )
                    definition = self._read_style(style)
                    details[definition.name] = definition
                return details
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass

    @staticmethod
    def _fingerprint_matches(
        target: Path,
        expected_size: int | None,
        expected_modified_ns: int | None,
    ) -> bool:
        if expected_size is None or expected_modified_ns is None:
            return True
        try:
            stat = target.stat()
        except OSError:
            return False
        return (
            int(stat.st_size) == int(expected_size)
            and int(stat.st_mtime_ns) == int(expected_modified_ns)
        )

    def apply_operations_fast(
        self,
        target_path: Path,
        operations: list[PatchOperation],
        *,
        expected_file_size: int | None,
        expected_modified_ns: int | None,
    ) -> tuple[TemplateSnapshot, Path]:
        target = self._validate_target(target_path)
        if not operations:
            return self.snapshot_path_index(target), Path()
        if not self._fingerprint_matches(
            target,
            expected_file_size,
            expected_modified_ns,
        ):
            raise ConcurrentTemplateChange(
                f"{target.name} 파일이 로드 후 변경되었습니다. 새로고침 후 다시 적용하십시오."
            )

        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=False,
            )
            backup_path = Path()
            applied: list[PatchOperation] = []
            style_index: Any | None = None
            try:
                if not bool(self._safe_get(document, "Saved", True)):
                    raise WordGatewayError(
                        "Word에 저장하지 않은 변경이 있습니다. Word에서 먼저 저장하십시오."
                    )
                style_index = self._build_style_object_index(document.Styles)
                current_details: dict[str, StyleDefinition] = {}
                for style_name in dict.fromkeys(
                    operation.style_name for operation in operations
                ):
                    style_object = self._resolve_style_object(
                        style_index,
                        style_name,
                        context="Patch preflight",
                    )
                    current_details[style_name] = self._read_style(style_object)

                for operation in operations:
                    current = current_details[operation.style_name]
                    actual = current.properties.get(operation.property_name)
                    if actual != operation.expected_old_value:
                        raise ConcurrentTemplateChange(
                            f"{operation.style_name}.{operation.property_name} 값이 "
                            "다른 곳에서 변경되었습니다."
                        )
                    policy = property_policy(current, operation.property_name)
                    if not policy.editable:
                        raise WordGatewayError(
                            f"편집할 수 없는 속성입니다: {operation.style_name}."
                            f"{operation.property_name}: {policy.reason}"
                        )

                backup_path = self._make_target_backup(document, target)
                for operation in operations:
                    style_object = self._resolve_style_object(
                        style_index,
                        operation.style_name,
                        context="Patch operation",
                    )
                    self._set_property(
                        style_object,
                        operation.property_name,
                        operation.value,
                        style_index,
                    )
                    applied.append(operation)

                index_snapshot = self._snapshot_style_index_object(
                    session.application,
                    document,
                    target,
                )
                changed_names = list(
                    dict.fromkeys(operation.style_name for operation in operations)
                )
                for style_name in changed_names:
                    style_object = self._resolve_style_object(
                        style_index,
                        style_name,
                        context="Patch validation",
                    )
                    definition = self._read_style(style_object)
                    index_snapshot.styles[definition.name] = definition
                index_snapshot.metadata["details_loaded"] = changed_names
                errors = [
                    issue
                    for issue in validate_snapshot(index_snapshot)
                    if issue.severity.value == "error"
                ]
                if errors:
                    raise WordGatewayError(
                        "저장 전 검증 실패: "
                        + "; ".join(issue.message for issue in errors)
                    )

                document.Save()
                index_snapshot.metadata.update(self._file_metadata(target))
                return index_snapshot, backup_path
            except Exception:
                if applied and style_index is not None:
                    self._rollback_operations(document, applied, style_index)
                raise
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass

    def create_style_on_path(
        self,
        target_path: Path,
        request: CreateStyleRequest,
        current_snapshot: TemplateSnapshot,
    ) -> tuple[TemplateSnapshot, Path]:
        target = self._validate_target(target_path)
        new_name = validate_new_style_name(current_snapshot, request.name)
        clone_source = (
            current_snapshot.styles.get(request.clone_from)
            if request.clone_from
            else None
        )
        if request.clone_from and clone_source is None:
            raise WordGatewayError(f"복제 원본 스타일을 찾지 못했습니다: {request.clone_from}")
        if clone_source is not None and len(clone_source.properties) <= 3:
            details = self.read_style_details(target, [clone_source.name])
            clone_source = details.get(clone_source.name, clone_source)

        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=False,
            )
            backup = Path()
            created_style: Any = None
            try:
                if not bool(self._safe_get(document, "Saved", True)):
                    raise WordGatewayError(
                        "Word에 저장하지 않은 변경이 있습니다. Word에서 먼저 저장하십시오."
                    )
                backup = self._make_target_backup(document, target)
                try:
                    created_style = document.Styles.Add(
                        Name=new_name,
                        Type=request.style_type.word_type,
                    )
                except pywintypes.com_error as exc:
                    raise WordGatewayError(
                        f"Word가 스타일 생성을 거부했습니다: {new_name}: {exc}"
                    ) from exc

                if clone_source is not None:
                    created_definition = self._read_style(created_style)
                    style_index = self._build_style_object_index(document.Styles)
                    for property_name, value in cloneable_properties(
                        clone_source
                    ).items():
                        policy = property_policy(created_definition, property_name)
                        if not policy.editable:
                            continue
                        try:
                            self._set_property(
                                created_style,
                                property_name,
                                value,
                                style_index,
                            )
                        except (pywintypes.com_error, WordGatewayError):
                            # A style type may expose a property for reading but
                            # reject it during creation. Unsupported clone fields
                            # are skipped rather than corrupting the new style.
                            continue

                document.Save()
                snapshot = self._snapshot_style_index_object(
                    session.application,
                    document,
                    target,
                )
                details = self._read_style(created_style)
                snapshot.styles[details.name] = details
                snapshot.metadata["details_loaded"] = [details.name]
                snapshot.metadata.update(self._file_metadata(target))
                return snapshot, backup
            except Exception:
                if created_style is not None:
                    try:
                        created_style.Delete()
                    except pywintypes.com_error:
                        pass
                raise
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass

    def delete_styles_on_path(
        self,
        target_path: Path,
        request: DeleteStyleRequest,
        current_snapshot: TemplateSnapshot,
    ) -> tuple[TemplateSnapshot, Path]:
        target = self._validate_target(target_path)
        # Deletion is intentionally a full-audit operation. It is infrequent,
        # and reference safety is more important than speed here.
        full_snapshot = self.snapshot_path(target)
        blockers = delete_style_blockers(full_snapshot, request.style_names)
        if blockers:
            details = []
            for blocker in blockers:
                suffix = (
                    "\n    " + "\n    ".join(blocker.referenced_by)
                    if blocker.referenced_by
                    else ""
                )
                details.append(f"- {blocker.style_name}: {blocker.reason}{suffix}")
            raise WordGatewayError(
                "삭제할 수 없는 스타일이 있습니다.\n" + "\n".join(details)
            )

        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=False,
            )
            backup = Path()
            try:
                if not bool(self._safe_get(document, "Saved", True)):
                    raise WordGatewayError(
                        "Word에 저장하지 않은 변경이 있습니다. Word에서 먼저 저장하십시오."
                    )
                backup = self._make_target_backup(document, target)
                style_index = self._build_style_object_index(document.Styles)
                for style_name in request.style_names:
                    style = self._resolve_style_object(
                        style_index,
                        style_name,
                        context="Style deletion",
                    )
                    try:
                        style.Delete()
                    except pywintypes.com_error as exc:
                        raise WordGatewayError(
                            f"Word가 스타일 삭제를 거부했습니다: {style_name}: {exc}"
                        ) from exc
                document.Save()
                snapshot = self._snapshot_style_index_object(
                    session.application,
                    document,
                    target,
                )
                snapshot.metadata.update(self._file_metadata(target))
                return snapshot, backup
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass
