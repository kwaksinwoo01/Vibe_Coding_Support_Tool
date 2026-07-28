from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_private_correspondent_input_is_ignored_by_git() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "private/correspondent.txt" in gitignore.splitlines()


def test_installer_copies_default_before_configure_and_preserves_existing_file() -> None:
    installer = (PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi").read_text(
        encoding="utf-8-sig"
    )

    preserve_check = (
        'IfFileExists "$INSTDIR\\config\\correspondent.txt" '
        "CorrespondentPreserved"
    )
    embedded_copy = 'File /oname=correspondent.txt "${CORRESPONDENT_SOURCE_FILE}"'
    configure = 'classifier.exe" configure --default-name'

    assert preserve_check in installer
    assert embedded_copy in installer
    assert installer.index(preserve_check) < installer.index(embedded_copy)
    assert installer.index(embedded_copy) < installer.index(configure)


def test_build_supports_default_and_explicit_private_input() -> None:
    build_script = (PROJECT_ROOT / "scripts" / "build.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "[string]$CorrespondentFile = ''" in build_script
    assert "private\\correspondent.txt" in build_script
    assert "/DCORRESPONDENT_SOURCE_FILE=" in build_script
    assert "CorrespondentFile must be UTF-8 with BOM" in build_script


def test_pascal_script_supports_correspondent_alias_mappings() -> None:
    pascal_script = (
        PROJECT_ROOT / "renamer" / "7.3_자동이름 변경 시스템.pas"
    ).read_text(encoding="utf-8-sig")

    assert "KnownCorrespondentTerms" in pascal_script
    assert "KnownCorrespondentDisplayNames" in pascal_script
    assert "WidePos('=>', Value)" in pascal_script
    assert "RemoveCorrespondentTerms" in pascal_script
