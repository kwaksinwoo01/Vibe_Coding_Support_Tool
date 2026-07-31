from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from word_editor.domain.models import ConflictChoice, MergePlan, Severity
from word_editor.services.editor_service import EditorService


class _EventBridge(QObject):
    normal_changed = Signal()


class MainWindow(QMainWindow):
    def __init__(self, service: EditorService) -> None:
        super().__init__()
        self.service = service
        self._loading_properties = False
        self._merge_plan: MergePlan | None = None
        self._event_bridge = _EventBridge()
        self._event_bridge.normal_changed.connect(self._on_external_change)
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(800)
        self._apply_timer.timeout.connect(self.apply_current_style)

        self.setWindowTitle("Word Normal.dotm Style Editor")
        self.resize(1500, 900)
        self.setStatusBar(QStatusBar(self))
        self._build_ui()
        self._load_initial_state()
        self.service.start_watching(self._event_bridge.normal_changed.emit)

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)

        toolbar = QHBoxLayout()
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.refresh_snapshot)
        self.apply_button = QPushButton("현재 스타일 적용")
        self.apply_button.clicked.connect(self.apply_current_style)
        self.export_button = QPushButton("전체 스냅샷 내보내기")
        self.export_button.clicked.connect(self.export_snapshot)
        self.compare_button = QPushButton("Word 문서와 비교")
        self.compare_button.clicked.connect(self.compare_document)
        self.inject_button = QPushButton("선택 스타일을 문서에 주입")
        self.inject_button.clicked.connect(self.inject_selected_style)
        self.update_document_button = QPushButton("문서 스타일 전체 업데이트")
        self.update_document_button.clicked.connect(self.update_document_styles)
        self.live_sync = QCheckBox("편집 후 자동 적용")
        self.live_sync.setChecked(True)
        for widget in (
            self.refresh_button,
            self.apply_button,
            self.export_button,
            self.compare_button,
            self.inject_button,
            self.update_document_button,
            self.live_sync,
        ):
            toolbar.addWidget(widget)
        toolbar.addStretch(1)
        root_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Normal.dotm의 모든 스타일"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("스타일 이름 필터")
        self.filter_edit.textChanged.connect(self._filter_styles)
        left_layout.addWidget(self.filter_edit)
        self.style_list = QListWidget()
        self.style_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.style_list.currentTextChanged.connect(self._load_selected_style)
        left_layout.addWidget(self.style_list, 1)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.style_title = QLabel("스타일을 선택하십시오")
        center_layout.addWidget(self.style_title)
        self.property_table = QTableWidget(0, 3)
        self.property_table.setHorizontalHeaderLabels(
            ["속성", "현재 Normal.dotm", "편집값"]
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.property_table.itemChanged.connect(self._property_edited)
        center_layout.addWidget(self.property_table, 1)
        splitter.addWidget(center)

        self.tabs = QTabWidget()
        self.validation_table = QTableWidget(0, 4)
        self.validation_table.setHorizontalHeaderLabels(
            ["심각도", "검증기", "스타일/속성", "내용"]
        )
        self.validation_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.tabs.addTab(self.validation_table, "검증")

        merge_tab = QWidget()
        merge_layout = QVBoxLayout(merge_tab)
        self.merge_summary = QLabel("비교한 문서가 없습니다.")
        merge_layout.addWidget(self.merge_summary)
        self.merge_table = QTableWidget(0, 6)
        self.merge_table.setHorizontalHeaderLabels(
            ["스타일", "속성", "기준", "Normal.dotm", "문서", "선택"]
        )
        self.merge_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        merge_layout.addWidget(self.merge_table, 1)
        self.apply_merge_button = QPushButton("선택한 병합을 Normal.dotm에 적용")
        self.apply_merge_button.clicked.connect(self.apply_merge)
        merge_layout.addWidget(self.apply_merge_button)
        self.tabs.addTab(merge_tab, "Diff / 병합")
        splitter.addWidget(self.tabs)
        splitter.setSizes([280, 650, 570])

        self.setCentralWidget(root)

    def _load_initial_state(self) -> None:
        try:
            snapshot = self.service.initialize()
        except Exception as exc:
            QMessageBox.critical(self, "초기화 실패", str(exc))
            QTimer.singleShot(0, QApplication.instance().quit)
            return
        self._populate_styles(snapshot.styles)
        self._show_validation()
        self.statusBar().showMessage(f"로드 완료: {snapshot.source_path}")

    def _populate_styles(self, styles: dict[str, Any]) -> None:
        selected = self.style_list.currentItem()
        selected_name = selected.text() if selected else ""
        self.style_list.blockSignals(True)
        self.style_list.clear()
        for name in sorted(styles, key=str.casefold):
            item = QListWidgetItem(name)
            style = styles[name]
            item.setToolTip(
                f"Type={style.style_type}, BuiltIn={style.built_in}, "
                f"InUse={style.in_use}"
            )
            self.style_list.addItem(item)
        self.style_list.blockSignals(False)
        self._filter_styles(self.filter_edit.text())
        matches = self.style_list.findItems(
            selected_name,
            Qt.MatchFlag.MatchExactly,
        )
        if matches:
            self.style_list.setCurrentItem(matches[0])
        elif self.style_list.count():
            self.style_list.setCurrentRow(0)

    def _filter_styles(self, value: str) -> None:
        needle = value.strip().casefold()
        for index in range(self.style_list.count()):
            item = self.style_list.item(index)
            item.setHidden(bool(needle and needle not in item.text().casefold()))

    def _load_selected_style(self, style_name: str) -> None:
        snapshot = self.service.current
        if snapshot is None or not style_name:
            return
        style = snapshot.styles.get(style_name)
        if style is None:
            return
        self.style_title.setText(
            f"{style.name}  ·  {style.style_type}  ·  "
            f"BuiltIn={style.built_in}"
        )
        self._loading_properties = True
        try:
            self.property_table.setRowCount(0)
            for property_name, value in sorted(style.properties.items()):
                row = self.property_table.rowCount()
                self.property_table.insertRow(row)
                name_item = QTableWidgetItem(property_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                current_item = QTableWidgetItem(self._format_value(value))
                current_item.setFlags(
                    current_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                )
                edit_item = QTableWidgetItem(self._format_value(value))
                edit_item.setData(Qt.ItemDataRole.UserRole, value)
                self.property_table.setItem(row, 0, name_item)
                self.property_table.setItem(row, 1, current_item)
                self.property_table.setItem(row, 2, edit_item)
        finally:
            self._loading_properties = False

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _parse_value(text: str, original: Any) -> Any:
        stripped = text.strip()
        if isinstance(original, str):
            return text
        if stripped == "":
            return None
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            if isinstance(original, bool):
                lowered = stripped.casefold()
                if lowered in {"true", "yes", "1", "예"}:
                    return True
                if lowered in {"false", "no", "0", "아니오"}:
                    return False
            return text

    def _property_edited(self, item: QTableWidgetItem) -> None:
        if self._loading_properties or item.column() != 2:
            return
        if self.live_sync.isChecked():
            self._apply_timer.start()

    def _collect_updates(self) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        for row in range(self.property_table.rowCount()):
            property_name = self.property_table.item(row, 0).text()
            edit_item = self.property_table.item(row, 2)
            original = edit_item.data(Qt.ItemDataRole.UserRole)
            parsed = self._parse_value(edit_item.text(), original)
            if parsed != original:
                updates[property_name] = parsed
        return updates

    def apply_current_style(self) -> None:
        item = self.style_list.currentItem()
        if item is None:
            return
        updates = self._collect_updates()
        if not updates:
            return
        try:
            snapshot = self.service.apply_style_updates(item.text(), updates)
        except Exception as exc:
            QMessageBox.critical(self, "적용 실패", str(exc))
            self.refresh_snapshot()
            return
        self._populate_styles(snapshot.styles)
        self._show_validation()
        self.statusBar().showMessage(
            f"{item.text()} 속성 {len(updates)}개 적용 완료",
            5000,
        )

    def refresh_snapshot(self) -> None:
        try:
            snapshot = self.service.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "새로고침 실패", str(exc))
            return
        self._populate_styles(snapshot.styles)
        self._show_validation()
        self.statusBar().showMessage("Normal.dotm 새로고침 완료", 4000)

    def _show_validation(self) -> None:
        issues = self.service.validate_current()
        self.validation_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            target = ".".join(
                value
                for value in (issue.style_name, issue.property_name)
                if value
            )
            values = [
                issue.severity.value,
                issue.validator,
                target,
                issue.message,
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.validation_table.setItem(row, column, cell)
        errors = sum(issue.severity is Severity.ERROR for issue in issues)
        self.tabs.setTabText(0, f"검증 ({errors} 오류 / {len(issues)} 전체)")

    def export_snapshot(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "스냅샷 저장 폴더",
            str(Path.home() / "Desktop"),
        )
        if not directory:
            return
        try:
            path = self.service.export_snapshot(Path(directory))
        except Exception as exc:
            QMessageBox.critical(self, "내보내기 실패", str(exc))
            return
        QMessageBox.information(self, "내보내기 완료", str(path))

    def compare_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "비교할 Word 문서 또는 템플릿",
            str(Path.home()),
            "Word files (*.docx *.docm *.dotx *.dotm);;All files (*)",
        )
        if not path:
            return
        try:
            self._merge_plan = self.service.compare_document(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "비교 실패", str(exc))
            return
        self._populate_merge(self._merge_plan)
        self.tabs.setCurrentIndex(1)

    def _populate_merge(self, plan: MergePlan) -> None:
        self.merge_summary.setText(
            f"자동 병합 스타일 {len(plan.automatic_values)}개 · "
            f"충돌 {len(plan.conflicts)}개 · "
            f"문서 전용 스타일 {len(plan.added_styles)}개"
        )
        self.merge_table.setRowCount(len(plan.conflicts))
        for row, conflict in enumerate(plan.conflicts):
            values = [
                conflict.style_name,
                conflict.property_name,
                self._format_value(conflict.baseline_value),
                self._format_value(conflict.normal_value),
                self._format_value(conflict.document_value),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.merge_table.setItem(row, column, item)
            chooser = QComboBox()
            chooser.addItem("Normal.dotm 유지", ConflictChoice.KEEP_NORMAL)
            chooser.addItem("문서 값 사용", ConflictChoice.USE_DOCUMENT)
            chooser.addItem("기준값 사용", ConflictChoice.USE_BASELINE)
            self.merge_table.setCellWidget(row, 5, chooser)

    def apply_merge(self) -> None:
        plan = self._merge_plan
        if plan is None:
            return
        for row, conflict in enumerate(plan.conflicts):
            chooser = self.merge_table.cellWidget(row, 5)
            if isinstance(chooser, QComboBox):
                conflict.choice = chooser.currentData()
        try:
            snapshot = self.service.apply_merge_plan(plan)
        except Exception as exc:
            QMessageBox.critical(self, "병합 적용 실패", str(exc))
            return
        self._populate_styles(snapshot.styles)
        self._show_validation()
        self.statusBar().showMessage("속성 병합 완료", 5000)

    def inject_selected_style(self) -> None:
        selected = self.style_list.currentItem()
        if selected is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "스타일을 주입할 Word 문서",
            str(Path.home()),
            "Word files (*.docx *.docm *.dotx *.dotm)",
        )
        if not path:
            return
        try:
            self.service.inject_selected_styles(
                Path(path), [selected.text()]
            )
        except Exception as exc:
            QMessageBox.critical(self, "스타일 주입 실패", str(exc))
            return
        QMessageBox.information(
            self,
            "주입 완료",
            f"{selected.text()} → {path}",
        )

    def update_document_styles(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Normal.dotm 스타일로 업데이트할 Word 문서",
            str(Path.home()),
            "Word documents (*.docx *.docm)",
        )
        if not path:
            return
        answer = QMessageBox.question(
            self,
            "전체 스타일 업데이트",
            "같은 이름의 문서 스타일을 Normal.dotm 정의로 덮어씁니다. 계속합니까?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.update_all_document_styles(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "문서 업데이트 실패", str(exc))
            return
        QMessageBox.information(self, "완료", "문서 스타일을 업데이트했습니다.")

    def _on_external_change(self) -> None:
        if self._apply_timer.isActive():
            return
        self.refresh_snapshot()
        self.statusBar().showMessage(
            "Word 또는 외부 프로그램의 Normal.dotm 변경을 감지했습니다.",
            6000,
        )

    def closeEvent(self, event: Any) -> None:
        self.service.stop_watching()
        super().closeEvent(event)
