from __future__ import annotations

import subprocess
from unittest.mock import patch

from pathlib import Path

from renamer_document_classifier.extractors import (
    ExtractionLimits,
    _ocr_image,
    _run,
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
