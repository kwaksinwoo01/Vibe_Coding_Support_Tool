from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .classification import ClassificationResult, DocumentKind, classify_document_text
from .config import resolve_person_name
from .extractors import (
    ExtractionLimits,
    ExtractionResult,
    PDF_EXTENSIONS,
    SPREADSHEET_EXTENSIONS,
    extract_primary_text,
    extract_spreadsheet_fallback,
    ocr_pdf,
)
from .logging_utils import append_log


PDF_OCR_ATTEMPTS: tuple[dict[str, int | bool], ...] = (
    {"page_segmentation_mode": 6},
    {"page_segmentation_mode": 3},
    {"page_segmentation_mode": 11},
    {"page_segmentation_mode": 3, "dpi": 300, "grayscale": True},
    {"page_segmentation_mode": 11, "dpi": 300, "grayscale": True},
)


@dataclass(slots=True)
class InspectionResult:
    classification: ClassificationResult
    extraction: ExtractionResult
    person_name: str
    source_path: Path


def _classify(text: str) -> ClassificationResult:
    return classify_document_text(text)


def _extract_pdf_ocr_adaptively(
    path: Path,
    extraction: ExtractionResult,
    limits: ExtractionLimits,
) -> ClassificationResult:
    classification = _classify(extraction.text)

    for attempt_options in PDF_OCR_ATTEMPTS:
        attempt = ocr_pdf(path, limits, **attempt_options)
        extraction.extend(attempt)

        # Classify the latest OCR text on its own first. Otherwise a title found
        # by a later layout mode can land beyond the title scan limit after the
        # earlier OCR text and still be missed.
        attempt_classification = _classify(attempt.text)
        if attempt_classification.kind is not DocumentKind.UNKNOWN:
            return attempt_classification

        classification = _classify(extraction.text)
        if classification.kind is not DocumentKind.UNKNOWN:
            return classification

    return classification


def inspect_document(
    source_path: str | Path,
    *,
    original_name: str | None = None,
    limits: ExtractionLimits | None = None,
) -> InspectionResult:
    path = Path(source_path).expanduser().resolve()
    active_limits = limits or ExtractionLimits()
    extraction = extract_primary_text(path, active_limits)
    classification = _classify(extraction.text)

    extension = path.suffix.casefold()
    if classification.kind is DocumentKind.UNKNOWN:
        if extension in PDF_EXTENSIONS:
            classification = _extract_pdf_ocr_adaptively(
                path,
                extraction,
                active_limits,
            )
        elif extension in SPREADSHEET_EXTENSIONS:
            extraction.extend(extract_spreadsheet_fallback(path, active_limits))
            classification = _classify(extraction.text)

    person_name = resolve_person_name(original_name or path.name)
    result = InspectionResult(
        classification=classification,
        extraction=extraction,
        person_name=person_name,
        source_path=path,
    )

    try:
        write_inspection_log(result)
    except OSError as exc:
        # Classification must still be returned when only the optional log file
        # cannot be written in a restricted GUI-host environment.
        extraction.warnings.append(
            f"log_write_failed:{type(exc).__name__}:{exc}"
        )

    return result


def write_inspection_log(result: InspectionResult) -> None:
    classification = result.classification
    extraction = result.extraction
    append_log(
        [
            f"path={result.source_path}",
            f"extension={result.source_path.suffix.casefold()}",
            f"methods={' | '.join(extraction.methods) or 'none'}",
            f"fallback_used={extraction.fallback_used}",
            f"extracted_text_length={len(extraction.text)}",
            f"quote_title_position={classification.quote_title_position}",
            f"transaction_title_position={classification.transaction_title_position}",
            f"quote_score={classification.quote_score}",
            f"transaction_score={classification.transaction_score}",
            f"matches={' | '.join(classification.matches) or 'none'}",
            f"reason={classification.reason}",
            f"person={result.person_name}",
            f"result={classification.kind.value}",
            f"warnings={' | '.join(extraction.warnings) or 'none'}",
        ]
    )
