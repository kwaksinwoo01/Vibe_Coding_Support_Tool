from __future__ import annotations

from pathlib import Path
from threading import Barrier, Lock
from unittest.mock import ANY, call, patch

from renamer_document_classifier.classification import (
    DocumentKind,
    classify_document_text,
)
from renamer_document_classifier.correspondent_config import normalize_correspondents
from renamer_document_classifier.extractors import (
    ExtractionLimits,
    ExtractionResult,
    RenderedPdfPages,
)
from renamer_document_classifier.ocr_scheduler import OcrSchedulerConfig
from renamer_document_classifier.service import (
    _extract_pdf_ocr_adaptively,
    inspect_document,
)


PAGES = (Path("page-1.png"),)
SCHEDULER = OcrSchedulerConfig(
    cpu_workers=4,
    gpu_workers=1,
    max_documents_in_flight=1,
    max_attempts_per_document=6,
    memory_budget_mb=2048,
    batch_size=2,
)


def rendered(method: str = "pdftoppm-dpi300-gray") -> RenderedPdfPages:
    return RenderedPdfPages(
        PAGES,
        ExtractionResult(methods=["pdftoppm", method], fallback_used=True),
    )


def tesseract_attempts(
    psm3: str,
    psm6: str,
    psm11: str,
) -> dict[int, ExtractionResult]:
    return {
        mode: ExtractionResult(
            text=text,
            methods=["tesseract", f"tesseract-psm{mode}"],
        )
        for mode, text in zip((3, 6, 11), (psm3, psm6, psm11), strict=True)
    }


def run_adaptive(
    extraction: ExtractionResult | None = None,
    *,
    correspondents: tuple = (),
    scheduler: OcrSchedulerConfig = SCHEDULER,
) -> tuple:
    return _extract_pdf_ocr_adaptively(
        Path("scan.pdf"),
        extraction or ExtractionResult(),
        ExtractionLimits(),
        original_name="scan.pdf",
        correspondents=correspondents,
        scheduler=scheduler,
    )


def test_pdf_ocr_renders_300_gray_once_and_runs_all_standard_engines() -> None:
    extraction = ExtractionResult()
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ) as render,
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            return_value=tesseract_attempts(
                "거래명세서 공급받는자용",
                "본문",
                "본문",
            ),
        ) as tesseract,
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            return_value=ExtractionResult(text="본문", methods=["paddleocr"]),
        ) as paddle,
    ):
        classification, correspondent = run_adaptive(extraction)

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == ""
    render.assert_called_once_with(
        Path("scan.pdf"),
        ANY,
        ANY,
        dpi=300,
        grayscale=True,
    )
    tesseract.assert_called_once_with(
        PAGES,
        ANY,
        (3, 6, 11),
        cpu_slot_factory=ANY,
    )
    paddle.assert_called_once_with(PAGES, ANY, batch_size=2, cpu_threads=1)
    assert "ocr-arbiter" in extraction.methods


def test_tesseract_group_and_paddle_start_concurrently() -> None:
    barrier = Barrier(2, timeout=2)
    seen: list[str] = []
    seen_lock = Lock()

    def tesseract(*args, **kwargs):
        with seen_lock:
            seen.append("tesseract")
        barrier.wait()
        return tesseract_attempts("본문", "거래명세서", "본문")

    def paddle(*args, **kwargs):
        with seen_lock:
            seen.append("paddle")
        barrier.wait()
        return ExtractionResult(text="본문")

    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            side_effect=tesseract,
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            side_effect=paddle,
        ),
    ):
        classification, _ = run_adaptive()

    assert classification.kind is DocumentKind.TRANSACTION
    assert sorted(seen) == ["paddle", "tesseract"]


def test_arbiter_uses_independent_engine_votes_deterministically() -> None:
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            return_value=tesseract_attempts(
                "판독 불가",
                "거래명세서",
                "거래명세서",
            ),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            return_value=ExtractionResult(text="견적서"),
        ),
    ):
        classification, _ = run_adaptive()

    assert classification.kind is DocumentKind.TRANSACTION
    assert classification.reason == "transaction_title"


def test_pdf_ocr_uses_400_dpi_only_after_standard_arbiter_is_unknown() -> None:
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
                tesseract_attempts("판독 불가", "판독 불가", "판독 불가"),
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
        ANY,
        ANY,
        dpi=400,
        grayscale=True,
    )


def test_attempt_budget_can_disable_400_dpi_fallback() -> None:
    scheduler = OcrSchedulerConfig(
        cpu_workers=4,
        gpu_workers=1,
        max_documents_in_flight=1,
        max_attempts_per_document=4,
        memory_budget_mb=2048,
        batch_size=1,
    )
    extraction = ExtractionResult()
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ) as render,
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            return_value=tesseract_attempts("본문", "본문", "본문"),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            return_value=ExtractionResult(text="본문"),
        ),
    ):
        classification, _ = run_adaptive(extraction, scheduler=scheduler)

    assert classification.kind is DocumentKind.UNKNOWN
    assert render.call_count == 1
    assert "ocr_attempt_budget_exhausted" in extraction.warnings


def test_all_standard_results_are_available_for_correspondent_resolution() -> None:
    correspondents = normalize_correspondents(("등록거래처A",))
    with (
        patch(
            "renamer_document_classifier.service.render_pdf_pages",
            return_value=rendered(),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_tesseract",
            return_value=tesseract_attempts(
                "거래명세서",
                "등록거래처A",
                "본문",
            ),
        ),
        patch(
            "renamer_document_classifier.service.ocr_images_with_paddleocr",
            return_value=ExtractionResult(text="본문"),
        ),
    ):
        classification, correspondent = run_adaptive(
            correspondents=correspondents
        )

    assert classification.kind is DocumentKind.TRANSACTION
    assert correspondent == "등록거래처A"


def test_inspect_uses_document_admission_slot_for_pdf_ocr() -> None:
    correspondents = normalize_correspondents(
        ("써모피서사이언티픽 => ThermoFisher Scientific",)
    )
    tesseract_result = classify_document_text("거래명세서")
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
            "renamer_document_classifier.service.DocumentSlotLease"
        ) as lease,
        patch(
            "renamer_document_classifier.service._extract_pdf_ocr_adaptively",
            return_value=(
                tesseract_result,
                "ThermoFisher Scientific",
            ),
        ) as adaptive,
        patch("renamer_document_classifier.service.write_inspection_log"),
    ):
        result = inspect_document(
            Path("scan.pdf"),
            original_name="SAuthor26072320030.pdf",
            scheduler=SCHEDULER,
        )

    assert result.classification is tesseract_result
    assert result.correspondent_name == "ThermoFisher Scientific"
    lease.assert_called_once_with(1, 120)
    adaptive.assert_called_once()
