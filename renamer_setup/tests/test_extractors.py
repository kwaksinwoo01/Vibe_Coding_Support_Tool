from __future__ import annotations

import subprocess
from unittest.mock import patch

from pathlib import Path

from renamer_document_classifier.extractors import (
    ExtractionLimits,
    _ocr_image,
    _run,
    ocr_images_with_paddleocr,
    ocr_images_with_tesseract,
)


def test_run_uses_devnull_for_stdin() -> None:
    completed = subprocess.CompletedProcess(["tool.exe"], 0, "ok", "")

    with patch(
        "renamer_document_classifier.extractors.subprocess.run",
        return_value=completed,
    ) as run:
        result = _run(["tool.exe"], timeout_seconds=10)

    assert result is completed
    assert run.call_args.kwargs["stdin"] is subprocess.DEVNULL


def test_ocr_image_uses_requested_page_segmentation_mode() -> None:
    completed = subprocess.CompletedProcess(["tesseract.exe"], 0, "text", "")

    with (
        patch(
            "renamer_document_classifier.extractors.find_tesseract",
            return_value=Path("tesseract.exe"),
        ),
        patch(
            "renamer_document_classifier.extractors._run",
            return_value=completed,
        ) as run,
    ):
        result = _ocr_image(
            Path("page.png"),
            ExtractionLimits(),
            page_segmentation_mode=11,
        )

    assert run.call_args.args[0][-1] == "11"
    assert result.text == "text"
    assert result.methods == ["tesseract", "tesseract-psm11"]


def test_tesseract_parallel_group_preserves_mode_and_page_order() -> None:
    def fake_ocr(
        image_path,
        limits,
        *,
        page_segmentation_mode,
        tesseract_path,
        environment,
    ):
        from renamer_document_classifier.extractors import ExtractionResult

        assert int(environment["OMP_THREAD_LIMIT"]) >= 1
        return ExtractionResult(text=f"{page_segmentation_mode}:{image_path.name}")

    pages = (Path("page-1.png"), Path("page-2.png"))
    with (
        patch(
            "renamer_document_classifier.extractors.find_tesseract",
            return_value=Path("tesseract.exe"),
        ),
        patch(
            "renamer_document_classifier.extractors._ocr_image",
            side_effect=fake_ocr,
        ) as ocr,
    ):
        results = ocr_images_with_tesseract(
            pages,
            ExtractionLimits(ocr_workers=4),
            (6, 11),
        )

    assert ocr.call_count == 4
    assert results[6].text == "6:page-1.png\n6:page-2.png"
    assert results[11].text == "11:page-1.png\n11:page-2.png"
    assert results[6].methods == ["tesseract", "tesseract-psm6"]
    assert results[11].methods == ["tesseract", "tesseract-psm11"]


def test_paddleocr_reads_file_result_without_stdout(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(["python.exe"], 0, "ignored", "")

    def run(arguments, *, timeout_seconds):
        output_path = Path(arguments[arguments.index("--output") + 1])
        output_path.write_text(
            '{"status":"ok","text":"거래명세서\\n아이셀"}',
            encoding="utf-8-sig",
        )
        return completed

    with (
        patch(
            "renamer_document_classifier.extractors.find_paddleocr_python",
            return_value=Path("python.exe"),
        ),
        patch(
            "renamer_document_classifier.extractors.find_paddleocr_runner",
            return_value=Path("paddleocr_runner.py"),
        ),
        patch("renamer_document_classifier.extractors._run", side_effect=run),
    ):
        result = ocr_images_with_paddleocr(
            (tmp_path / "page-1.png",),
            ExtractionLimits(),
        )

    assert result.text == "거래명세서\n아이셀"
    assert result.methods == ["paddleocr", "paddleocr-onnx"]


def test_paddleocr_missing_is_a_safe_optional_fallback() -> None:
    with patch(
        "renamer_document_classifier.extractors.find_paddleocr_python",
        return_value=None,
    ):
        result = ocr_images_with_paddleocr(
            (Path("page-1.png"),),
            ExtractionLimits(),
        )

    assert result.text == ""
    assert result.warnings == ["paddleocr_missing"]


def test_paddleocr_respects_page_batch_size(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(["python.exe"], 0, "", "")
    calls: list[tuple[str, ...]] = []

    def run(arguments, *, timeout_seconds):
        output_path = Path(arguments[arguments.index("--output") + 1])
        image_arguments = tuple(
            arguments[arguments.index("--cpu-threads") + 2 :]
        )
        calls.append(image_arguments)
        output_path.write_text(
            '{"status":"ok","text":"batch text"}',
            encoding="utf-8-sig",
        )
        return completed

    pages = tuple(tmp_path / f"page-{index}.png" for index in range(5))
    with (
        patch(
            "renamer_document_classifier.extractors.find_paddleocr_python",
            return_value=Path("python.exe"),
        ),
        patch(
            "renamer_document_classifier.extractors.find_paddleocr_runner",
            return_value=Path("paddleocr_runner.py"),
        ),
        patch("renamer_document_classifier.extractors._run", side_effect=run),
    ):
        result = ocr_images_with_paddleocr(
            pages,
            ExtractionLimits(),
            batch_size=2,
        )

    assert [len(batch) for batch in calls] == [2, 2, 1]
    assert result.text == "batch text\nbatch text\nbatch text"
