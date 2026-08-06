from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
)

from word_editor.services.editor_service import EditorService
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
    UnapprovedTemplateChanges,
)
from word_editor.ui.main_window import MainWindow
from word_editor.ui.style_visibility import belongs_to_hidden_tab


class ApplicationMainWindow(MainWindow):
    """Word style editor with company template profile lifecycle controls."""

    def __init__(
        self,
        service: EditorService,
        lifecycle: TemplateLifecycleService,
    ) -> None:
        self.lifecycle = lifecycle
        self.lifecycle.initialize()
        super().__init__(service)
        self._insert_profile_controls()
        self._reload_profile_combo()

    @staticmethod
    def _is_hidden_style(style: Any) -> bool:
        return belongs_to_hidden_tab(style)

    def _insert_profile_controls(self) -> None:
        root_layout = self.centralWidget().layout()
        profile_bar = QHBoxLayout()
        profile_bar.addWidget(QLabel("회사 서식 프로필:"))

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(280)
        profile_bar.addWidget(self.profile_combo, 1)

        self.active_profile_label = QLabel("")
        profile_bar.addWidget(self.active_profile_label)

        self.register_profile_button = QPushButton("프로필 등록")
        self.register_profile_button.clicked.connect(self.register_profile)
        profile_bar.addWidget(self.register_profile_button)

        self.activate_profile_button = QPushButton("선택 프로필 활성화")
        self.activate_profile_button.clicked.connect(
            self.activate_selected_profile
        )
        profile_bar.addWidget(self.activate_profile_button)

        self.approve_changes_button = QPushButton("현재 변경 검증·저장")
        self.approve_changes_button.clicked.connect(
            self.review_and_save_current_changes
        )
        profile_bar.addWidget(self.approve_changes_button)

        self.register_asset_button = QPushButton("템플릿 자산 등록")
        self.register_asset_button.clicked.connect(self.register_template_asset)
        profile_bar.addWidget(self.register_asset_button)

        self.package_button = QPushButton("배포 패키지 생성")
        self.package_button.clicked.connect(self.create_distribution_package)
        profile_bar.addWidget(self.package_button)

        root_layout.insertLayout(1, profile_bar)

    def _reload_profile_combo(self, selected_profile_id: str | None = None) -> None:
        current_id = selected_profile_id or self._selected_profile_id()
        active_id = self.lifecycle.registry.active_profile_id
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected_index = 0
        for index, profile in enumerate(self.lifecycle.profiles()):
            marker = " [활성]" if profile.profile_id == active_id else ""
            label = (
                f"{profile.classification_code or '-'} · "
                f"{profile.display_name}{marker}"
            )
            self.profile_combo.addItem(label, profile.profile_id)
            if profile.profile_id == current_id:
                selected_index = index
        if self.profile_combo.count():
            self.profile_combo.setCurrentIndex(selected_index)
        self.profile_combo.blockSignals(False)
        try:
            active = self.lifecycle.active_profile()
            self.active_profile_label.setText(
                f"실제 Normal.dotm: {active.classification_code} / "
                f"{active.display_name}"
            )
        except TemplateLifecycleError:
            self.active_profile_label.setText("활성 프로필 없음")

    def _selected_profile_id(self) -> str:
        if not hasattr(self, "profile_combo"):
            return ""
        return str(self.profile_combo.currentData() or "")

    @staticmethod
    def _report_text(report: Any) -> str:
        return "\n".join(report.summary_lines())

    def register_profile(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "회사 Normal.dotm 프로필 원본 선택",
            str(Path.home()),
            "Word macro-enabled template (*.dotm)",
        )
        if not source:
            return
        default_name = "FDM 종이문서" if "fdm" in Path(source).stem.casefold() else Path(source).stem
        display_name, accepted = QInputDialog.getText(
            self,
            "프로필 이름",
            "표시 이름:",
            text=default_name,
        )
        if not accepted or not display_name.strip():
            return
        default_code = "FDM" if "fdm" in display_name.casefold() else "DCM"
        classification_code, accepted = QInputDialog.getText(
            self,
            "문서 분류코드",
            "분류코드(FDM, DCM 등):",
            text=default_code,
        )
        if not accepted:
            return
        try:
            profile = self.lifecycle.register_profile(
                Path(source),
                display_name,
                classification_code,
            )
        except Exception as exc:
            QMessageBox.critical(self, "프로필 등록 실패", str(exc))
            return
        self._reload_profile_combo(profile.profile_id)
        QMessageBox.information(
            self,
            "프로필 등록 완료",
            f"{profile.display_name}\n{profile.canonical_path}",
        )

    def _finish_profile_activation(self, profile_id: str) -> None:
        self.service.stop_watching()
        try:
            self.lifecycle.activate_profile(profile_id)
            snapshot = self.service.select_normal_target()
            self.service.accept_as_baseline(snapshot)
        finally:
            self.service.start_watching(self._event_bridge.target_changed.emit)
        self._populate_styles(snapshot.styles)
        self._update_target_ui()
        self._show_validation()
        self._reload_profile_combo(profile_id)
        self.statusBar().showMessage(
            "회사 Normal.dotm 프로필 활성화 완료",
            6000,
        )

    def activate_selected_profile(self) -> None:
        profile_id = self._selected_profile_id()
        if not profile_id:
            return
        if profile_id == self.lifecycle.registry.active_profile_id:
            QMessageBox.information(
                self,
                "프로필 활성화",
                "이미 활성화된 프로필입니다.",
            )
            return
        try:
            self._finish_profile_activation(profile_id)
        except UnapprovedTemplateChanges as exc:
            message = QMessageBox(self)
            message.setIcon(QMessageBox.Icon.Warning)
            message.setWindowTitle("승인되지 않은 Normal.dotm 변경")
            message.setText(
                "현재 활성 프로필에 저장되지 않은 변경이 있습니다."
            )
            message.setInformativeText(
                "저장 후 전환하거나 변경을 폐기해야 합니다."
            )
            message.setDetailedText(self._report_text(exc.report))
            message.setStandardButtons(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            message.setDefaultButton(QMessageBox.StandardButton.Cancel)
            result = message.exec()
            if result == QMessageBox.StandardButton.Yes:
                note, accepted = QInputDialog.getText(
                    self,
                    "변경 승인 메모",
                    "현재 프로필에 저장할 변경 설명:",
                )
                if not accepted:
                    return
                try:
                    self.lifecycle.approve_current_changes(note)
                    self.service.refresh()
                    self.service.accept_as_baseline()
                    self._finish_profile_activation(profile_id)
                except Exception as save_exc:
                    QMessageBox.critical(
                        self,
                        "저장 후 전환 실패",
                        str(save_exc),
                    )
            elif result == QMessageBox.StandardButton.Discard:
                try:
                    self.service.stop_watching()
                    self.lifecycle.activate_profile(
                        profile_id,
                        discard_unapproved_changes=True,
                    )
                    snapshot = self.service.select_normal_target()
                    self.service.accept_as_baseline(snapshot)
                    self.service.start_watching(
                        self._event_bridge.target_changed.emit
                    )
                    self._populate_styles(snapshot.styles)
                    self._update_target_ui()
                    self._show_validation()
                    self._reload_profile_combo(profile_id)
                except Exception as discard_exc:
                    self.service.start_watching(
                        self._event_bridge.target_changed.emit
                    )
                    QMessageBox.critical(
                        self,
                        "변경 폐기 후 전환 실패",
                        str(discard_exc),
                    )
        except Exception as exc:
            QMessageBox.critical(self, "프로필 활성화 실패", str(exc))

    def review_and_save_current_changes(self) -> None:
        try:
            report = self.lifecycle.review_current_changes()
        except Exception as exc:
            QMessageBox.critical(self, "변경 검증 실패", str(exc))
            return
        if not report.has_changes:
            QMessageBox.information(
                self,
                "변경 검증",
                "활성 프로필과 현재 Normal.dotm 사이에 변경이 없습니다.",
            )
            return
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Question)
        message.setWindowTitle("Normal.dotm 변경 검증")
        message.setText(
            "현재 Normal.dotm 변경을 활성 회사 프로필의 새 버전으로 저장합니까?"
        )
        message.setInformativeText(
            f"스타일 변경 {len(report.style_changes)}개, "
            f"Building Block 추가/삭제/변경 "
            f"{len(report.added_building_blocks)}/"
            f"{len(report.removed_building_blocks)}/"
            f"{len(report.changed_building_blocks)}"
        )
        message.setDetailedText(self._report_text(report))
        message.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Cancel
        )
        if message.exec() != QMessageBox.StandardButton.Save:
            return
        note, accepted = QInputDialog.getText(
            self,
            "변경 승인 메모",
            "버전 변경 설명:",
        )
        if not accepted:
            return
        try:
            _, version_directory = self.lifecycle.approve_current_changes(note)
            snapshot = self.service.refresh()
            self.service.accept_as_baseline(snapshot)
        except Exception as exc:
            QMessageBox.critical(self, "프로필 저장 실패", str(exc))
            return
        self._reload_profile_combo()
        QMessageBox.information(
            self,
            "프로필 버전 저장 완료",
            str(version_directory),
        )

    def register_template_asset(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "보존할 회사 Word 템플릿 선택",
            str(Path.home()),
            "Word templates (*.dotm *.dotx)",
        )
        if not source:
            return
        display_name, accepted = QInputDialog.getText(
            self,
            "템플릿 자산 이름",
            "표시 이름:",
            text=Path(source).stem,
        )
        if not accepted or not display_name.strip():
            return
        roles = [
            "header-building-block-template",
            "company-template",
            "document-building-block-template",
        ]
        role, accepted = QInputDialog.getItem(
            self,
            "템플릿 자산 역할",
            "역할:",
            roles,
            0,
            False,
        )
        if not accepted:
            return
        try:
            asset = self.lifecycle.register_asset(
                Path(source),
                display_name,
                role,
            )
        except Exception as exc:
            QMessageBox.critical(self, "템플릿 자산 등록 실패", str(exc))
            return
        QMessageBox.information(
            self,
            "템플릿 자산 등록 완료",
            f"{asset.display_name}\n{asset.managed_path}\n"
            "현재 활성 프로필의 배포 패키지에 포함됩니다.",
        )

    def create_distribution_package(self) -> None:
        profile_id = self._selected_profile_id()
        if not profile_id:
            return
        directory = QFileDialog.getExistingDirectory(
            self,
            "배포 패키지 저장 폴더",
            str(Path.home() / "Desktop"),
        )
        if not directory:
            return
        default_version = datetime.now().strftime("%Y.%m.%d")
        version_label, accepted = QInputDialog.getText(
            self,
            "배포 버전",
            "버전명:",
            text=default_version,
        )
        if not accepted or not version_label.strip():
            return
        note, accepted = QInputDialog.getText(
            self,
            "배포 메모",
            "배포 설명(선택):",
        )
        if not accepted:
            return
        try:
            package = self.lifecycle.create_distribution_package(
                profile_id,
                Path(directory),
                version_label,
                note,
            )
        except Exception as exc:
            QMessageBox.critical(self, "배포 패키지 생성 실패", str(exc))
            return
        QMessageBox.information(
            self,
            "배포 패키지 생성 완료",
            str(package),
        )
