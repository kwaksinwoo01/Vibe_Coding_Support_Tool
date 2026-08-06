from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
)

from word_editor.domain.style_mutation import (
    CreateStyleRequest,
    CreateStyleType,
    DeleteStyleRequest,
)
from word_editor.services.editor_service import EditorService
from word_editor.services.template_lifecycle_service import TemplateLifecycleService
from word_editor.ui.company_template_window import CompanyTemplateWindow


class StyleManagementWindow(CompanyTemplateWindow):
    """Company template window with lazy style details and context actions."""

    def __init__(
        self,
        service: EditorService,
        lifecycle: TemplateLifecycleService,
    ) -> None:
        super().__init__(service, lifecycle)
        for style_list in self._all_style_lists():
            style_list.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            style_list.customContextMenuRequested.connect(
                lambda point, widget=style_list: self._show_style_context_menu(
                    widget,
                    point,
                )
            )

    def _load_selected_styles(self) -> None:
        selected = self._selected_style_names()
        if selected:
            try:
                self.service.ensure_style_details(selected)
            except Exception as exc:
                QMessageBox.critical(self, "스타일 상세 조회 실패", str(exc))
                return
        super()._load_selected_styles()

    def _show_style_context_menu(
        self,
        widget: QListWidget,
        point: QPoint,
    ) -> None:
        item = widget.itemAt(point)
        if item is not None and not item.isSelected():
            widget.clearSelection()
            item.setSelected(True)
            widget.setCurrentItem(item)

        menu = QMenu(widget)
        create_action = menu.addAction("새 스타일 만들기…")
        duplicate_action = menu.addAction("선택 스타일 복제…")
        delete_action = menu.addAction("선택 스타일 삭제…")
        menu.addSeparator()
        detail_action = menu.addAction("선택 스타일 상세 다시 읽기")

        selected = self._selected_style_names()
        duplicate_action.setEnabled(len(selected) == 1)
        delete_action.setEnabled(bool(selected))
        detail_action.setEnabled(bool(selected))

        chosen = menu.exec(widget.mapToGlobal(point))
        if chosen is create_action:
            self._create_style()
        elif chosen is duplicate_action:
            self._duplicate_style()
        elif chosen is delete_action:
            self._delete_selected_styles()
        elif chosen is detail_action:
            self._reload_selected_style_details()

    @staticmethod
    def _style_type_options() -> list[tuple[str, CreateStyleType]]:
        return [
            ("문단 스타일", CreateStyleType.PARAGRAPH),
            ("문자 스타일", CreateStyleType.CHARACTER),
            ("표 스타일", CreateStyleType.TABLE),
            ("목록 스타일", CreateStyleType.LIST),
        ]

    def _create_style(self) -> None:
        options = self._style_type_options()
        label, accepted = QInputDialog.getItem(
            self,
            "새 스타일 종류",
            "스타일 종류:",
            [item[0] for item in options],
            0,
            False,
        )
        if not accepted:
            return
        name, accepted = QInputDialog.getText(
            self,
            "새 스타일 이름",
            "Word 스타일 이름:",
        )
        if not accepted or not name.strip():
            return
        style_type = dict(options)[label]
        try:
            snapshot = self.service.create_style(
                CreateStyleRequest(name=name, style_type=style_type)
            )
        except Exception as exc:
            QMessageBox.critical(self, "스타일 생성 실패", str(exc))
            return
        created_name = name.strip()
        self._populate_styles(snapshot.styles, [created_name])
        self._show_validation()
        self.statusBar().showMessage(f"스타일 생성 완료: {created_name}", 5000)

    @staticmethod
    def _clone_type(style_type: str) -> CreateStyleType:
        return {
            "Character": CreateStyleType.CHARACTER,
            "Table": CreateStyleType.TABLE,
            "List": CreateStyleType.LIST,
        }.get(style_type, CreateStyleType.PARAGRAPH)

    def _duplicate_style(self) -> None:
        selected = self._selected_style_names()
        if len(selected) != 1:
            return
        source_name = selected[0]
        snapshot = self.service.ensure_style_details([source_name])
        source = snapshot.styles[source_name]
        name, accepted = QInputDialog.getText(
            self,
            "스타일 복제",
            f"'{source_name}'을 복제할 새 이름:",
            text=f"{source_name}_복사본",
        )
        if not accepted or not name.strip():
            return
        try:
            updated = self.service.create_style(
                CreateStyleRequest(
                    name=name,
                    style_type=self._clone_type(source.style_type),
                    clone_from=source_name,
                )
            )
        except Exception as exc:
            QMessageBox.critical(self, "스타일 복제 실패", str(exc))
            return
        created_name = name.strip()
        self._populate_styles(updated.styles, [created_name])
        self._show_validation()
        self.statusBar().showMessage(
            f"스타일 복제 완료: {source_name} → {created_name}",
            5000,
        )

    def _delete_selected_styles(self) -> None:
        selected = self._selected_style_names()
        if not selected:
            return
        preview = "\n".join(f"• {name}" for name in selected[:20])
        if len(selected) > 20:
            preview += f"\n… 외 {len(selected) - 20}개"
        answer = QMessageBox.warning(
            self,
            "스타일 삭제 확인",
            "다음 사용자 정의 스타일을 현재 Word 파일에서 삭제합니다.\n\n"
            + preview
            + "\n\n내장 스타일과 참조 중인 스타일은 자동으로 차단됩니다. "
            "계속합니까?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            snapshot = self.service.delete_styles(
                DeleteStyleRequest(style_names=tuple(selected))
            )
        except Exception as exc:
            QMessageBox.critical(self, "스타일 삭제 실패", str(exc))
            return
        self._populate_styles(snapshot.styles)
        self._show_validation()
        self.statusBar().showMessage(
            f"스타일 {len(selected)}개 삭제 완료",
            5000,
        )

    def _reload_selected_style_details(self) -> None:
        selected = self._selected_style_names()
        if not selected:
            return
        current = self.service.current
        if current is not None:
            loaded = set(current.metadata.get("details_loaded", []))
            for name in selected:
                loaded.discard(name)
            current.metadata["details_loaded"] = sorted(loaded)
        try:
            self.service.ensure_style_details(selected)
        except Exception as exc:
            QMessageBox.critical(self, "스타일 상세 조회 실패", str(exc))
            return
        super()._load_selected_styles()
        self.statusBar().showMessage("선택 스타일 상세 조회 완료", 3000)

    def closeEvent(self, event: Any) -> None:
        if getattr(self, "_apply_thread", None) is not None:
            super().closeEvent(event)
            return
        self.service.close()
        super().closeEvent(event)
