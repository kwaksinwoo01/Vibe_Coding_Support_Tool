from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
import zipfile

import pywintypes
import pythoncom
import win32com.client

from word_editor.config import EditorConfig
from word_editor.domain.diff import changed_properties
from word_editor.domain.template_lifecycle import (
    RegisteredTemplateAsset,
    TemplateAssetInventory,
    TemplateChangeReport,
    TemplateProfile,
    TemplateRegistry,
    utc_now_iso,
)
from word_editor.infrastructure.editable_word_com import EditableWordComGateway
from word_editor.infrastructure.snapshot_store import SnapshotStore
from word_editor.infrastructure.template_inventory import TemplateInventoryReader
from word_editor.infrastructure.template_registry_store import TemplateRegistryStore


class TemplateLifecycleError(RuntimeError):
    pass


class UnapprovedTemplateChanges(TemplateLifecycleError):
    def __init__(self, report: TemplateChangeReport) -> None:
        self.report = report
        super().__init__(
            "현재 활성 프로필의 Normal.dotm에 승인되지 않은 변경이 있습니다. "
            "변경 검증 후 프로필에 저장하거나 변경을 폐기한 뒤 전환하십시오."
        )


def _safe_slug(value: str, fallback: str = "template") -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", value.strip())
    normalized = normalized.strip("-_").lower()
    return normalized or fallback


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )


def _building_block_map(
    inventory: TemplateAssetInventory,
) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("key", "")): dict(item)
        for item in inventory.building_blocks
        if item.get("key")
    }


def compare_template_inventories(
    baseline: TemplateAssetInventory,
    current: TemplateAssetInventory,
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    baseline_blocks = _building_block_map(baseline)
    current_blocks = _building_block_map(current)
    baseline_keys = set(baseline_blocks)
    current_keys = set(current_blocks)
    added_blocks = sorted(current_keys - baseline_keys, key=str.casefold)
    removed_blocks = sorted(baseline_keys - current_keys, key=str.casefold)
    changed_blocks = sorted(
        key
        for key in baseline_keys & current_keys
        if baseline_blocks[key] != current_blocks[key]
    )
    baseline_autotext = set(baseline.autotext_entries)
    current_autotext = set(current.autotext_entries)
    added_autotext = sorted(
        current_autotext - baseline_autotext,
        key=str.casefold,
    )
    removed_autotext = sorted(
        baseline_autotext - current_autotext,
        key=str.casefold,
    )
    return (
        added_blocks,
        removed_blocks,
        changed_blocks,
        added_autotext,
        removed_autotext,
    )


class TemplateLifecycleService:
    def __init__(
        self,
        config: EditorConfig,
        gateway: EditableWordComGateway,
        snapshot_store: SnapshotStore,
        registry_store: TemplateRegistryStore | None = None,
    ) -> None:
        self.config = config
        self.gateway = gateway
        self.snapshot_store = snapshot_store
        self.registry_store = registry_store or TemplateRegistryStore()
        self.inventory_reader = TemplateInventoryReader(gateway)
        self.root = config.state_directory / "template-lifecycle"
        self.registry_path = self.root / "registry.json"
        self.profiles_directory = self.root / "profiles"
        self.assets_directory = self.root / "assets"
        self.reports_directory = self.root / "reports"
        self.packages_directory = self.root / "packages"
        self.activation_backups_directory = self.root / "activation-backups"
        self.registry = TemplateRegistry()

    def initialize(self) -> TemplateRegistry:
        for path in (
            self.root,
            self.profiles_directory,
            self.assets_directory,
            self.reports_directory,
            self.packages_directory,
            self.activation_backups_directory,
        ):
            path.mkdir(parents=True, exist_ok=True)
        self.registry = self.registry_store.load(self.registry_path)
        if not self.registry.profiles:
            self._create_default_dcm_profile()
        self._repair_active_profile()
        self._save_registry()
        return self.registry

    def _create_default_dcm_profile(self) -> None:
        if not self.config.normal_path.exists():
            raise TemplateLifecycleError(
                f"기본 Normal.dotm을 찾지 못했습니다: {self.config.normal_path}"
            )
        profile_id = "dcm-electronic"
        canonical = self._profile_canonical_path(profile_id)
        self.inventory_reader.make_preservation_copy(
            self.config.normal_path,
            canonical,
        )
        now = utc_now_iso()
        profile = TemplateProfile(
            profile_id=profile_id,
            display_name="DCM 전자문서",
            classification_code="DCM",
            canonical_path=str(canonical),
            created_at=now,
            updated_at=now,
            description="프로그램 최초 실행 시 현재 Normal.dotm에서 생성된 전자문서 프로필",
        )
        self.registry.profiles[profile_id] = profile
        self.registry.active_profile_id = profile_id
        self._write_profile_state(profile)

    def _repair_active_profile(self) -> None:
        if self.registry.active_profile_id in self.registry.profiles:
            return
        self.registry.active_profile_id = next(iter(self.registry.profiles), "")

    def _save_registry(self) -> None:
        self.registry_store.save(self.registry, self.registry_path)

    def _profile_directory(self, profile_id: str) -> Path:
        return self.profiles_directory / profile_id

    def _profile_canonical_path(self, profile_id: str) -> Path:
        return self._profile_directory(profile_id) / "current" / "Normal.dotm"

    def _profile_inventory_path(self, profile_id: str) -> Path:
        return self._profile_directory(profile_id) / "current" / "inventory.json"

    def _profile_snapshot_path(self, profile_id: str) -> Path:
        return self._profile_directory(profile_id) / "current" / "styles.json"

    def profiles(self) -> list[TemplateProfile]:
        return sorted(
            self.registry.profiles.values(),
            key=lambda item: (
                item.classification_code.casefold(),
                item.display_name.casefold(),
            ),
        )

    def assets(self) -> list[RegisteredTemplateAsset]:
        return sorted(
            self.registry.assets.values(),
            key=lambda item: item.display_name.casefold(),
        )

    def active_profile(self) -> TemplateProfile:
        try:
            return self.registry.profiles[self.registry.active_profile_id]
        except KeyError as exc:
            raise TemplateLifecycleError("활성 템플릿 프로필이 없습니다.") from exc

    def register_profile(
        self,
        source_path: Path,
        display_name: str,
        classification_code: str,
        description: str = "",
    ) -> TemplateProfile:
        source = source_path.expanduser().resolve()
        if source.suffix.casefold() != ".dotm":
            raise TemplateLifecycleError(
                "Normal 프로필 원본은 매크로 사용 가능 템플릿 .dotm이어야 합니다."
            )
        base_id = _safe_slug(
            f"{classification_code}-{display_name}",
            fallback="normal-profile",
        )
        profile_id = base_id
        sequence = 2
        while profile_id in self.registry.profiles:
            profile_id = f"{base_id}-{sequence}"
            sequence += 1
        canonical = self._profile_canonical_path(profile_id)
        self.inventory_reader.make_preservation_copy(source, canonical)
        now = utc_now_iso()
        profile = TemplateProfile(
            profile_id=profile_id,
            display_name=display_name.strip() or source.stem,
            classification_code=classification_code.strip().upper(),
            canonical_path=str(canonical),
            created_at=now,
            updated_at=now,
            description=description,
        )
        self.registry.profiles[profile_id] = profile
        self._write_profile_state(profile)
        self._save_registry()
        return profile

    def _write_profile_state(self, profile: TemplateProfile) -> None:
        canonical = Path(profile.canonical_path)
        inventory = self.inventory_reader.capture(canonical)
        snapshot = self.gateway.snapshot_path(canonical)
        _write_json(
            self._profile_inventory_path(profile.profile_id),
            inventory.to_dict(),
        )
        self.snapshot_store.save(
            snapshot,
            self._profile_snapshot_path(profile.profile_id),
        )

    def _load_profile_inventory(
        self,
        profile: TemplateProfile,
    ) -> TemplateAssetInventory:
        path = self._profile_inventory_path(profile.profile_id)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            return TemplateAssetInventory.from_dict(payload)
        inventory = self.inventory_reader.capture(Path(profile.canonical_path))
        _write_json(path, inventory.to_dict())
        return inventory

    def review_current_changes(
        self,
        profile_id: str | None = None,
    ) -> TemplateChangeReport:
        profile = self.registry.profiles[
            profile_id or self.registry.active_profile_id
        ]
        canonical = Path(profile.canonical_path)
        current_path = self.config.normal_path
        baseline_snapshot = self.gateway.snapshot_path(canonical)
        current_snapshot = self.gateway.snapshot_path(current_path)
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
        warnings = list(baseline_inventory.warnings)
        warnings.extend(current_inventory.warnings)
        report = TemplateChangeReport(
            profile_id=profile.profile_id,
            baseline_path=str(canonical),
            current_path=str(current_path),
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
        report_path = self.reports_directory / (
            f"{profile.profile_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        _write_json(report_path, report.to_dict())
        return report

    def approve_current_changes(
        self,
        note: str = "",
    ) -> tuple[TemplateChangeReport, Path]:
        profile = self.active_profile()
        report = self.review_current_changes(profile.profile_id)
        version_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        version_directory = (
            self._profile_directory(profile.profile_id)
            / "versions"
            / version_id
        )
        version_template = version_directory / "Normal.dotm"
        self.inventory_reader.make_preservation_copy(
            self.config.normal_path,
            version_template,
        )
        version_inventory = self.inventory_reader.capture(version_template)
        version_snapshot = self.gateway.snapshot_path(version_template)
        _write_json(version_directory / "inventory.json", version_inventory.to_dict())
        self.snapshot_store.save(
            version_snapshot,
            version_directory / "styles.json",
        )
        _write_json(version_directory / "change-report.json", report.to_dict())
        _write_json(
            version_directory / "version.json",
            {
                "profile_id": profile.profile_id,
                "version_id": version_id,
                "approved_at": utc_now_iso(),
                "note": note,
                "source_path": str(self.config.normal_path),
                "template_sha256": version_inventory.file_sha256,
            },
        )
        canonical = Path(profile.canonical_path)
        self.inventory_reader.make_preservation_copy(
            version_template,
            canonical,
        )
        profile.updated_at = utc_now_iso()
        self._write_profile_state(profile)
        self._save_registry()
        return report, version_directory

    @staticmethod
    def _word_is_running() -> bool:
        pythoncom.CoInitialize()
        try:
            try:
                win32com.client.GetActiveObject("Word.Application")
            except (pywintypes.com_error, AttributeError):
                return False
            return True
        finally:
            pythoncom.CoUninitialize()

    def activate_profile(
        self,
        profile_id: str,
        discard_unapproved_changes: bool = False,
    ) -> Path:
        if profile_id not in self.registry.profiles:
            raise TemplateLifecycleError(f"프로필을 찾지 못했습니다: {profile_id}")
        if profile_id == self.registry.active_profile_id:
            return self.config.normal_path
        if self._word_is_running():
            raise TemplateLifecycleError(
                "프로필을 전환하려면 Microsoft Word를 완전히 종료해야 합니다."
            )
        current_report = self.review_current_changes(
            self.registry.active_profile_id
        )
        if current_report.has_changes and not discard_unapproved_changes:
            raise UnapprovedTemplateChanges(current_report)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.activation_backups_directory / (
            f"Normal.before-{self.registry.active_profile_id}-to-{profile_id}-{timestamp}.dotm"
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

    def register_asset(
        self,
        source_path: Path,
        display_name: str,
        role: str = "header-building-block-template",
        description: str = "",
        attach_to_active_profile: bool = True,
    ) -> RegisteredTemplateAsset:
        source = source_path.expanduser().resolve()
        if source.suffix.casefold() not in {".dotm", ".dotx"}:
            raise TemplateLifecycleError(
                "등록 템플릿 자산은 .dotm 또는 .dotx 파일이어야 합니다."
            )
        base_id = _safe_slug(display_name or source.stem, "template-asset")
        asset_id = base_id
        sequence = 2
        while asset_id in self.registry.assets:
            asset_id = f"{base_id}-{sequence}"
            sequence += 1
        asset_directory = self.assets_directory / asset_id / "current"
        managed = asset_directory / source.name
        self.inventory_reader.make_preservation_copy(source, managed)
        now = utc_now_iso()
        asset = RegisteredTemplateAsset(
            asset_id=asset_id,
            display_name=display_name.strip() or source.stem,
            role=role,
            managed_path=str(managed),
            source_path=str(source),
            created_at=now,
            updated_at=now,
            description=description,
        )
        self.registry.assets[asset_id] = asset
        inventory = self.inventory_reader.capture(managed)
        _write_json(asset_directory / "inventory.json", inventory.to_dict())
        snapshot = self.gateway.snapshot_path(managed)
        self.snapshot_store.save(snapshot, asset_directory / "styles.json")
        if attach_to_active_profile:
            profile = self.active_profile()
            if asset_id not in profile.asset_ids:
                profile.asset_ids.append(asset_id)
                profile.updated_at = utc_now_iso()
        self._save_registry()
        return asset

    def update_registered_asset(
        self,
        asset_id: str,
        note: str = "",
    ) -> Path:
        asset = self.registry.assets[asset_id]
        source = Path(asset.source_path)
        if not source.exists():
            raise TemplateLifecycleError(
                f"등록 당시 원본 템플릿을 찾지 못했습니다: {source}"
            )
        version_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        asset_root = self.assets_directory / asset_id
        version_directory = asset_root / "versions" / version_id
        version_path = version_directory / source.name
        self.inventory_reader.make_preservation_copy(source, version_path)
        inventory = self.inventory_reader.capture(version_path)
        _write_json(version_directory / "inventory.json", inventory.to_dict())
        _write_json(
            version_directory / "version.json",
            {
                "asset_id": asset_id,
                "version_id": version_id,
                "approved_at": utc_now_iso(),
                "note": note,
                "template_sha256": inventory.file_sha256,
            },
        )
        managed = Path(asset.managed_path)
        self.inventory_reader.make_preservation_copy(version_path, managed)
        asset.updated_at = utc_now_iso()
        _write_json(
            managed.parent / "inventory.json",
            self.inventory_reader.capture(managed).to_dict(),
        )
        self._save_registry()
        return version_directory

    def create_distribution_package(
        self,
        profile_id: str,
        output_directory: Path,
        version_label: str,
        note: str = "",
    ) -> Path:
        profile = self.registry.profiles[profile_id]
        canonical = Path(profile.canonical_path)
        inventory = self.inventory_reader.capture(canonical)
        safe_version = _safe_slug(version_label, "release")
        output_directory.mkdir(parents=True, exist_ok=True)
        package_path = output_directory / (
            f"Company-Word-{profile.classification_code or profile.profile_id}-{safe_version}.zip"
        )
        with tempfile.TemporaryDirectory(prefix="word-template-package-") as temp:
            root = Path(temp) / "CompanyWordTemplate"
            root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(canonical, root / "Normal.dotm")
            packaged_assets: list[dict[str, Any]] = []
            assets_root = root / "CompanyTemplates"
            for asset_id in profile.asset_ids:
                asset = self.registry.assets.get(asset_id)
                if asset is None:
                    continue
                assets_root.mkdir(parents=True, exist_ok=True)
                source = Path(asset.managed_path)
                destination = assets_root / source.name
                shutil.copy2(source, destination)
                packaged_assets.append(
                    {
                        "asset_id": asset.asset_id,
                        "display_name": asset.display_name,
                        "role": asset.role,
                        "file_name": destination.name,
                        "sha256": self.inventory_reader._sha256(destination),
                    }
                )
            manifest = {
                "schema_version": 1,
                "profile_id": profile.profile_id,
                "display_name": profile.display_name,
                "classification_code": profile.classification_code,
                "version_label": version_label,
                "created_at": utc_now_iso(),
                "note": note,
                "normal_dotm": {
                    "file_name": "Normal.dotm",
                    "sha256": inventory.file_sha256,
                    "file_size": inventory.file_size,
                    "styles_sha256": inventory.styles_sha256,
                    "building_block_count": len(inventory.building_blocks),
                    "autotext_count": len(inventory.autotext_entries),
                },
                "assets": packaged_assets,
            }
            _write_json(root / "manifest.json", manifest)
            (root / "Install-CompanyWordTemplate.ps1").write_text(
                self._installer_script(inventory.file_sha256),
                encoding="utf-8-sig",
            )
            with zipfile.ZipFile(
                package_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for file_path in root.rglob("*"):
                    if file_path.is_file():
                        archive.write(
                            file_path,
                            file_path.relative_to(root.parent),
                        )
        return package_path

    @staticmethod
    def _installer_script(expected_sha256: str) -> str:
        return f'''[CmdletBinding()]
param(
    [string]$NormalPath = "$env:APPDATA\\Microsoft\\Templates\\Normal.dotm"
)
$ErrorActionPreference = "Stop"
if (Get-Process WINWORD -ErrorAction SilentlyContinue) {{
    throw "Microsoft Word를 완전히 종료한 뒤 다시 실행하십시오."
}}
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceNormal = Join-Path $packageRoot "Normal.dotm"
if (-not (Test-Path -LiteralPath $sourceNormal)) {{
    throw "패키지의 Normal.dotm을 찾지 못했습니다."
}}
$actualHash = (Get-FileHash -LiteralPath $sourceNormal -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne "{expected_sha256.lower()}") {{
    throw "패키지 Normal.dotm SHA-256이 manifest와 다릅니다."
}}
$targetDirectory = Split-Path -Parent $NormalPath
New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
if (Test-Path -LiteralPath $NormalPath) {{
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item -LiteralPath $NormalPath -Destination "$NormalPath.before-company-$stamp.bak" -Force
}}
Copy-Item -LiteralPath $sourceNormal -Destination $NormalPath -Force
$companySource = Join-Path $packageRoot "CompanyTemplates"
$companyTarget = Join-Path $targetDirectory "CompanyTemplates"
if (Test-Path -LiteralPath $companySource) {{
    New-Item -ItemType Directory -Path $companyTarget -Force | Out-Null
    Copy-Item -Path (Join-Path $companySource "*") -Destination $companyTarget -Recurse -Force
}}
Write-Host "회사 Word 템플릿 설치 완료: $NormalPath"
'''
