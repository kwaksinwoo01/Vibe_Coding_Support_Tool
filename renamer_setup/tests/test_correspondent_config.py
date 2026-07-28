from __future__ import annotations

from pathlib import Path

from renamer_document_classifier.correspondent_config import (
    correspondent_path,
    ensure_correspondent_file,
    load_correspondents,
    normalize_correspondents,
    resolve_correspondent,
)


def test_correspondent_file_is_created_empty_and_not_overwritten(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(tmp_path))

    created = ensure_correspondent_file()
    assert created == correspondent_path()
    assert created.read_text(encoding="utf-8-sig") == ""

    created.write_text("등록거래처A\n", encoding="utf-8-sig")
    ensure_correspondent_file()
    assert created.read_text(encoding="utf-8-sig") == "등록거래처A\n"


def test_correspondents_ignore_comments_duplicates_and_self_company() -> None:
    assert normalize_correspondents(
        [
            "# 한 줄에 한 업체",
            "등록거래처A",
            " 등록거래처A ",
            "등록거래처B",
            "에아스텍",
            "ERSTEQ Co., Ltd.",
            "",
        ]
    ) == ("등록거래처A", "등록거래처B")


def test_only_registered_correspondent_is_resolved() -> None:
    registered = ("등록거래처A", "PARTNER_ALPHA")

    assert resolve_correspondent(
        "공급자 주식회사 에아스텍 공급받는자 등록거래처A",
        registered,
    ) == "등록거래처A"
    assert resolve_correspondent("미등록바이오", registered) == ""
    assert resolve_correspondent("ERSTEQ Co., Ltd.", registered) == ""


def test_filename_is_preferred_before_extracted_document_text() -> None:
    registered = ("PARTNER_ALPHA", "등록거래처A")

    assert resolve_correspondent(
        ("담당자_PARTNER_ALPHA_견적서.pdf", "공급받는자 등록거래처A"),
        registered,
    ) == "PARTNER_ALPHA"


def test_correspondents_are_loaded_from_utf8_bom_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(tmp_path))
    path = ensure_correspondent_file()
    path.write_text("# private entries\n등록거래처A\n에아스텍\n", encoding="utf-8-sig")

    assert load_correspondents() == ("등록거래처A",)
