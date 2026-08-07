from __future__ import annotations

from pathlib import Path
import re
import tomllib

from renamer_document_classifier import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_synchronized() -> None:
    pyproject = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    package_version = pyproject["project"]["version"]

    installer = (
        PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi"
    ).read_text(encoding="utf-8-sig")

    build_script = (
        PROJECT_ROOT / "scripts" / "build.ps1"
    ).read_text(encoding="utf-8-sig")

    installer_match = re.search(
        r'!define PRODUCT_VERSION "([^"]+)"',
        installer,
    )
    assert installer_match is not None

    versions = {
        package_version,
        __version__,
        installer_match.group(1),
    }

    assert versions == {"7.4.2"}
    assert "dist\\ReNamer_Setup_7.4.2.exe" in build_script
    