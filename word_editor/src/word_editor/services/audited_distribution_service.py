from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from word_editor.domain.template_lifecycle import TemplateChangeReport
from word_editor.services.template_lifecycle_service import (
    TemplateLifecycleError,
    TemplateLifecycleService,
)

GLOBAL_TEMPLATE_ROLES = frozenset(
    {
        "header-building-block-template",
        "document-building-block-template",
    }
)


class UnapprovedDistributionChanges(TemplateLifecycleError):
    def __init__(self, report: TemplateChangeReport) -> None:
        self.report = report
        super().__init__(
            "활성 프로필의 실제 Normal.dotm에 미승인 변경이 있습니다. "
            "현재 변경 검증·저장을 완료한 뒤 배포 패키지를 생성하십시오."
        )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )


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
$manifestPath = Join-Path $packageRoot "manifest.json"
$sourceNormal = Join-Path $packageRoot "Normal.dotm"
if (-not (Test-Path -LiteralPath $manifestPath)) {{
    throw "패키지 manifest.json을 찾지 못했습니다."
}}
if (-not (Test-Path -LiteralPath $sourceNormal)) {{
    throw "패키지 Normal.dotm을 찾지 못했습니다."
}}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
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
$assetSourceRoot = Join-Path $packageRoot "CompanyTemplates"
$normalTemplateAssetRoot = Join-Path $targetDirectory "CompanyTemplates"
$wordStartupAssetRoot = Join-Path $env:APPDATA "Microsoft\\Word\\STARTUP"
foreach ($asset in @($manifest.assets)) {{
    $source = Join-Path $assetSourceRoot $asset.file_name
    if (-not (Test-Path -LiteralPath $source)) {{
        throw "등록 템플릿 파일을 찾지 못했습니다: $($asset.file_name)"
    }}
    $assetHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($assetHash -ne ([string]$asset.sha256).ToLowerInvariant()) {{
        throw "등록 템플릿 SHA-256이 manifest와 다릅니다: $($asset.file_name)"
    }}
    if ($asset.install_destination -eq "word-startup") {{
        $destinationRoot = $wordStartupAssetRoot
    }} else {{
        $destinationRoot = $normalTemplateAssetRoot
    }}
    New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination (Join-Path $destinationRoot $asset.file_name) -Force
}}
Write-Host "회사 Word 템플릿 설치 완료: $NormalPath"
Write-Host "머리글/문서블록 템플릿은 Word STARTUP 전역 템플릿 폴더에 설치되었습니다."
'''


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

    with tempfile.TemporaryDirectory(prefix="audited-word-package-") as temp:
        extraction_root = Path(temp) / "extracted"
        with zipfile.ZipFile(package_path, mode="r") as archive:
            archive.extractall(extraction_root)
        package_root = extraction_root / "CompanyWordTemplate"
        manifest_path = package_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        for asset_record in manifest.get("assets", []):
            role = str(asset_record.get("role", ""))
            asset_record["install_destination"] = (
                "word-startup"
                if role in GLOBAL_TEMPLATE_ROLES
                else "templates"
            )
        manifest["installation_policy"] = {
            "normal_dotm": "%APPDATA%/Microsoft/Templates/Normal.dotm",
            "global_building_block_templates": (
                "%APPDATA%/Microsoft/Word/STARTUP"
            ),
            "other_company_templates": (
                "%APPDATA%/Microsoft/Templates/CompanyTemplates"
            ),
        }
        _write_json(manifest_path, manifest)

        audit_root = package_root / "audit"
        _write_json(audit_root / "profile.json", profile.to_dict())
        if inventory_path.exists():
            shutil.copy2(
                inventory_path,
                audit_root / "normal-inventory.json",
            )
        if styles_path.exists():
            shutil.copy2(
                styles_path,
                audit_root / "normal-styles.json",
            )
        for asset_id in profile.asset_ids:
            asset = lifecycle.registry.assets.get(asset_id)
            if asset is None:
                continue
            asset_audit_root = audit_root / "assets" / asset_id
            _write_json(asset_audit_root / "asset.json", asset.to_dict())
            asset_inventory = Path(asset.managed_path).parent / "inventory.json"
            if asset_inventory.exists():
                asset_audit_root.mkdir(parents=True, exist_ok=True)
                shutil.copy2(
                    asset_inventory,
                    asset_audit_root / "inventory.json",
                )

        normal_hash = str(manifest["normal_dotm"]["sha256"])
        (package_root / "Install-CompanyWordTemplate.ps1").write_text(
            _installer_script(normal_hash),
            encoding="utf-8-sig",
        )

        replacement = Path(temp) / "replacement.zip"
        with zipfile.ZipFile(
            replacement,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for file_path in package_root.rglob("*"):
                if file_path.is_file():
                    archive.write(
                        file_path,
                        file_path.relative_to(package_root.parent),
                    )
        replacement.replace(package_path)
    return package_path
