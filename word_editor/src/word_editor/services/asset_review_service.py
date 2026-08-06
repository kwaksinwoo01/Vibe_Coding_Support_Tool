from __future__ import annotations

import json
from pathlib import Path

from word_editor.domain.diff import changed_properties
from word_editor.domain.template_lifecycle import TemplateChangeReport, utc_now_iso
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
    compare_template_inventories,
)


def review_registered_asset(
    lifecycle: TemplateLifecycleService,
    asset_id: str,
) -> TemplateChangeReport:
    try:
        asset = lifecycle.registry.assets[asset_id]
    except KeyError as exc:
        raise TemplateLifecycleError(
            f"등록 템플릿 자산을 찾지 못했습니다: {asset_id}"
        ) from exc

    managed_path = Path(asset.managed_path)
    source_path = Path(asset.source_path)
    if not managed_path.exists():
        raise TemplateLifecycleError(
            f"보존된 템플릿 파일을 찾지 못했습니다: {managed_path}"
        )
    if not source_path.exists():
        raise TemplateLifecycleError(
            f"등록 당시 원본 템플릿을 찾지 못했습니다: {source_path}"
        )

    baseline_snapshot = lifecycle.gateway.snapshot_path(managed_path)
    current_snapshot = lifecycle.gateway.snapshot_path(source_path)
    baseline_inventory = lifecycle.inventory_reader.capture(managed_path)
    current_inventory = lifecycle.inventory_reader.capture(source_path)
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
    warnings = list(baseline_inventory.warnings)
    warnings.extend(current_inventory.warnings)
    return TemplateChangeReport(
        profile_id=f"asset:{asset.asset_id}",
        baseline_path=str(managed_path),
        current_path=str(source_path),
        created_at=utc_now_iso(),
        baseline_sha256=baseline_inventory.file_sha256,
        current_sha256=current_inventory.file_sha256,
        style_changes=changed_properties(
            baseline_snapshot,
            current_snapshot,
        ),
        added_building_blocks=added_blocks,
        removed_building_blocks=removed_blocks,
        changed_building_blocks=changed_blocks,
        added_autotext=added_autotext,
        removed_autotext=removed_autotext,
        warnings=warnings,
    )


def approve_registered_asset_update(
    lifecycle: TemplateLifecycleService,
    asset_id: str,
    report: TemplateChangeReport,
    note: str = "",
) -> Path:
    version_directory = lifecycle.update_registered_asset(asset_id, note)
    report_path = version_directory / "change-report.json"
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    return version_directory
