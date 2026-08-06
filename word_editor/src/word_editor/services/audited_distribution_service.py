from __future__ import annotations

import json
from pathlib import Path
import zipfile

from word_editor.domain.template_lifecycle import TemplateChangeReport
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
)


class UnapprovedDistributionChanges(TemplateLifecycleError):
    def __init__(self, report: TemplateChangeReport) -> None:
        self.report = report
        super().__init__(
            "활성 프로필의 실제 Normal.dotm에 미승인 변경이 있습니다. "
            "현재 변경 검증·저장을 완료한 뒤 배포 패키지를 생성하십시오."
        )


def _zip_json(
    archive: zipfile.ZipFile,
    name: str,
    payload: dict[str, object],
) -> None:
    archive.writestr(
        name,
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
    )


def create_audited_distribution_package(
    lifecycle: TemplateLifecycleService,
    profile_id: str,
    output_directory: Path,
    version_label: str,
    note: str = "",
) -> Path:
    if profile_id == lifecycle.registry.active_profile_id:
        report = lifecycle.review_current_changes(profile_id)
        if report.has_changes:
            raise UnapprovedDistributionChanges(report)

    package_path = lifecycle.create_distribution_package(
        profile_id,
        output_directory,
        version_label,
        note,
    )
    profile = lifecycle.registry.profiles[profile_id]
    inventory_path = lifecycle._profile_inventory_path(profile_id)
    styles_path = lifecycle._profile_snapshot_path(profile_id)

    with zipfile.ZipFile(
        package_path,
        mode="a",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        _zip_json(
            archive,
            "CompanyWordTemplate/audit/profile.json",
            profile.to_dict(),
        )
        if inventory_path.exists():
            archive.write(
                inventory_path,
                "CompanyWordTemplate/audit/normal-inventory.json",
            )
        if styles_path.exists():
            archive.write(
                styles_path,
                "CompanyWordTemplate/audit/normal-styles.json",
            )
        for asset_id in profile.asset_ids:
            asset = lifecycle.registry.assets.get(asset_id)
            if asset is None:
                continue
            _zip_json(
                archive,
                f"CompanyWordTemplate/audit/assets/{asset_id}/asset.json",
                asset.to_dict(),
            )
            asset_inventory = Path(asset.managed_path).parent / "inventory.json"
            if asset_inventory.exists():
                archive.write(
                    asset_inventory,
                    f"CompanyWordTemplate/audit/assets/{asset_id}/inventory.json",
                )
    return package_path
