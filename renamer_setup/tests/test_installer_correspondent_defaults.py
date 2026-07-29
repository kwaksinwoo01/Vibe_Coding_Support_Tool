from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_private_correspondent_input_is_ignored_by_git() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "private/correspondent.txt" in gitignore.splitlines()


def test_installer_packages_defaults_and_runs_three_way_sync() -> None:
    installer = (PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi").read_text(
        encoding="utf-8-sig"
    )

    embedded_copy = (
        'File /oname=correspondent.defaults.txt "${CORRESPONDENT_SOURCE_FILE}"'
    )
    configure = 'classifier.exe" configure --default-name'
    synchronize = (
        'classifier.exe" sync-correspondents --defaults '
        '"$INSTDIR\\support\\correspondent.defaults.txt"'
    )

    assert embedded_copy in installer
    assert installer.index(embedded_copy) < installer.index(configure)
    assert installer.index(configure) < installer.index(synchronize)
    assert '--release-version "${PRODUCT_VERSION}"' in installer
    assert "거래처 목록 병합에 실패했습니다" in installer
    assert 'File /oname=correspondent.txt "${CORRESPONDENT_SOURCE_FILE}"' not in installer


def test_build_supports_default_and_explicit_private_input() -> None:
    build_script = (PROJECT_ROOT / "scripts" / "build.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "[string]$CorrespondentFile = ''" in build_script
    assert "private\\correspondent.txt" in build_script
    assert "/DCORRESPONDENT_SOURCE_FILE=" in build_script
    assert "CorrespondentFile must be UTF-8 with BOM" in build_script


def test_installer_output_uses_the_release_name() -> None:
    installer = (PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi").read_text(
        encoding="utf-8-sig"
    )
    build_script = (PROJECT_ROOT / "scripts" / "build.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert '!define PRODUCT_FILE_VERSION "7.4.1"' in installer
    assert 'OutFile "..\\dist\\ReNamer_Setup_${PRODUCT_FILE_VERSION}.exe"' in installer
    assert "dist\\ReNamer_Setup_7.4.1.exe" in build_script
    assert "$PreviousInstaller" in build_script
    assert "dist\\ReNamer_Setup_7.4.exe" in build_script
    assert "$OlderInstaller" in build_script
    assert "dist\\ReNamer_Setup_7.3.exe" in build_script
    assert "dist\\ReNamer_Setup.exe" in build_script


def test_installer_packages_optional_paddleocr_runner_and_installer() -> None:
    installer = (PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi").read_text(
        encoding="utf-8-sig"
    )
    verifier = (
        PROJECT_ROOT / "scripts" / "verify_text_encoding.ps1"
    ).read_text(encoding="utf-8-sig")
    paddle_installer = (
        PROJECT_ROOT / "scripts" / "install_paddleocr.ps1"
    ).read_text(encoding="utf-8-sig")

    assert 'File "..\\scripts\\install_paddleocr.ps1"' in installer
    assert 'File "..\\scripts\\paddleocr_runner.py"' in installer
    assert installer.count("PaddleOCR 보조 엔진 설치.lnk") == 1
    assert "scripts\\install_paddleocr.ps1" in verifier
    assert "paddleocr==3.7.0" in paddle_installer
    assert "onnxruntime>=1.23,<2" in paddle_installer
    assert 'Write-InstallLog "PaddleOCR 설치 실패: $failureMessage"' in paddle_installer


def test_installer_automatically_prepares_paddleocr_with_safe_fallback() -> None:
    installer = (PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi").read_text(
        encoding="utf-8-sig"
    )

    packaged_installer = 'File "..\\scripts\\install_paddleocr.ps1"'
    automatic_install = (
        "nsExec::Exec 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass "
        '-File "$INSTDIR\\support\\install_paddleocr.ps1" -InstallRoot "$INSTDIR"\''
    )

    assert installer.index(packaged_installer) < installer.index(automatic_install)
    assert "PaddleOCR 자동 설치에 실패했습니다" in installer
    assert "Tesseract 분류는 계속 사용할 수 있으며" in installer
    assert "PaddleOCR 보조 엔진과 한국어 모델 설치가 완료되었습니다" in installer


def test_installer_uses_release_icons_and_minimal_shortcuts() -> None:
    installer = (PROJECT_ROOT / "installer" / "ReNamer_Setup.nsi").read_text(
        encoding="utf-8-sig"
    )
    classifier_spec = (PROJECT_ROOT / "classifier.spec").read_text(
        encoding="utf-8"
    )
    classifier_icon = PROJECT_ROOT / "assets" / "classifier_ico_pack.ico"
    correspondents_icon = PROJECT_ROOT / "assets" / "correspondents_ico_pack.ico"

    assert classifier_icon.read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert correspondents_icon.read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert 'icon="assets/classifier_ico_pack.ico"' in classifier_spec
    assert '!define MUI_ICON "..\\assets\\classifier_ico_pack.ico"' in installer
    assert 'File "..\\assets\\classifier_ico_pack.ico"' in installer
    assert 'File "..\\assets\\correspondents_ico_pack.ico"' in installer
    assert (
        '"open-correspondents" \\\n'
        '    "$INSTDIR\\assets\\correspondents_ico_pack.ico"'
    ) in installer

    assert "MUI_FINISHPAGE_RUN" not in installer
    assert installer.count("분류 로그 열기.lnk") == 1
    assert installer.count("분류 로그 초기화.lnk") == 1
    assert installer.count("PaddleOCR 보조 엔진 설치.lnk") == 1
    assert "CreateShortCut \\\n    \"$SMPROGRAMS\\ReNamer Document Classifier\\제거.lnk\"" not in installer
    assert (
        '"$SMPROGRAMS\\ReNamer Document Classifier\\'
        'ReNamer_Setup_${PRODUCT_FILE_VERSION}_Uninstall .lnk"'
    ) in installer


def test_paddleocr_runner_has_valid_python_syntax() -> None:
    runner = (PROJECT_ROOT / "scripts" / "paddleocr_runner.py").read_text(
        encoding="utf-8"
    )

    compile(runner, "paddleocr_runner.py", "exec")


def test_pascal_script_supports_correspondent_alias_mappings() -> None:
    pascal_script = (
        PROJECT_ROOT / "renamer" / "7.4_자동이름 변경 시스템.pas"
    ).read_text(encoding="utf-8-sig")

    assert "KnownCorrespondentTerms" in pascal_script
    assert "KnownCorrespondentDisplayNames" in pascal_script
    assert "WidePos('=>', Value)" in pascal_script
    assert "RemoveCorrespondentTerms" in pascal_script
