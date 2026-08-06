from __future__ import annotations

from word_editor.services.header_footer_review import (
    compare_header_footer_inventories,
)
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleService,
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
