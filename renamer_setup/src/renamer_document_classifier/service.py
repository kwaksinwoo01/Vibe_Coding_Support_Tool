from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

from .classification import ClassificationResult, DocumentKind, classify_document_text
from .correspondent_config import (
    CorrespondentRule,
    load_correspondents,
    resolve_correspondent,
)
from .extractors import (
    ExtractionLimits,
    ExtractionResult,
    PDF_EXTENSIONS,
    SPREADSHEET_EXTENSIONS,
    extract_primary_text,
    extract_spreadsheet_fallback,
    ocr_images_with_paddleocr,
    ocr_images_with_tesseract,
    render_pdf_pages,
)
from .logging_utils import append_log
from .names_config import resolve_person_name


PDF_OCR_PRIMARY_PSM = 3
PDF_OCR_PARALLEL_PSMS = (6, 11)
PDF_OCR_HIGH_RESOLUTION_PSMS = (3, 11)


@dataclass(slots=True)
class InspectionResult:
    classification: ClassificationResult
    extraction: ExtractionResult
    person_name: str
    correspondent_name: str
    source_path: Path


def _classify(text: str) -> ClassificationResult:
    return classify_document_text(text)


def _apply_ocr_attempt(
    attempt: ExtractionResult,
    extraction: ExtractionResult,
    classification: ClassificationResult,
    *,
    original_name: str,
    correspondents: tuple[CorrespondentRule, ...],
) -> tuple[ClassificationResult, str]:
    extraction.extend(attempt)

    # Classify the latest OCR text on its own first. Otherwise a title found
    # by a later engine can land beyond the title scan limit after earlier OCR
    # text and still be missed.
    attempt_classification = _classify(attempt.text)
    if attempt_classification.kind is not DocumentKind.UNKNOWN:
        classification = attempt_classification
    else:
        classification = _classify(extraction.text)

    correspondent = resolve_correspondent(
        (original_name, extraction.text),
        correspondents,
    )
    return classification, correspondent


def _extract_pdf_ocr_adaptively(
    path: Path,
    extraction: ExtractionResult,
    limits: ExtractionLimits,
    *,
    original_name: str,
    correspondents: tuple[CorrespondentRule, ...],
) -> tuple[ClassificationResult, str]:
    classification = _classify(extraction.text)
    correspondent = resolve_correspondent(
        (original_name, extraction.text),
        correspondents,
    )

    with tempfile.TemporaryDirectory(prefix="renamer_pdf_ocr_") as temp_dir:
        workspace = Path(temp_dir)
        rendered = render_pdf_pages(
            path,
            limits,
            workspace / "dpi300",
        )
        extraction.extend(rendered.extraction)

        primary_attempt = ocr_images_with_tesseract(
            rendered.pages,
            limits,
            (PDF_OCR_PRIMARY_PSM,),
        )[PDF_OCR_PRIMARY_PSM]
        classification, correspondent = _apply_ocr_attempt(
            primary_attempt,
            extraction,
            classification,
            original_name=original_name,
            correspondents=correspondents,
        )
        if classification.kind is not DocumentKind.UNKNOWN and (
            correspondent or not correspondents
        ):
            return classification, correspondent

        parallel_attempts = ocr_images_with_tesseract(
            rendered.pages,
            limits,
            PDF_OCR_PARALLEL_PSMS,
        )
        for mode in PDF_OCR_PARALLEL_PSMS:
            classification, correspondent = _apply_ocr_attempt(
                parallel_attempts[mode],
                extraction,
                classification,
                original_name=original_name,
                correspondents=correspondents,
            )
            if classification.kind is not DocumentKind.UNKNOWN and (
                correspondent or not correspondents
            ):
                return classification, correspondent

        # Preserve the established correspondent search budget: once all three
        # 300 DPI Tesseract layouts have classified the document, do not start
        # heavier engines only to search for an unregistered correspondent.
        if classification.kind is not DocumentKind.UNKNOWN:
            return classification, correspondent

        paddle_attempt = ocr_images_with_paddleocr(rendered.pages, limits)
        classification, correspondent = _apply_ocr_attempt(
            paddle_attempt,
            extraction,
            classification,
            original_name=original_name,
            correspondents=correspondents,
        )
        if classification.kind is not DocumentKind.UNKNOWN:
            return classification, correspondent

        high_resolution = render_pdf_pages(
            path,
            limits,
            workspace / "dpi400-gray",
            dpi=400,
            grayscale=True,
        )
        extraction.extend(high_resolution.extraction)
        high_resolution_attempts = ocr_images_with_tesseract(
            high_resolution.pages,
            limits,
            PDF_OCR_HIGH_RESOLUTION_PSMS,
        )
        for mode in PDF_OCR_HIGH_RESOLUTION_PSMS:
            classification, correspondent = _apply_ocr_attempt(
                high_resolution_attempts[mode],
                extraction,
                classification,
                original_name=original_name,
                correspondents=correspondents,
            )
            if classification.kind is not DocumentKind.UNKNOWN:
                return classification, correspondent

    return classification, correspondent


def inspect_document(
    source_path: str | Path,
    *,
    original_name: str | None = None,
    limits: ExtractionLimits | None = None,
) -> InspectionResult:
    path = Path(source_path).expanduser().resolve()
    active_limits = limits or ExtractionLimits()
    active_original_name = original_name or path.name
    correspondents = load_correspondents()
    extraction = extract_primary_text(path, active_limits)
    classification = _classify(extraction.text)
    correspondent_name = resolve_correspondent(
        (active_original_name, extraction.text),
        correspondents,
    )

    extension = path.suffix.casefold()
    needs_pdf_ocr = (
        extension in PDF_EXTENSIONS
        and (
            classification.kind is DocumentKind.UNKNOWN
            or (correspondents and not correspondent_name)
        )
    )
    if needs_pdf_ocr:
        classification, correspondent_name = _extract_pdf_ocr_adaptively(
            path,
            extraction,
            active_limits,
            original_name=active_original_name,
            correspondents=correspondents,
        )
    elif classification.kind is DocumentKind.UNKNOWN:
        if extension in SPREADSHEET_EXTENSIONS:
            extraction.extend(extract_spreadsheet_fallback(path, active_limits))
            classification = _classify(extraction.text)
            correspondent_name = resolve_correspondent(
                (active_original_name, extraction.text),
                correspondents,
            )

    person_name = resolve_person_name(active_original_name)
    result = InspectionResult(
        classification=classification,
        extraction=extraction,
        person_name=person_name,
        correspondent_name=correspondent_name,
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
            f"correspondent={result.correspondent_name or 'none'}",
            f"result={classification.kind.value}",
            f"warnings={' | '.join(extraction.warnings) or 'none'}",
        ]
    )
