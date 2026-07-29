from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
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
from .ocr_scheduler import (
    DocumentSlotLease,
    OcrSchedulerConfig,
    SchedulerSlotLease,
    load_scheduler_config,
)


PDF_OCR_STANDARD_DPI = 300
PDF_OCR_PARALLEL_PSMS = (3, 6, 11)
PDF_OCR_HIGH_RESOLUTION_DPI = 400
PDF_OCR_HIGH_RESOLUTION_PSMS = (3, 11)


@dataclass(slots=True)
class InspectionResult:
    classification: ClassificationResult
    extraction: ExtractionResult
    person_name: str
    correspondent_name: str
    source_path: Path
    scheduler: OcrSchedulerConfig | None = None


@dataclass(frozen=True, slots=True)
class OcrAttempt:
    label: str
    extraction: ExtractionResult
    priority: int


def _classify(text: str) -> ClassificationResult:
    return classify_document_text(text)


def _classification_weight(classification: ClassificationResult) -> int:
    if classification.kind is DocumentKind.UNKNOWN:
        return 0
    title_match = "title" in classification.reason
    score = max(classification.quote_score, classification.transaction_score)
    return (400 if title_match else 200) + score


def _arbitrate_ocr_attempts(
    attempts: tuple[OcrAttempt, ...],
    extraction: ExtractionResult,
    classification: ClassificationResult,
    *,
    original_name: str,
    correspondents: tuple[CorrespondentRule, ...],
) -> tuple[ClassificationResult, str]:
    candidates: list[tuple[int, ClassificationResult]] = [(0, classification)]
    for attempt in sorted(attempts, key=lambda item: item.priority):
        extraction.extend(attempt.extraction)
        extraction.methods.append(f"ocr-attempt:{attempt.label}")
        candidates.append((attempt.priority, _classify(attempt.extraction.text)))
    if attempts:
        extraction.methods.append("ocr-arbiter")

    # Embedded text containing a document title is the most authoritative
    # signal. Otherwise let independent OCR engines vote, with title matches
    # weighted above support-only classifications. Completion order never
    # affects the result because priority is fixed by engine/mode.
    if (
        classification.kind is not DocumentKind.UNKNOWN
        and "title" in classification.reason
    ):
        selected = classification
    else:
        votes = {DocumentKind.QUOTE: 0, DocumentKind.TRANSACTION: 0}
        for _, candidate in candidates:
            if candidate.kind in votes:
                votes[candidate.kind] += _classification_weight(candidate)

        winning_kind = max(
            votes,
            key=lambda kind: (votes[kind], kind is DocumentKind.TRANSACTION),
        )
        known = [
            (priority, candidate)
            for priority, candidate in candidates
            if candidate.kind is winning_kind
        ]
        if known and votes[winning_kind] > 0:
            _, selected = max(
                known,
                key=lambda item: (
                    _classification_weight(item[1]),
                    max(item[1].quote_score, item[1].transaction_score),
                    -item[0],
                ),
            )
        else:
            selected = _classify(extraction.text)

    correspondent = resolve_correspondent(
        (original_name, extraction.text),
        correspondents,
    )
    return selected, correspondent


def _run_standard_ocr_attempts(
    pages: tuple[Path, ...],
    limits: ExtractionLimits,
    scheduler: OcrSchedulerConfig,
) -> tuple[OcrAttempt, ...]:
    active = scheduler.normalized()
    attempt_budget = active.max_attempts_per_document
    modes = PDF_OCR_PARALLEL_PSMS[: min(3, attempt_budget)]
    include_paddle = active.gpu_workers > 0 and attempt_budget > len(modes)
    max_engine_workers = min(
        2 if include_paddle else 1,
        active.max_parallel_attempts(
            dpi=PDF_OCR_STANDARD_DPI,
            page_count=len(pages),
        ),
    )

    def tesseract_group() -> dict[int, ExtractionResult]:
        return ocr_images_with_tesseract(
            pages,
            limits,
            modes,
            cpu_slot_factory=lambda: SchedulerSlotLease(
                "cpu",
                active.cpu_workers,
                limits.timeout_seconds,
            ),
        )

    def paddle_group() -> ExtractionResult:
        with SchedulerSlotLease(
            "gpu",
            active.gpu_workers,
            limits.timeout_seconds,
        ), SchedulerSlotLease(
            "cpu",
            active.cpu_workers,
            limits.timeout_seconds,
        ):
            return ocr_images_with_paddleocr(
                pages,
                limits,
                batch_size=active.batch_size,
                cpu_threads=1,
            )

    if include_paddle and max_engine_workers > 1:
        with ThreadPoolExecutor(
            max_workers=max_engine_workers,
            thread_name_prefix="ocr-engine",
        ) as executor:
            tesseract_future = executor.submit(tesseract_group)
            paddle_future = executor.submit(paddle_group)
            tesseract_results = tesseract_future.result()
            paddle_result = paddle_future.result()
    else:
        tesseract_results = tesseract_group()
        paddle_result = paddle_group() if include_paddle else None

    attempts = [
        OcrAttempt(
            label=f"tesseract-psm{mode}-dpi300",
            extraction=tesseract_results[mode],
            priority=index,
        )
        for index, mode in enumerate(modes)
    ]
    if paddle_result is not None:
        attempts.append(
            OcrAttempt(
                label="paddleocr-dpi300",
                extraction=paddle_result,
                priority=len(attempts),
            )
        )
    return tuple(attempts)


def _extract_pdf_ocr_adaptively(
    path: Path,
    extraction: ExtractionResult,
    limits: ExtractionLimits,
    *,
    original_name: str,
    correspondents: tuple[CorrespondentRule, ...],
    scheduler: OcrSchedulerConfig | None = None,
) -> tuple[ClassificationResult, str]:
    active_scheduler = (scheduler or load_scheduler_config()).normalized()
    active_limits = replace(
        limits,
        ocr_dpi=PDF_OCR_STANDARD_DPI,
        ocr_workers=active_scheduler.cpu_workers,
    )
    classification = _classify(extraction.text)
    correspondent = resolve_correspondent(
        (original_name, extraction.text),
        correspondents,
    )

    with tempfile.TemporaryDirectory(prefix="renamer_pdf_ocr_") as temp_dir:
        workspace = Path(temp_dir)
        rendered = render_pdf_pages(
            path,
            active_limits,
            workspace / "dpi300-gray",
            dpi=PDF_OCR_STANDARD_DPI,
            grayscale=True,
        )
        extraction.extend(rendered.extraction)

        standard_attempts = _run_standard_ocr_attempts(
            rendered.pages,
            active_limits,
            active_scheduler,
        )
        classification, correspondent = _arbitrate_ocr_attempts(
            standard_attempts,
            extraction,
            classification,
            original_name=original_name,
            correspondents=correspondents,
        )
        if classification.kind is not DocumentKind.UNKNOWN:
            return classification, correspondent

        attempts_used = len(standard_attempts)
        remaining_attempts = max(
            0, active_scheduler.max_attempts_per_document - attempts_used
        )
        high_modes = PDF_OCR_HIGH_RESOLUTION_PSMS[:remaining_attempts]
        if not high_modes:
            extraction.warnings.append("ocr_attempt_budget_exhausted")
            return classification, correspondent

        high_resolution = render_pdf_pages(
            path,
            active_limits,
            workspace / "dpi400-gray",
            dpi=PDF_OCR_HIGH_RESOLUTION_DPI,
            grayscale=True,
        )
        extraction.extend(high_resolution.extraction)
        high_resolution_attempts = ocr_images_with_tesseract(
            high_resolution.pages,
            active_limits,
            high_modes,
            cpu_slot_factory=lambda: SchedulerSlotLease(
                "cpu",
                active_scheduler.cpu_workers,
                active_limits.timeout_seconds,
            ),
        )
        high_attempts = tuple(
            OcrAttempt(
                label=f"tesseract-psm{mode}-dpi400",
                extraction=high_resolution_attempts[mode],
                priority=attempts_used + index,
            )
            for index, mode in enumerate(high_modes)
        )
        classification, correspondent = _arbitrate_ocr_attempts(
            high_attempts,
            extraction,
            classification,
            original_name=original_name,
            correspondents=correspondents,
        )

    return classification, correspondent


def inspect_document(
    source_path: str | Path,
    *,
    original_name: str | None = None,
    limits: ExtractionLimits | None = None,
    scheduler: OcrSchedulerConfig | None = None,
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
    used_scheduler: OcrSchedulerConfig | None = None

    extension = path.suffix.casefold()
    needs_pdf_ocr = (
        extension in PDF_EXTENSIONS
        and (
            classification.kind is DocumentKind.UNKNOWN
            or (correspondents and not correspondent_name)
        )
    )
    if needs_pdf_ocr:
        active_scheduler = (scheduler or load_scheduler_config()).normalized()
        used_scheduler = active_scheduler
        with DocumentSlotLease(
            active_scheduler.max_documents_in_flight,
            active_limits.timeout_seconds,
        ):
            classification, correspondent_name = _extract_pdf_ocr_adaptively(
                path,
                extraction,
                active_limits,
                original_name=active_original_name,
                correspondents=correspondents,
                scheduler=active_scheduler,
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
        scheduler=used_scheduler,
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
    scheduler = result.scheduler
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
            f"ocr.scheduler.cpu_workers={scheduler.cpu_workers if scheduler else 'not_used'}",
            f"ocr.scheduler.gpu_workers={scheduler.gpu_workers if scheduler else 'not_used'}",
            "ocr.scheduler.max_documents_in_flight="
            f"{scheduler.max_documents_in_flight if scheduler else 'not_used'}",
            "ocr.scheduler.max_attempts_per_document="
            f"{scheduler.max_attempts_per_document if scheduler else 'not_used'}",
            "ocr.scheduler.memory_budget_mb="
            f"{scheduler.memory_budget_mb if scheduler else 'not_used'}",
            f"ocr.scheduler.batch_size={scheduler.batch_size if scheduler else 'not_used'}",
            f"warnings={' | '.join(extraction.warnings) or 'none'}",
        ]
    )
