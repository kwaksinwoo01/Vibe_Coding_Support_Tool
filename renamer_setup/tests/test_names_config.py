from pathlib import Path

from renamer_document_classifier.names_config import (
    load_user_config,
    names_path,
    resolve_person_name,
    save_user_config,
)


def test_installer_configuration_is_saved_for_python_and_pascal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(tmp_path))

    saved = save_user_config(
        "홍길동",
        ["홍길동", "김민규", "홍길동", " 이슬기 "],
    )

    assert saved.default_name == "홍길동"
    assert saved.known_names == ("홍길동", "김민규", "이슬기")
    assert names_path().read_text(encoding="utf-8-sig").splitlines() == [
        "홍길동",
        "김민규",
        "이슬기",
    ]

    loaded = load_user_config()
    assert loaded == saved


def test_person_name_is_resolved_from_filename_or_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(tmp_path))
    save_user_config("홍길동", ["김민규", "이슬기"])

    assert resolve_person_name("에아스텍 김민규 2026-01-05.pdf") == "김민규"
    assert resolve_person_name("에아스텍 2026-01-05.pdf") == "홍길동"
