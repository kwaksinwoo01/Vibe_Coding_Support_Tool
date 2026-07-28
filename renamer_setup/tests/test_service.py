from __future__ import annotations

from pathlib import Path
from unittest.mock import call, patch

from renamer_document_classifier.classification import DocumentKind
from renamer_document_classifier.correspondent_config import normalize_correspondents
from renamer_document_classifier.extractors import ExtractionLimits, ExtractionResult
from renamer_document_classifier.service import (
    _extract_pdf_ocr_adaptively,
    inspect_document,
)


def test_pdf_ocr_stops_after_later_layout_mode_finds_title() -> None:
    extraction = ExtractionResult()
    attempts = [
        ExtractionResult(text="본문만 인식", methods=["tesseract-psm6"]),
        ExtractionResult(text="거래명세서 공급받는자용", methods=["tesseract-psm3"]),
    ]

    with patch(
        "renamer_document_classifier.service.ocr_pdf",
        side_effect=attempts,
    ) as ocr:
        classification, correspondent = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
            original_name="scan.pdf",
            correspondents=(),
        )

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == ""
    assert ocr.call_args_list == [
        call(
            Path("scan.pdf"),
            ExtractionLimits(),
            page_segmentation_mode=6,
        ),
        call(
            Path("scan.pdf"),
            ExtractionLimits(),
            page_segmentation_mode=3,
        ),
    ]
    assert extraction.text == "본문만 인식\n거래명세서 공급받는자용"


def test_pdf_ocr_tries_high_resolution_grayscale_when_layout_modes_fail() -> None:
    extraction = ExtractionResult()
    attempts = [ExtractionResult(text="판독 불가") for _ in range(5)]

    with patch(
        "renamer_document_classifier.service.ocr_pdf",
        side_effect=attempts,
    ) as ocr:
        classification, correspondent = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
            original_name="scan.pdf",
            correspondents=(),
        )

    assert classification.kind is DocumentKind.UNKNOWN
    assert correspondent == ""
    assert ocr.call_count == 5
    assert ocr.call_args_list[-1] == call(
        Path("scan.pdf"),
        ExtractionLimits(),
        page_segmentation_mode=11,
        dpi=300,
        grayscale=True,
    )


def test_later_ocr_title_is_not_hidden_by_earlier_long_text() -> None:
    extraction = ExtractionResult()
    attempts = [
        ExtractionResult(text="본문" * 2_000),
        ExtractionResult(text="거래명세서"),
    ]

    with patch(
        "renamer_document_classifier.service.ocr_pdf",
        side_effect=attempts,
    ) as ocr:
        classification, correspondent = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
            original_name="scan.pdf",
            correspondents=(),
        )

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == ""
    assert ocr.call_count == 2


def test_pdf_ocr_continues_until_registered_correspondent_is_found() -> None:
    extraction = ExtractionResult()
    attempts = [
        ExtractionResult(text="거래명세서 본문", methods=["tesseract-psm6"]),
        ExtractionResult(
            text="거래명세서 공급받는자 등록거래처A",
            methods=["tesseract-psm3"],
        ),
    ]

    with patch(
        "renamer_document_classifier.service.ocr_pdf",
        side_effect=attempts,
    ) as ocr:
        classification, correspondent = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
            original_name="scan.pdf",
            correspondents=normalize_correspondents(("등록거래처A",)),
        )

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == "등록거래처A"
    assert ocr.call_count == 2


def test_classified_pdf_uses_ocr_when_registered_correspondent_is_missing() -> None:
    correspondents = normalize_correspondents(
        ("써모피서사이언티픽 => ThermoFisher Scientific",)
    )

    with (
        patch(
            "renamer_document_classifier.service.load_correspondents",
            return_value=correspondents,
        ),
        patch(
            "renamer_document_classifier.service.extract_primary_text",
            return_value=ExtractionResult(text="거래명세서"),
        ),
        patch(
            "renamer_document_classifier.service.ocr_pdf",
            return_value=ExtractionResult(text="써모피서사이언티픽솔루션스"),
        ) as ocr,
        patch("renamer_document_classifier.service.write_inspection_log"),
    ):
        result = inspect_document(
            Path("scan.pdf"),
            original_name="SAuthor26072320030.pdf",
        )

    assert result.classification.kind is DocumentKind.TRANSACTION
    assert result.correspondent_name == "ThermoFisher Scientific"
    assert ocr.call_count == 1
