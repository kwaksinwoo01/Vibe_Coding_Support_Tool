from __future__ import annotations

from pathlib import Path
from unittest.mock import call, patch

from renamer_document_classifier.classification import DocumentKind
from renamer_document_classifier.extractors import ExtractionLimits, ExtractionResult
from renamer_document_classifier.service import _extract_pdf_ocr_adaptively


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
        classification = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
        )

    assert classification.kind is DocumentKind.TRANSACTION
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
        classification = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
        )

    assert classification.kind is DocumentKind.UNKNOWN
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
        classification = _extract_pdf_ocr_adaptively(
            Path("scan.pdf"),
            extraction,
            ExtractionLimits(),
        )

    assert classification.kind is DocumentKind.TRANSACTION
    assert ocr.call_count == 2
