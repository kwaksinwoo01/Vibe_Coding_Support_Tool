from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
)

from word_editor.infrastructure.header_footer_sdk import (
    HeaderFooterApplyOptions,
    HeaderFooterSdk,
)
from word_editor.services.editor_service import EditorService
from word_editor.services.template_lifecycle_service import TemplateLifecycleService
from word_editor.ui.style_management_window import StyleManagementWindow

WORD_FILE_FILTER = "Word files (*.docx *.docm *.dotx *.dotm)"
TEMPLATE_FILTER = "Word templates (*.dotm *.dotx)"


class HeaderFooterManagementWindow(StyleManagementWindow):
    """Full Word SDK window including header/footer layout assets."""

    def __init__(
        self,
        service: EditorService,
        lifecycle: TemplateLifecycleService,
    ) -> None:
        self.header_footer_sdk = HeaderFooterSdk(service.gateway)
        super().__init__(service, lifecycle)
        self._insert_header_footer_controls()

    def _insert_header_footer_controls(self) -> None:
        root_layout = self.centralWidget().layout()
        row = QHBoxLayout()
        row.addWidget(QLabel("머리글·바닥글 자산:"))
        self.header_footer_summary = QLabel("")
        row.addWidget(self.header_footer_summary, 1)
        register_button = QPushButton("머리글·바닥글 템플릿 등록")
        register_button.clicked.connect(self.register_header_footer_asset)
        row.addWidget(register_button)
        apply_button = QPushButton("문서에 머리글·바닥글 적용")
        apply_button.clicked.connect(self.apply_header_footer_asset)
        row.addWidget(apply_button)
        root_layout.insertLayout(3, row)
        self._refresh_header_footer_summary()

    def _header_footer_assets(self):
        return [
            asset
            for asset in self.lifecycle.assets()
            if asset.role == "header-footer-template"
        ]

    def _refresh_header_footer_summary(self) -> None:
        assets = self._header_footer_assets()
        self.header_footer_summary.setText(
            f"등록된 레이아웃 템플릿 {len(assets)}개 · "
            "Word 기본 머리글/바닥글은 검증 대상이 아님"
        )

    def register_header_footer_asset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "머리글·바닥글 원본 템플릿",
            str(Path.home()),
            TEMPLATE_FILTER,
        )
        if not path:
            return
        display_name, accepted = QInputDialog.getText(
            self,
            "머리글·바닥글 자산 이름",
            "표시 이름:",
            text=Path(path).stem,
        )
        if not accepted or not display_name.strip():
            return
        description, accepted = QInputDialog.getText(
            self,
            "자산 설명",
            "용도 또는 적용 문서 설명(선택):",
        )
        if not accepted:
            return
        try:
            asset = self.lifecycle.register_asset(
                Path(path),
                display_name,
                role="header-footer-template",
                description=description,
                attach_to_active_profile=True,
            )
        except Exception as exc:
            QMessageBox.critical(self, "자산 등록 실패", str(exc))
            return
        self._refresh_asset_summary()
        self._refresh_header_footer_summary()
        inventory = self.lifecycle.inventory_reader.capture(
            Path(asset.managed_path)
        )
        QMessageBox.information(
            self,
            "머리글·바닥글 자산 등록 완료",
            f"{asset.display_name}\n"
            f"인식된 머리글·바닥글 항목: "
            f"{len(inventory.header_footer_entries)}개\n"
            "원본 템플릿 파일 전체가 보존되었습니다.",
        )

    def apply_header_footer_asset(self) -> None:
        assets = self._header_footer_assets()
        if not assets:
            QMessageBox.information(
                self,
                "등록 자산 없음",
                "먼저 머리글·바닥글 템플릿을 등록하십시오.",
            )
            return
        labels = [
            f"{asset.display_name} · {Path(asset.managed_path).name}"
            for asset in assets
        ]
        selected, accepted = QInputDialog.getItem(
            self,
            "머리글·바닥글 자산 선택",
            "적용할 회사 템플릿:",
            labels,
            0,
            False,
        )
        if not accepted:
            return
        asset = assets[labels.index(selected)]
        target, _ = QFileDialog.getOpenFileName(
            self,
            "머리글·바닥글을 적용할 Word 문서",
            str(Path.home()),
            WORD_FILE_FILTER,
        )
        if not target:
            return
        mode_label, accepted = QInputDialog.getItem(
            self,
            "구역 대응 방식",
            "원본 구역을 대상 구역에 적용하는 방법:",
            [
                "같은 구역 번호 대응(대상 구역이 더 많으면 마지막 원본 구역 반복)",
                "원본 첫 구역을 대상의 모든 구역에 반복",
            ],
            0,
            False,
        )
        if not accepted:
            return
        scope_label, accepted = QInputDialog.getItem(
            self,
            "적용 범위",
            "적용할 범위:",
            ["머리글과 바닥글", "머리글만", "바닥글만"],
            0,
            False,
        )
        if not accepted:
            return
        answer = QMessageBox.warning(
            self,
            "머리글·바닥글 적용 확인",
            f"'{asset.display_name}'의 머리글·바닥글을\n{target}\n에 적용합니다. "
            "대상 파일은 적용 전에 자동 백업됩니다. 계속합니까?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        options = HeaderFooterApplyOptions(
            section_mode=(
                "repeat-first"
                if mode_label.startswith("원본 첫")
                else "match-index"
            ),
            include_headers=scope_label != "바닥글만",
            include_footers=scope_label != "머리글만",
        )
        try:
            backup = self.header_footer_sdk.apply_asset(
                Path(asset.managed_path),
                Path(target),
                options,
            )
        except Exception as exc:
            QMessageBox.critical(self, "머리글·바닥글 적용 실패", str(exc))
            return
        self.service.cache.invalidate(Path(target))
        QMessageBox.information(
            self,
            "머리글·바닥글 적용 완료",
            f"대상: {target}\n백업: {backup}",
        )
