"""Build and release-source validation for ReNamer."""

from __future__ import annotations

from dataclasses import dataclass
import re
import tomllib

from renamer_sdk.core_sdk import OperationResult, OperationStatus
from renamer_sdk.integration_sdk import RepositoryLayout


@dataclass(frozen=True, slots=True)
class ReleaseVersionSnapshot:
    pyproject: str
    installer_product: str
    installer_file: str
    build_output: str


_VERSION = r"([0-9]+(?:\.[0-9]+)+)"


def inspect_release_versions(layout: RepositoryLayout) -> ReleaseVersionSnapshot:
    pyproject_data = tomllib.loads(layout.pyproject.read_text(encoding="utf-8"))
    pyproject_version = str(pyproject_data["project"]["version"])

    installer = layout.installer.read_text(encoding="utf-8-sig")
    product_match = re.search(r'!define PRODUCT_VERSION "' + _VERSION + r'"', installer)
    file_match = re.search(r'!define PRODUCT_FILE_VERSION "' + _VERSION + r'"', installer)
    if product_match is None or file_match is None:
        raise ValueError("Installer release version definitions were not found.")

    build = layout.build_script.read_text(encoding="utf-8-sig")
    build_match = re.search(r"ReNamer_Setup_" + _VERSION + r"\.exe", build)
    if build_match is None:
        raise ValueError("Build output version was not found.")

    return ReleaseVersionSnapshot(
        pyproject=pyproject_version,
        installer_product=product_match.group(1),
        installer_file=file_match.group(1),
        build_output=build_match.group(1),
    )


def validate_release_versions(
    snapshot: ReleaseVersionSnapshot,
) -> OperationResult[ReleaseVersionSnapshot]:
    versions = {
        snapshot.pyproject,
        snapshot.installer_product,
        snapshot.installer_file,
        snapshot.build_output,
    }
    if len(versions) == 1:
        return OperationResult(OperationStatus.PASSED, snapshot)
    return OperationResult(
        OperationStatus.FAILED,
        snapshot,
        ("Release version sources are not synchronized.",),
    )
