from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

from word_editor.domain.diff import changed_properties
from word_editor.domain.models import TemplateSnapshot
from word_editor.domain.template_lifecycle import (
    TemplateChangeReport,
    utc_now_iso,
)
from word_editor.infrastructure.openxml_style_index import (
    OpenXmlStyleIndexError,
    OpenXmlStyleIndexReader,
)
from word_editor.services.header_footer_review import (
    compare_header_footer_inventories,
)
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
    UnapprovedTemplateChanges,
    _write_json,
    compare_template_inventories,
)


class CompanyTemplateLifecycleService(TemplateLifecycleService):
    """Header/footer-aware lifecycle service with candidate-only style audits."""

    @staticmethod
    def _detail_snapshot(
        path: Path,
        styles,
        label: str,
    ) -> TemplateSnapshot:
        return TemplateSnapshot(
            source_path=str(path),
            sha256=label,
            captured_at=utc_now_iso(),
            word_version="OpenXML+COM",
            styles=styles,
        )

    def _candidate_style_changes(
        self,
        baseline_path: Path,
        current_path: Path,
    ):
        reader = OpenXmlStyleIndexReader()
        try:
            difference = reader.compare(baseline_path, current_path)
            baseline_names = list((*difference.changed, *difference.removed))
            current_names = list((*difference.changed, *difference.added))
            baseline_details = self.gateway.read_style_details(
                baseline_path,
                baseline_names,
            )
            current_details = self.gateway.read_style_details(
                current_path,
                current_names,
            )
            return changed_properties(
                self._detail_snapshot(
                    baseline_path,
                    baseline_details,
                    "lifecycle-before",
                ),
                self._detail_snapshot(
                    current_path,
                    current_details,
                    "lifecycle-after",
                ),
            )
        except (OpenXmlStyleIndexError, KeyError, RuntimeError):
            baseline_snapshot = self.gateway.snapshot_path(baseline_path)
            current_snapshot = self.gateway.snapshot_path(current_path)
            return changed_properties(baseline_snapshot, current_snapshot)

    def review_current_changes(self, profile_id: str | None = None):
        profile = self.registry.profiles[
            profile_id or self.registry.active_profile_id
        ]
        canonical = Path(profile.canonical_path)
        current_path = self.config.normal_path
        baseline_inventory = self._load_profile_inventory(profile)
        current_inventory = self.inventory_reader.capture(current_path)
        (
            added_blocks,
            removed_blocks,
            changed_blocks,
            added_autotext,
            removed_autotext,
        ) = compare_template_inventories(
            baseline_inventory,
            current_inventory,
        )
        added_headers, removed_headers, changed_headers = (
            compare_header_footer_inventories(
                baseline_inventory,
                current_inventory,
            )
        )
        style_changes = self._candidate_style_changes(
            canonical,
            current_path,
        )
        warnings = list(baseline_inventory.warnings)
        warnings.extend(current_inventory.warnings)
        report = TemplateChangeReport(
            profile_id=profile.profile_id,
            baseline_path=str(canonical),
            current_path=str(current_path),
            created_at=utc_now_iso(),
            baseline_sha256=baseline_inventory.file_sha256,
            current_sha256=current_inventory.file_sha256,
            style_changes=style_changes,
            added_building_blocks=added_blocks,
            removed_building_blocks=removed_blocks,
            changed_building_blocks=changed_blocks,
            added_autotext=added_autotext,
            removed_autotext=removed_autotext,
            added_header_footers=added_headers,
            removed_header_footers=removed_headers,
            changed_header_footers=changed_headers,
            warnings=warnings,
        )
        report_path = self.reports_directory / (
            f"{profile.profile_id}-"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        _write_json(report_path, report.to_dict())
        return report

    def _close_editor_owned_word(self) -> None:
        close_gateway = getattr(self.gateway, "close", None)
        if callable(close_gateway):
            close_gateway()

    def activate_profile(
        self,
        profile_id: str,
        discard_unapproved_changes: bool = False,
    ) -> Path:
        if profile_id not in self.registry.profiles:
            raise TemplateLifecycleError(f"프로필을 찾지 못했습니다: {profile_id}")
        if profile_id == self.registry.active_profile_id:
            return self.config.normal_path

        self._close_editor_owned_word()
        if self._word_is_running():
            raise TemplateLifecycleError(
                "프로필을 전환하려면 사용자가 연 Microsoft Word를 완전히 종료해야 합니다."
            )

        current_report = self.review_current_changes(
            self.registry.active_profile_id
        )
        self._close_editor_owned_word()
        if current_report.has_changes and not discard_unapproved_changes:
            raise UnapprovedTemplateChanges(current_report)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.activation_backups_directory / (
            f"Normal.before-{self.registry.active_profile_id}-to-"
            f"{profile_id}-{timestamp}.dotm"
        )
        self.inventory_reader.make_preservation_copy(
            self.config.normal_path,
            backup,
        )
        selected = self.registry.profiles[profile_id]
        shutil.copy2(Path(selected.canonical_path), self.config.normal_path)
        self.registry.active_profile_id = profile_id
        self._save_registry()
        return backup
