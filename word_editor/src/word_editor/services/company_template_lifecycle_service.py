from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

from word_editor.services.header_footer_review import (
    compare_header_footer_inventories,
)
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
    UnapprovedTemplateChanges,
)


class CompanyTemplateLifecycleService(TemplateLifecycleService):
    """Template lifecycle service with header/footer-aware reports."""

    def review_current_changes(self, profile_id: str | None = None):
        report = super().review_current_changes(profile_id)
        profile = self.registry.profiles[
            profile_id or self.registry.active_profile_id
        ]
        baseline_inventory = self._load_profile_inventory(profile)
        current_inventory = self.inventory_reader.capture(self.config.normal_path)
        added, removed, changed = compare_header_footer_inventories(
            baseline_inventory,
            current_inventory,
        )
        report.added_header_footers = added
        report.removed_header_footers = removed
        report.changed_header_footers = changed
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

        # Remove only the hidden Word process owned by this application. If the
        # user has a real Word window open, GetActiveObject still detects it and
        # the switch remains blocked.
        self._close_editor_owned_word()
        if self._word_is_running():
            raise TemplateLifecycleError(
                "프로필을 전환하려면 사용자가 연 Microsoft Word를 완전히 종료해야 합니다."
            )

        current_report = self.review_current_changes(
            self.registry.active_profile_id
        )
        # Review recreated the editor-owned hidden Word process. Close it again
        # before replacing the live Normal.dotm file.
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
