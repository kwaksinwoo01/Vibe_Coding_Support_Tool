from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton

from word_editor.services.asset_review_service import (
    approve_registered_asset_update,
    review_registered_asset,
)
from word_editor.services.editor_service import EditorService
from word_editor.services.template_lifecycle_service import TemplateLifecycleService
from word_editor.ui.application_window import ApplicationMainWindow


class CompanyTemplateWindow(ApplicationMainWindow):
    """Complete company Word template manager window."""

    def __init__(
        self,
        service: EditorService,
        lifecycle: TemplateLifecycleService,
    ) -> None:
        super().__init__(service, lifecycle)
        self._insert_asset_review_controls()

    def _insert_asset_review_controls(self) -> None:
        root_layout = self.centralWidget().layout()
        asset_bar = QHBoxLayout()
        asset_bar.addWidget(QLabel("등록 템플릿 자산:"))
        self.asset_summary_label = QLabel("")
        asset_bar.addWidget(self.asset_summary_label, 1)
        self.review_asset_button = QPushButton("등록 자산 변경 검증·저장")
        self.review_asset_button.clicked.connect(
            self.review_and_update_registered_asset
        )
        asset_bar.addWidget(self.review_asset_button)
        root_layout.insertLayout(2, asset_bar)
        self._refresh_asset_summary()

    def _refresh_asset_summary(self) -> None:
        assets = self.lifecycle.assets()
        if not assets:
            self.asset_summary_label.setText(
                "등록된 템플릿 없음 — 머리글 문서블록 템플릿을 먼저 등록하십시오."
            )
            self.review_asset_button.setEnabled(False)
            return
        self.asset_summary_label.setText(
            f"{len(assets)}개 보존됨 · 활성 프로필 배포 패키지에 연결된 자산 "
            f"{len(self.lifecycle.active_profile().asset_ids)}개"
        )
        self.review_asset_button.setEnabled(True)

    def register_template_asset(self) -> None:
        super().register_template_asset()
        self._refresh_asset_summary()

    def review_and_update_registered_asset(self) -> None:
        assets = self.lifecycle.assets()
        if not assets:
            return
        labels = [
            f"{asset.display_name} · {asset.role} · {asset.asset_id}"
            for asset in assets
        ]
        selected, accepted = QInputDialog.getItem(
            self,
            "등록 템플릿 선택",
            "변경을 검증할 템플릿:",
            labels,
            0,
            False,
        )
        if not accepted:
            return
        asset = assets[labels.index(selected)]
        try:
            report = review_registered_asset(
                self.lifecycle,
                asset.asset_id,
            )
        except Exception as exc:
            QMessageBox.critical(self, "템플릿 자산 검증 실패", str(exc))
            return
        if not report.has_changes:
            QMessageBox.information(
                self,
                "템플릿 자산 검증",
                "등록 원본과 프로그램 보존본 사이에 변경이 없습니다.",
            )
            return

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Question)
        message.setWindowTitle("등록 템플릿 변경 검증")
        message.setText(
            f"'{asset.display_name}' 원본 변경을 새 보존 버전으로 저장합니까?"
        )
        message.setInformativeText(
            f"스타일 변경 {len(report.style_changes)}개 · "
            f"Building Block 추가/삭제/변경 "
            f"{len(report.added_building_blocks)}/"
            f"{len(report.removed_building_blocks)}/"
            f"{len(report.changed_building_blocks)}"
        )
        message.setDetailedText("\n".join(report.summary_lines()))
        message.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Cancel
        )
        if message.exec() != QMessageBox.StandardButton.Save:
            return
        note, accepted = QInputDialog.getText(
            self,
            "템플릿 자산 승인 메모",
            "변경 설명:",
        )
        if not accepted:
            return
        try:
            version_directory = approve_registered_asset_update(
                self.lifecycle,
                asset.asset_id,
                report,
                note,
            )
        except Exception as exc:
            QMessageBox.critical(self, "템플릿 자산 저장 실패", str(exc))
            return
        self._refresh_asset_summary()
        QMessageBox.information(
            self,
            "템플릿 자산 버전 저장 완료",
            str(version_directory),
        )

    def _on_external_change(self) -> None:
        super()._on_external_change()
        self.active_profile_label.setText(
            self.active_profile_label.text()
            + " · 외부 변경 감지: 검증 필요"
        )
