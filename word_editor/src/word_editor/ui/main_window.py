from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor
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
from word_editor.domain.property_policy import (
    common_property_names,
    common_property_policy,
)
from word_editor.services.editor_service import EditorService
from word_editor.ui.property_display import (
    format_property_value,
    parse_property_value,
    property_label,
    style_type_label,
)

MIXED_VALUE_TEXT = "⟪혼합값: 변경할 값을 입력⟫"
WORD_FILE_FILTER = "Word files (*.docx *.docm *.dotx *.dotm)"
STYLE_NAME_ROLE = Qt.ItemDataRole.UserRole
ORIGINAL_NAME_ROLE = Qt.ItemDataRole.UserRole + 1


class _EventBridge(QObject):
    target_changed = Signal()


class _ApplyWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: EditorService,
        updates_by_style: dict[str, dict[str, Any]],
    ) -> None:
        super().__init__()
        self._service = service
        self._updates_by_style = updates_by_style

    @Slot()
    def run(self) -> None:
        try:
            snapshot = self._service.apply_style_updates_many(
                self._updates_by_style
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(snapshot)


class MainWindow(QMainWindow):
    def __init__(self, service: EditorService) -> None:
        super().__init__()
        self.service = service
        self._loading_properties = False
        self._loading_style_lists = False
        self._merge_plan: MergePlan | None = None
        self._apply_thread: QThread | None = None
        self._apply_worker: _ApplyWorker | None = None
        self._apply_selection: list[str] = []
        self._apply_property_count = 0
        self._event_bridge = _EventBridge()
        self._event_bridge.target_changed.connect(self._on_external_change)
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(800)
        self._apply_timer.timeout.connect(self.apply_selected_styles)

        self.setWindowTitle("Word Style Editor")
        self.resize(1680, 940)
        self.setStatusBar(QStatusBar(self))
        self._build_ui()
        self._load_initial_state()
        self.service.start_watching(self._event_bridge.target_changed.emit)

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)

        target_bar = QHBoxLayout()
        target_bar.addWidget(QLabel("현재 편집 대상:"))
        self.target_label = QLabel("")
        self.target_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        target_bar.addWidget(self.target_label, 1)
        self.open_target_button = QPushButton("Word 파일 열기")
        self.open_target_button.clicked.connect(self.open_edit_target)
        target_bar.addWidget(self.open_target_button)
        self.normal_target_button = QPushButton("Normal.dotm으로 전환")
        self.normal_target_button.clicked.connect(self.use_normal_target)
        target_bar.addWidget(self.normal_target_button)
        root_layout.addLayout(target_bar)

        toolbar = QHBoxLayout()
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.refresh_snapshot)
        self.apply_button = QPushButton("선택 스타일 적용")
        self.apply_button.clicked.connect(self.apply_selected_styles)
        self.export_button = QPushButton("전체 스냅샷 내보내기")
        self.export_button.clicked.connect(self.export_snapshot)
        self.compare_button = QPushButton("Word 문서와 비교")
        self.compare_button.clicked.connect(self.compare_document)
        self.inject_button = QPushButton("선택 스타일을 문서에 주입")
        self.inject_button.clicked.connect(self.inject_selected_styles)
        self.update_document_button = QPushButton("현재 대상의 전체 스타일 주입")
        self.update_document_button.clicked.connect(self.update_document_styles)
        self.live_sync = QCheckBox("단일 스타일 편집 후 자동 적용")
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
        self.style_list_label = QLabel("모든 스타일")
        left_layout.addWidget(self.style_list_label)

        sort_bar = QHBoxLayout()
        sort_bar.addWidget(QLabel("정렬:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("우선순위순", "priority")
        self.sort_combo.addItem("이름순", "name")
        self.sort_combo.currentIndexChanged.connect(self._resort_styles)
        sort_bar.addWidget(self.sort_combo, 1)
        left_layout.addLayout(sort_bar)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("로컬 이름 또는 원래 이름 필터")
        self.filter_edit.textChanged.connect(self._filter_styles)
        left_layout.addWidget(self.filter_edit)

        self.style_tabs = QTabWidget()
        self.active_style_list = self._create_style_list()
        self.hidden_style_list = self._create_style_list()
        self.style_tabs.addTab(self.active_style_list, "사용 스타일")
        self.style_tabs.addTab(self.hidden_style_list, "숨김 스타일")
        self.style_tabs.currentChanged.connect(self._style_tab_changed)
        left_layout.addWidget(self.style_tabs, 1)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.style_title = QLabel("스타일을 선택하십시오")
        center_layout.addWidget(self.style_title)
        self.style_identity = QLabel("")
        self.style_identity.setWordWrap(True)
        self.style_identity.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        center_layout.addWidget(self.style_identity)
        self.property_table = QTableWidget(0, 5)
        self.property_table.setHorizontalHeaderLabels(
            ["이름", "내부 속성 키", "편집 상태", "현재 값", "편집값"]
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.property_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
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
        self.merge_table = QTableWidget(0, 7)
        self.merge_table.setHorizontalHeaderLabels(
            [
                "스타일",
                "속성 이름",
                "내부 속성 키",
                "기준",
                "현재 대상",
                "비교 문서",
                "선택",
            ]
        )
        self.merge_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        merge_layout.addWidget(self.merge_table, 1)
        self.apply_merge_button = QPushButton("선택한 병합을 현재 대상에 적용")
        self.apply_merge_button.clicked.connect(self.apply_merge)
        merge_layout.addWidget(self.apply_merge_button)
        self.tabs.addTab(merge_tab, "Diff / 병합")
        splitter.addWidget(self.tabs)
        splitter.setSizes([360, 760, 560])

        self.setCentralWidget(root)

    def _create_style_list(self) -> QListWidget:
        widget = QListWidget()
        widget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        widget.itemSelectionChanged.connect(self._style_selection_changed)
        return widget

    def _all_style_lists(self) -> tuple[QListWidget, QListWidget]:
        return self.active_style_list, self.hidden_style_list

    def _current_style_list(self) -> QListWidget:
        current = self.style_tabs.currentWidget()
        if isinstance(current, QListWidget):
            return current
        return self.active_style_list

    def _item_style_name(self, item: QListWidgetItem) -> str:
        return str(item.data(STYLE_NAME_ROLE) or item.text())

    def _load_initial_state(self) -> None:
        try:
            snapshot = self.service.initialize()
        except Exception as exc:
            QMessageBox.critical(self, "초기화 실패", str(exc))
            QTimer.singleShot(0, QApplication.instance().quit)
            return
        self._populate_styles(snapshot.styles)
        self._update_target_ui()
        self._show_validation()
        self.statusBar().showMessage(f"로드 완료: {snapshot.source_path}")

    def _update_target_ui(self) -> None:
        target = self.service.target_path
        self.target_label.setText(str(target))
        self.style_list_label.setText(f"{target.name}의 모든 스타일")
        self.normal_target_button.setEnabled(not self.service.is_normal_target)
        self.setWindowTitle(f"Word Style Editor — {target.name}")

    def open_edit_target(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "편집할 Word 문서 또는 템플릿",
            str(self.service.target_path.parent),
            f"{WORD_FILE_FILTER};;All files (*)",
        )
        if not path:
            return
        self._switch_target(Path(path))

    def use_normal_target(self) -> None:
        self._switch_target(self.service.config.normal_path)

    def _switch_target(self, path: Path) -> None:
        self._apply_timer.stop()
        try:
            snapshot = self.service.select_target(path)
        except Exception as exc:
            QMessageBox.critical(self, "편집 대상 열기 실패", str(exc))
            return
        self._merge_plan = None
        self.merge_table.setRowCount(0)
        self.merge_summary.setText("비교한 문서가 없습니다.")
        self._populate_styles(snapshot.styles)
        self._update_target_ui()
        self._show_validation()
        self.statusBar().showMessage(
            f"편집 대상 전환 완료: {snapshot.source_path}",
            5000,
        )

    def _selected_style_names(self) -> list[str]:
        return [
            self._item_style_name(item)
            for item in self._current_style_list().selectedItems()
        ]

    def _selected_names_by_tab(self) -> tuple[list[str], list[str]]:
        return (
            [self._item_style_name(item) for item in self.active_style_list.selectedItems()],
            [self._item_style_name(item) for item in self.hidden_style_list.selectedItems()],
        )

    def _style_sort_key(self, style: Any) -> tuple[Any, ...]:
        mode = self.sort_combo.currentData()
        name_key = style.local_name.casefold()
        if mode == "name":
            return (name_key,)
        priority = style.properties.get("style.priority")
        try:
            numeric_priority = int(priority)
        except (TypeError, ValueError):
            numeric_priority = 1_000_000
        return (numeric_priority, name_key)

    @staticmethod
    def _is_hidden_style(style: Any) -> bool:
        return style.properties.get("style.hidden") is True

    def _populate_styles(
        self,
        styles: dict[str, Any],
        selected_names: list[str] | None = None,
    ) -> None:
        active_selected, hidden_selected = self._selected_names_by_tab()
        if selected_names is not None:
            selected_set = set(selected_names)
            active_selected = list(selected_set)
            hidden_selected = list(selected_set)

        active_styles = [style for style in styles.values() if not self._is_hidden_style(style)]
        hidden_styles = [style for style in styles.values() if self._is_hidden_style(style)]
        active_styles.sort(key=self._style_sort_key)
        hidden_styles.sort(key=self._style_sort_key)

        self._loading_style_lists = True
        try:
            for widget in self._all_style_lists():
                widget.blockSignals(True)
                widget.clear()

            self._fill_style_list(
                self.active_style_list,
                active_styles,
                set(active_selected),
            )
            self._fill_style_list(
                self.hidden_style_list,
                hidden_styles,
                set(hidden_selected),
            )

            for widget in self._all_style_lists():
                widget.blockSignals(False)
        finally:
            self._loading_style_lists = False

        self.style_tabs.setTabText(0, f"사용 스타일 ({len(active_styles)})")
        self.style_tabs.setTabText(1, f"숨김 스타일 ({len(hidden_styles)})")
        self._filter_styles(self.filter_edit.text())

        if selected_names:
            active_hits = self.active_style_list.selectedItems()
            hidden_hits = self.hidden_style_list.selectedItems()
            if hidden_hits and not active_hits:
                self.style_tabs.setCurrentIndex(1)
            elif active_hits:
                self.style_tabs.setCurrentIndex(0)

        current_list = self._current_style_list()
        if not current_list.selectedItems() and current_list.count():
            current_list.setCurrentRow(0)
        else:
            self._load_selected_styles()

    def _fill_style_list(
        self,
        widget: QListWidget,
        styles: list[Any],
        selected_names: set[str],
    ) -> None:
        for style in styles:
            item = QListWidgetItem(style.local_name)
            item.setData(STYLE_NAME_ROLE, style.local_name)
            item.setData(ORIGINAL_NAME_ROLE, style.original_name)
            priority = style.properties.get("style.priority")
            hidden = style.properties.get("style.hidden") is True
            item.setToolTip(
                f"로컬 이름={style.local_name}\n"
                f"원래 이름={style.original_name or '(확인 불가)'}\n"
                f"우선순위={priority if priority is not None else '(없음)'}\n"
                f"숨김={hidden}\n"
                f"BuiltIn ID={style.built_in_id}\n"
                f"Type={style_type_label(style.style_type)}, "
                f"BuiltIn={style.built_in}, InUse={style.in_use}"
            )
            widget.addItem(item)
            if style.local_name in selected_names:
                item.setSelected(True)

    def _resort_styles(self) -> None:
        snapshot = self.service.current
        if snapshot is None:
            return
        selected = self._selected_style_names()
        self._populate_styles(snapshot.styles, selected)
        mode = "우선순위순" if self.sort_combo.currentData() == "priority" else "이름순"
        self.statusBar().showMessage(f"스타일을 {mode}으로 정렬했습니다.", 3000)

    def _style_tab_changed(self, _index: int) -> None:
        if self._loading_style_lists:
            return
        self._load_selected_styles()

    def _style_selection_changed(self) -> None:
        if self._loading_style_lists:
            return
        sender = self.sender()
        current = self._current_style_list()
        if sender is not current:
            return
        self._load_selected_styles()

    def _filter_styles(self, value: str) -> None:
        needle = value.strip().casefold()
        for widget in self._all_style_lists():
            for index in range(widget.count()):
                item = widget.item(index)
                original_name = str(item.data(ORIGINAL_NAME_ROLE) or "").casefold()
                local_name = self._item_style_name(item).casefold()
                haystack = f"{local_name} {original_name}"
                item.setHidden(bool(needle and needle not in haystack))

    @staticmethod
    def _make_read_only(item: QTableWidgetItem) -> None:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setBackground(QColor(238, 238, 238))

    def _append_row(
        self,
        property_name: str,
        state: str,
        current_text: str,
        edit_text: str,
        editable: bool,
        row_data: dict[str, Any],
        tooltip: str = "",
    ) -> None:
        row = self.property_table.rowCount()
        self.property_table.insertRow(row)
        label_item = QTableWidgetItem(property_label(property_name))
        key_item = QTableWidgetItem(property_name)
        state_item = QTableWidgetItem(state)
        current_item = QTableWidgetItem(current_text)
        edit_item = QTableWidgetItem(edit_text)
        for item in (label_item, key_item, state_item, current_item):
            self._make_read_only(item)
        if not editable:
            self._make_read_only(edit_item)
        if tooltip:
            for item in (label_item, key_item, state_item, current_item, edit_item):
                item.setToolTip(tooltip)
        edit_item.setData(Qt.ItemDataRole.UserRole, row_data)
        self.property_table.setItem(row, 0, label_item)
        self.property_table.setItem(row, 1, key_item)
        self.property_table.setItem(row, 2, state_item)
        self.property_table.setItem(row, 3, current_item)
        self.property_table.setItem(row, 4, edit_item)

    def _load_selected_styles(self) -> None:
        snapshot = self.service.current
        selected_names = self._selected_style_names()
        if snapshot is None or not selected_names:
            self.style_title.setText("스타일을 선택하십시오")
            self.style_identity.setText("")
            self.property_table.setRowCount(0)
            return
        styles = [snapshot.styles[name] for name in selected_names]
        self._loading_properties = True
        try:
            self.property_table.setRowCount(0)
            if len(styles) == 1:
                style = styles[0]
                self.style_title.setText(
                    f"{style.local_name} · {style_type_label(style.style_type)} · "
                    f"내장 스타일={format_property_value('', style.built_in)}"
                )
                self.style_identity.setText(
                    f"로컬 표시 이름: {style.local_name}\n"
                    f"Word 원래 이름: {style.original_name or '(확인 불가)'}\n"
                    f"내장 스타일 ID: "
                    f"{style.built_in_id if style.built_in_id is not None else '(없음)'}"
                )
                metadata = (
                    ("meta.local_name", style.local_name),
                    ("meta.original_name", style.original_name),
                    ("meta.built_in_id", style.built_in_id),
                    ("meta.style_type", style.style_type),
                    ("meta.built_in", style.built_in),
                    ("meta.in_use", style.in_use),
                )
                for name, value in metadata:
                    text = format_property_value(name, value)
                    self._append_row(
                        name,
                        "읽기 전용 메타데이터",
                        text,
                        text,
                        False,
                        {"metadata": True},
                    )
            else:
                self.style_title.setText(f"스타일 {len(styles)}개 선택")
                self.style_identity.setText(
                    "선택한 모든 스타일에 공통으로 존재하는 속성만 표시합니다. "
                    "혼합값은 새 값을 입력한 경우에만 일괄 변경됩니다."
                )

            for property_name in common_property_names(styles):
                values = [style.properties.get(property_name) for style in styles]
                first = values[0]
                same = all(value == first for value in values[1:])
                policy = common_property_policy(styles, property_name)
                current_text = (
                    format_property_value(property_name, first)
                    if same
                    else f"혼합값 ({len({self._stable_value(v) for v in values})}종)"
                )
                edit_text = current_text if same else MIXED_VALUE_TEXT
                state = "편집 가능" if policy.editable else "읽기 전용"
                self._append_row(
                    property_name,
                    state,
                    current_text,
                    edit_text,
                    policy.editable,
                    {
                        "metadata": False,
                        "representative": first,
                        "initial_text": edit_text,
                        "mixed": not same,
                    },
                    tooltip=policy.reason,
                )
        finally:
            self._loading_properties = False
        self.apply_button.setText(
            "선택 스타일 일괄 적용"
            if len(styles) > 1
            else "선택 스타일 적용"
        )

    @staticmethod
    def _stable_value(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _format_value(value: Any, property_name: str = "") -> str:
        return format_property_value(property_name, value)

    def _property_edited(self, item: QTableWidgetItem) -> None:
        if self._loading_properties or item.column() != 4:
            return
        selected_count = len(self._selected_style_names())
        if self.live_sync.isChecked() and selected_count == 1:
            self._apply_timer.start()
        elif selected_count > 1:
            self.statusBar().showMessage(
                "다중 선택 편집은 안전을 위해 '선택 스타일 일괄 적용'을 누르십시오.",
                5000,
            )

    def _collect_common_updates(self) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        for row in range(self.property_table.rowCount()):
            property_name = self.property_table.item(row, 1).text()
            edit_item = self.property_table.item(row, 4)
            row_data = edit_item.data(Qt.ItemDataRole.UserRole) or {}
            if row_data.get("metadata"):
                continue
            if not (edit_item.flags() & Qt.ItemFlag.ItemIsEditable):
                continue
            text = edit_item.text()
            initial_text = row_data.get("initial_text", "")
            if text == initial_text:
                continue
            if row_data.get("mixed") and text.strip() in {
                "",
                MIXED_VALUE_TEXT,
            }:
                continue
            original = row_data.get("representative")
            updates[property_name] = parse_property_value(
                property_name,
                text,
                original,
            )
        return updates

    def apply_selected_styles(self) -> None:
        self._apply_timer.stop()
        if self._apply_thread is not None:
            return
        selected_names = self._selected_style_names()
        if not selected_names:
            return
        updates = self._collect_common_updates()
        if not updates:
            return
        updates_by_style = {
            style_name: dict(updates) for style_name in selected_names
        }
        self._apply_selection = selected_names
        self._apply_property_count = len(updates)
        self.service.stop_watching()
        self.centralWidget().setEnabled(False)
        self.statusBar().showMessage(
            "Word에서 스타일을 적용하고 검증하는 중입니다. 창은 계속 응답합니다."
        )

        thread = QThread(self)
        worker = _ApplyWorker(self.service, updates_by_style)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._apply_succeeded)
        worker.failed.connect(self._apply_failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._apply_finished)
        self._apply_thread = thread
        self._apply_worker = worker
        thread.start()

    @Slot(object)
    def _apply_succeeded(self, snapshot: Any) -> None:
        selected_names = self._apply_selection
        self._populate_styles(snapshot.styles, selected_names)
        self._show_validation()
        self.statusBar().showMessage(
            f"스타일 {len(selected_names)}개에 공통 속성 "
            f"{self._apply_property_count}개 적용 완료",
            5000,
        )

    @Slot(str)
    def _apply_failed(self, message: str) -> None:
        QMessageBox.critical(self, "적용 실패", message)
        self.statusBar().showMessage(
            "적용하지 못했습니다. 입력값을 확인한 뒤 다시 시도하거나 새로고침하세요.",
            8000,
        )

    @Slot()
    def _apply_finished(self) -> None:
        self._apply_thread = None
        self._apply_worker = None
        self._apply_selection = []
        self._apply_property_count = 0
        self.centralWidget().setEnabled(True)
        self.service.start_watching(self._event_bridge.target_changed.emit)

    def refresh_snapshot(self) -> None:
        selected_names = self._selected_style_names()
        try:
            snapshot = self.service.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "새로고침 실패", str(exc))
            return
        self._populate_styles(snapshot.styles, selected_names)
        self._update_target_ui()
        self._show_validation()
        self.statusBar().showMessage(
            f"{self.service.target_display_name} 새로고침 완료",
            4000,
        )

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
                self._make_read_only(cell)
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
            "현재 대상과 비교할 Word 문서 또는 템플릿",
            str(Path.home()),
            f"{WORD_FILE_FILTER};;All files (*)",
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
            f"비교 문서 전용 스타일 {len(plan.added_styles)}개"
        )
        self.merge_table.setRowCount(len(plan.conflicts))
        for row, conflict in enumerate(plan.conflicts):
            values = [
                conflict.style_name,
                property_label(conflict.property_name),
                conflict.property_name,
                self._format_value(
                    conflict.baseline_value,
                    conflict.property_name,
                ),
                self._format_value(
                    conflict.normal_value,
                    conflict.property_name,
                ),
                self._format_value(
                    conflict.document_value,
                    conflict.property_name,
                ),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                self._make_read_only(item)
                self.merge_table.setItem(row, column, item)
            chooser = QComboBox()
            chooser.addItem("현재 대상 유지", ConflictChoice.KEEP_NORMAL)
            chooser.addItem("비교 문서 값 사용", ConflictChoice.USE_DOCUMENT)
            chooser.addItem("기준값 사용", ConflictChoice.USE_BASELINE)
            self.merge_table.setCellWidget(row, 6, chooser)

    def apply_merge(self) -> None:
        plan = self._merge_plan
        if plan is None:
            return
        for row, conflict in enumerate(plan.conflicts):
            chooser = self.merge_table.cellWidget(row, 6)
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

    def inject_selected_styles(self) -> None:
        selected_names = self._selected_style_names()
        if not selected_names:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "스타일을 주입할 Word 문서",
            str(Path.home()),
            WORD_FILE_FILTER,
        )
        if not path:
            return
        try:
            self.service.inject_selected_styles(
                Path(path),
                selected_names,
            )
        except Exception as exc:
            QMessageBox.critical(self, "스타일 주입 실패", str(exc))
            return
        QMessageBox.information(
            self,
            "주입 완료",
            f"스타일 {len(selected_names)}개 → {path}",
        )

    def update_document_styles(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "현재 대상의 전체 스타일을 주입할 Word 파일",
            str(Path.home()),
            WORD_FILE_FILTER,
        )
        if not path:
            return
        answer = QMessageBox.question(
            self,
            "전체 스타일 주입",
            f"{self.service.target_display_name}의 같은 이름 스타일로 "
            "대상 파일을 덮어씁니다. 계속합니까?",
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
        if self._apply_timer.isActive() or self._apply_thread is not None:
            return
        self.refresh_snapshot()
        self.statusBar().showMessage(
            f"외부 프로그램의 {self.service.target_display_name} 변경을 감지했습니다.",
            6000,
        )

    def closeEvent(self, event: Any) -> None:
        if self._apply_thread is not None:
            event.ignore()
            self.statusBar().showMessage(
                "스타일 적용이 끝난 뒤 프로그램을 닫을 수 있습니다.",
                5000,
            )
            return
        self.service.stop_watching()
        super().closeEvent(event)
