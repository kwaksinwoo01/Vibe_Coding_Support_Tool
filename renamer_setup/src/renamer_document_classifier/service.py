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


@dataclass(slots=True)
class InspectionResult:
    classification: ClassificationResult
    extraction: ExtractionResult
    person_name: str
    source_path: Path


def _classify(text: str) -> ClassificationResult:
    return classify_document_text(text)


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
            extraction.extend(ocr_pdf(path, active_limits))
            classification = _classify(extraction.text)
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
    write_inspection_log(result)
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
