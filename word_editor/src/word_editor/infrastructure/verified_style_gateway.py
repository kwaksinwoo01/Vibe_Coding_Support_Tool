from __future__ import annotations

from pathlib import Path
from typing import Any

import pywintypes

from word_editor.domain.models import PatchOperation, TemplateSnapshot
from word_editor.domain.style_mutation import CreateStyleRequest, DeleteStyleRequest
from word_editor.infrastructure.safe_backup_style_gateway import (
    SafeBackupStyleGateway,
)
from word_editor.infrastructure.word_com import (
    WD_DO_NOT_SAVE_CHANGES,
    WordGatewayError,
)


class VerifiedStyleGateway(SafeBackupStyleGateway):
    """Verify every saved style mutation by reading it back from Word."""

    @staticmethod
    def _same_value(left: Any, right: Any) -> bool:
        if isinstance(left, float) and isinstance(right, (int, float)):
            return abs(left - float(right)) < 0.0001
        if isinstance(right, float) and isinstance(left, (int, float)):
            return abs(float(left) - right) < 0.0001
        return left == right

    def _restore_properties(
        self,
        target: Path,
        operations: list[PatchOperation],
    ) -> list[str]:
        errors: list[str] = []
        with self._session() as session:
            document, owns_document = self._open_target(
                session.application,
                target,
                read_only=False,
            )
            try:
                style_index = self._build_style_object_index(document.Styles)
                for operation in reversed(operations):
                    try:
                        style = self._resolve_style_object(
                            style_index,
                            operation.style_name,
                            context="Post-save verification rollback",
                        )
                        self._set_property(
                            style,
                            operation.property_name,
                            operation.expected_old_value,
                            style_index,
                        )
                    except Exception as exc:
                        errors.append(
                            f"{operation.style_name}."
                            f"{operation.property_name}: {exc}"
                        )
                if not errors:
                    document.Save()
            except Exception as exc:
                errors.append(str(exc))
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass
        return errors

    def apply_operations_fast(
        self,
        target_path: Path,
        operations: list[PatchOperation],
        *,
        expected_file_size: int | None,
        expected_modified_ns: int | None,
    ) -> tuple[TemplateSnapshot, Path]:
        updated, backup = super().apply_operations_fast(
            target_path,
            operations,
            expected_file_size=expected_file_size,
            expected_modified_ns=expected_modified_ns,
        )
        if not operations:
            return updated, backup

        target = self._validate_target(target_path)
        names = list(dict.fromkeys(item.style_name for item in operations))
        details = self.read_style_details(target, names)
        mismatches: list[str] = []
        for operation in operations:
            style = details.get(operation.style_name)
            actual = (
                None
                if style is None
                else style.properties.get(operation.property_name)
            )
            if style is None or not self._same_value(actual, operation.value):
                mismatches.append(
                    f"{operation.style_name}.{operation.property_name}: "
                    f"요청={operation.value!r}, 저장 후={actual!r}"
                )

        if mismatches:
            rollback_errors = self._restore_properties(target, operations)
            rollback_text = (
                "이전 속성값으로 되돌렸습니다."
                if not rollback_errors
                else "자동 되돌리기에도 오류가 있었습니다:\n- "
                + "\n- ".join(rollback_errors)
            )
            raise WordGatewayError(
                "Word 저장 후 검증에서 요청값과 실제값이 일치하지 않았습니다.\n- "
                + "\n- ".join(mismatches)
                + f"\n{rollback_text}\n전체 백업: {backup}"
            )

        for name, definition in details.items():
            updated.styles[name] = definition
        updated.metadata["post_save_verified"] = True
        updated.metadata["verified_styles"] = names
        return updated, backup

    def create_style_on_path(
        self,
        target_path: Path,
        request: CreateStyleRequest,
        current_snapshot: TemplateSnapshot,
    ) -> tuple[TemplateSnapshot, Path]:
        updated, backup = super().create_style_on_path(
            target_path,
            request,
            current_snapshot,
        )
        target = self._validate_target(target_path)
        index = self.snapshot_path_index(target)
        created_name = request.name.strip()
        if created_name not in index.styles:
            raise WordGatewayError(
                "Word가 저장 완료를 반환했지만 새 스타일이 다시 조회되지 않습니다: "
                f"{created_name}\n전체 백업: {backup}"
            )
        details = self.read_style_details(target, [created_name])
        updated.styles[created_name] = details[created_name]
        updated.metadata["post_save_verified"] = True
        updated.metadata["verified_styles"] = [created_name]
        return updated, backup

    def delete_styles_on_path(
        self,
        target_path: Path,
        request: DeleteStyleRequest,
        current_snapshot: TemplateSnapshot,
    ) -> tuple[TemplateSnapshot, Path]:
        updated, backup = super().delete_styles_on_path(
            target_path,
            request,
            current_snapshot,
        )
        target = self._validate_target(target_path)
        index = self.snapshot_path_index(target)
        remaining = [
            name for name in request.style_names if name in index.styles
        ]
        if remaining:
            raise WordGatewayError(
                "Word가 저장 완료를 반환했지만 삭제된 스타일이 다시 조회됩니다:\n- "
                + "\n- ".join(remaining)
                + f"\n전체 백업: {backup}"
            )
        updated.metadata["post_save_verified"] = True
        updated.metadata["verified_deleted_styles"] = list(
            request.style_names
        )
        return updated, backup
