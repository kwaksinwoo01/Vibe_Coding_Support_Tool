from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, call, patch

from renamer_document_classifier.classification import DocumentKind
from renamer_document_classifier.correspondent_config import normalize_correspondents
from renamer_document_classifier.extractors import (
    ExtractionLimits,
    ExtractionResult,
    RenderedPdfPages,
)
from renamer_document_classifier.service import (
    _extract_pdf_ocr_adaptively,
    inspect_document,
)


PAGES = (Path("page-1.png"),)


def rendered(method: str = "pdftoppm-dpi300") -> RenderedPdfPages:
    return RenderedPdfPages(
        PAGES,
        ExtractionResult(methods=["pdftoppm", method], fallback_used=True),
    )


def tesseract_attempts(*texts: str) -> dict[int, ExtractionResult]:
    modes = (3,) if len(texts) == 1 else (6, 11)
    return {
        mode: ExtractionResult(text=text, methods=[f"tesseract-psm{mode}"])
        for mode, text in zip(modes, texts, strict=True)
    }


def run_adaptive(
    extraction: ExtractionResult | None = None,
    *,
    correspondents: tuple = (),
) -> tuple:
    return _extract_pdf_ocr_adaptively(
        Path("scan.pdf"),
        extraction or ExtractionResult(),
        ExtractionLimits(),
        original_name="scan.pdf",
        correspondents=correspondents,
    )


def test_pdf_ocr_stops_after_primary_psm3_finds_title() -> None:
    extraction = ExtractionResult()
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ) as render,
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            return_value=tesseract_attempts("거래명세서 공급받는자용"),
        ) as tesseract,
        patch("renamer_document_classifier.service.ocr_images_with_paddleocr") as paddle,
    ):
        classification, correspondent = run_adaptive(extraction)

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == ""
    render.assert_called_once_with(Path("scan.pdf"), ExtractionLimits(), ANY)
    tesseract.assert_called_once_with(PAGES, ExtractionLimits(), (3,))
    paddle.assert_not_called()
    assert extraction.methods == ["pdftoppm", "pdftoppm-dpi300", "tesseract-psm3"]


def test_pdf_ocr_reuses_render_and_runs_psm6_11_as_one_parallel_group() -> None:
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ) as render,
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            side_effect=[
                tesseract_attempts("본문만 인식"),
                tesseract_attempts("여전히 본문", "거래명세서 공급받는자용"),
            ],
        ) as tesseract,
        patch("renamer_document_classifier.service.ocr_images_with_paddleocr") as paddle,
    ):
        classification, correspondent = run_adaptive()

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == ""
    assert render.call_count == 1
    assert tesseract.call_args_list == [
        call(PAGES, ExtractionLimits(), (3,)),
        call(PAGES, ExtractionLimits(), (6, 11)),
    ]
    paddle.assert_not_called()


def test_pdf_ocr_uses_paddleocr_only_after_all_300_dpi_tesseract_modes_fail() -> None:
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ) as render,
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            side_effect=[
                tesseract_attempts("판독 불가"),
                tesseract_attempts("판독 불가", "판독 불가"),
            ],
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            return_value=ExtractionResult(
                text="거래명세서",
                methods=["paddleocr", "paddleocr-onnx"],
            ),
        ) as paddle,
    ):
        classification, _ = run_adaptive()

    assert classification.kind is DocumentKind.TRANSACTION
    paddle.assert_called_once_with(PAGES, ExtractionLimits())
    assert render.call_count == 1


def test_pdf_ocr_uses_400_dpi_grayscale_after_paddleocr_also_fails() -> None:
    high_pages = (Path("high-page-1.png"),)
    high_render = RenderedPdfPages(
        high_pages,
        ExtractionResult(methods=["pdftoppm-dpi400-gray"]),
    )
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            side_effect=[rendered(), high_render],
        ) as render,
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            side_effect=[
                tesseract_attempts("판독 불가"),
                tesseract_attempts("판독 불가", "판독 불가"),
                {
                    3: ExtractionResult(text="판독 불가"),
                    11: ExtractionResult(text="거래명세서"),
                },
            ],
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            return_value=ExtractionResult(text="판독 불가"),
        ),
    ):
        classification, _ = run_adaptive()

    assert classification.kind is DocumentKind.TRANSACTION
    assert render.call_args_list[1] == call(
        Path("scan.pdf"),
        ExtractionLimits(),
        ANY,
        dpi=400,
        grayscale=True,
    )


def test_later_ocr_title_is_not_hidden_by_earlier_long_text() -> None:
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            side_effect=[
                tesseract_attempts("본문" * 2_000),
                tesseract_attempts("거래명세서", "판독 불가"),
            ],
        ),
        patch("renamer_document_classifier.service.ocr_images_with_paddleocr"),
    ):
        classification, _ = run_adaptive()

    assert classification.kind is DocumentKind.TRANSACTION


def test_pdf_ocr_continues_until_registered_correspondent_is_found() -> None:
    correspondents = normalize_correspondents(("등록거래처A",))
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            side_effect=[
                tesseract_attempts("거래명세서 본문"),
                tesseract_attempts(
                    "거래명세서 공급받는자 등록거래처A",
                    "거래명세서 본문",
                ),
            ],
        ) as tesseract,
        patch("renamer_document_classifier.service.ocr_images_with_paddleocr") as paddle,
    ):
        classification, correspondent = run_adaptive(correspondents=correspondents)

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == "등록거래처A"
    assert tesseract.call_count == 2
    paddle.assert_not_called()


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
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            return_value=tesseract_attempts("써모피서사이언티픽솔루션스"),
        ) as tesseract,
        patch("renamer_document_classifier.service.ocr_images_with_paddleocr") as paddle,
        patch("renamer_document_classifier.service.write_inspection_log"),
    ):
        result = inspect_document(
            Path("scan.pdf"),
            original_name="SAuthor26072320030.pdf",
        )

    assert result.classification.kind is DocumentKind.TRANSACTION
    assert result.correspondent_name == "ThermoFisher Scientific"
    tesseract.assert_called_once_with(PAGES, ExtractionLimits(), (3,))
    paddle.assert_not_called()
