from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree

from python_calamine import CalamineWorkbook

from .runtime_paths import installation_root, tools_directory


SPREADSHEET_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".xlsb", ".ods"}
PDF_EXTENSIONS = {".pdf"}


@dataclass(slots=True)
class ExtractionResult:
    text: str = ""
    methods: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fallback_used: bool = False

    def extend(self, other: "ExtractionResult") -> None:
        if other.text:
            if self.text:
                self.text += "\n"
            self.text += other.text
        self.methods.extend(other.methods)
        self.warnings.extend(other.warnings)
        self.fallback_used = self.fallback_used or other.fallback_used


@dataclass(slots=True, frozen=True)
class ExtractionLimits:
    max_pages: int = 2
    max_sheets: int = 3
    max_rows: int = 200
    max_columns: int = 50
    max_characters: int = 50_000
    ocr_dpi: int = 220
    timeout_seconds: int = 120


def _candidate_paths(relative_paths: tuple[str, ...], executable_names: tuple[str, ...]) -> list[Path]:
    root = tools_directory()
    candidates = [root / relative for relative in relative_paths]
    for executable_name in executable_names:
        found = shutil.which(executable_name)
        if found:
            candidates.append(Path(found))
    return candidates


def find_pdftotext() -> Path | None:
    candidates = _candidate_paths(
        (
            "poppler/Library/bin/pdftotext.exe",
            "poppler/bin/pdftotext.exe",
            "pdftotext.exe",
        ),
        ("pdftotext.exe", "pdftotext"),
    )
    return next((path for path in candidates if path.is_file()), None)


def find_pdftoppm() -> Path | None:
    candidates = _candidate_paths(
        (
            "poppler/Library/bin/pdftoppm.exe",
            "poppler/bin/pdftoppm.exe",
            "pdftoppm.exe",
        ),
        ("pdftoppm.exe", "pdftoppm"),
    )
    return next((path for path in candidates if path.is_file()), None)


def find_tesseract() -> Path | None:
    candidates = _candidate_paths(
        (
            "tesseract/tesseract.exe",
            "Tesseract-OCR/tesseract.exe",
        ),
        ("tesseract.exe", "tesseract"),
    )
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(Path(program_files) / "Tesseract-OCR" / "tesseract.exe")
    return next((path for path in candidates if path.is_file()), None)


def find_libreoffice() -> Path | None:
    candidates = _candidate_paths(
        (
            "libreoffice/program/soffice.exe",
            "LibreOffice/program/soffice.exe",
        ),
        ("soffice.exe", "libreoffice.exe", "soffice"),
    )
    for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(environment_name)
        if base:
            candidates.append(Path(base) / "LibreOffice" / "program" / "soffice.exe")
    return next((path for path in candidates if path.is_file()), None)


def _run(
    arguments: list[str],
    *,
    timeout_seconds: int,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        arguments,
        cwd=str(cwd) if cwd else None,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
        creationflags=creation_flags,
    )


def _truncate(text: str, max_characters: int) -> str:
    return text[:max_characters]


def extract_pdf_text(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    result = ExtractionResult()
    pdftotext = find_pdftotext()

    if pdftotext:
        with tempfile.TemporaryDirectory(prefix="renamer_pdf_text_") as temp_dir:
            output_path = Path(temp_dir) / "output.txt"
            process = _run(
                [
                    str(pdftotext),
                    "-f",
                    "1",
                    "-l",
                    str(limits.max_pages),
                    "-enc",
                    "UTF-8",
                    "-nopgbrk",
                    "-q",
                    str(path),
                    str(output_path),
                ],
                timeout_seconds=limits.timeout_seconds,
            )
            if process.returncode == 0 and output_path.exists():
                result.text = _truncate(
                    output_path.read_text(encoding="utf-8", errors="replace"),
                    limits.max_characters,
                )
                result.methods.append("pdftotext")
                return result
            result.warnings.append(
                f"pdftotext_failed:returncode={process.returncode}:stderr={process.stderr.strip()}"
            )

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages[: limits.max_pages]:
            pages.append(page.extract_text() or "")
        result.text = _truncate("\n".join(pages), limits.max_characters)
        result.methods.append("pypdf")
    except Exception as exc:  # noqa: BLE001 - extractor must degrade safely
        result.warnings.append(f"pypdf_failed:{type(exc).__name__}:{exc}")

    return result


def _stringify_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value).strip()


def extract_spreadsheet_cells(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    result = ExtractionResult()
    try:
        workbook = CalamineWorkbook.from_path(str(path))
        parts: list[str] = []
        character_count = 0

        for sheet_name in workbook.sheet_names[: limits.max_sheets]:
            parts.append(f"[SHEET:{sheet_name}]")
            sheet = workbook.get_sheet_by_name(sheet_name)
            rows = sheet.to_python()

            for row in rows[: limits.max_rows]:
                values = [
                    _stringify_cell(value)
                    for value in row[: limits.max_columns]
                ]
                values = [value for value in values if value]
                if not values:
                    continue

                line = "\t".join(values)
                remaining = limits.max_characters - character_count
                if remaining <= 0:
                    break
                line = line[:remaining]
                parts.append(line)
                character_count += len(line) + 1

            if character_count >= limits.max_characters:
                break

        result.text = "\n".join(parts)
        result.methods.append("python-calamine")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"python_calamine_failed:{type(exc).__name__}:{exc}")
    return result


def extract_ooxml_drawing_text(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    result = ExtractionResult()
    if path.suffix.casefold() not in {".xlsx", ".xlsm"}:
        return result

    try:
        parts: list[str] = []
        with zipfile.ZipFile(path) as archive:
            drawing_names = [
                name
                for name in archive.namelist()
                if name.startswith("xl/drawings/") and name.endswith(".xml")
            ]
            for drawing_name in drawing_names:
                root = ElementTree.fromstring(archive.read(drawing_name))
                for element in root.iter():
                    if element.tag.endswith("}t") and element.text:
                        parts.append(element.text.strip())
                        if sum(map(len, parts)) >= limits.max_characters:
                            break
                if sum(map(len, parts)) >= limits.max_characters:
                    break

        if parts:
            result.text = _truncate("\n".join(parts), limits.max_characters)
            result.methods.append("ooxml-drawing-text")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"ooxml_drawing_text_failed:{type(exc).__name__}:{exc}")
    return result


def _ocr_image(
    image_path: Path,
    limits: ExtractionLimits,
    *,
    page_segmentation_mode: int = 6,
) -> ExtractionResult:
    result = ExtractionResult(fallback_used=True)
    tesseract = find_tesseract()
    if not tesseract:
        result.warnings.append("tesseract_missing")
        return result

    process = _run(
        [
            str(tesseract),
            str(image_path),
            "stdout",
            "-l",
            "kor+eng",
            "--psm",
            str(page_segmentation_mode),
        ],
        timeout_seconds=limits.timeout_seconds,
    )
    if process.returncode == 0:
        result.text = _truncate(process.stdout, limits.max_characters)
        result.methods.extend(
            ["tesseract", f"tesseract-psm{page_segmentation_mode}"]
        )
    else:
        result.warnings.append(
            f"tesseract_failed:returncode={process.returncode}:stderr={process.stderr.strip()}"
        )
    return result


def extract_ooxml_embedded_images(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    result = ExtractionResult(fallback_used=True)
    if path.suffix.casefold() not in {".xlsx", ".xlsm"}:
        return result

    try:
        with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(
            prefix="renamer_excel_media_"
        ) as temp_dir:
            media_names = [
                name
                for name in archive.namelist()
                if name.startswith("xl/media/")
            ][:10]

            for index, media_name in enumerate(media_names):
                suffix = Path(media_name).suffix or ".png"
                media_path = Path(temp_dir) / f"media_{index}{suffix}"
                media_path.write_bytes(archive.read(media_name))
                image_result = _ocr_image(media_path, limits)
                result.extend(image_result)
                if len(result.text) >= limits.max_characters:
                    break

        if result.text:
            result.methods.insert(0, "ooxml-embedded-images")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"ooxml_media_failed:{type(exc).__name__}:{exc}")
    return result


def render_spreadsheet_with_excel(path: Path, output_pdf: Path) -> ExtractionResult:
    result = ExtractionResult(fallback_used=True)
    if os.name != "nt":
        result.warnings.append("excel_com_unsupported_platform")
        return result

    excel = None
    workbook = None
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(
            str(path.resolve()),
            UpdateLinks=0,
            ReadOnly=True,
            IgnoreReadOnlyRecommended=True,
        )
        workbook.ExportAsFixedFormat(0, str(output_pdf.resolve()))
        result.methods.append("microsoft-excel-pdf")
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"excel_com_failed:{type(exc).__name__}:{exc}")
    finally:
        if workbook is not None:
            try:
                workbook.Close(False)
            except Exception:  # noqa: BLE001
                pass
        if excel is not None:
            try:
                excel.Quit()
            except Exception:  # noqa: BLE001
                pass
        try:
            import pythoncom

            pythoncom.CoUninitialize()
        except Exception:  # noqa: BLE001
            pass
    return result


def render_spreadsheet_with_libreoffice(
    path: Path,
    output_directory: Path,
    limits: ExtractionLimits,
) -> tuple[Path | None, ExtractionResult]:
    result = ExtractionResult(fallback_used=True)
    soffice = find_libreoffice()
    if not soffice:
        result.warnings.append("libreoffice_missing")
        return None, result

    output_directory.mkdir(parents=True, exist_ok=True)
    process = _run(
        [
            str(soffice),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_directory),
            str(path),
        ],
        timeout_seconds=limits.timeout_seconds,
    )
    output_pdf = output_directory / f"{path.stem}.pdf"
    if process.returncode == 0 and output_pdf.exists():
        result.methods.append("libreoffice-pdf")
        return output_pdf, result

    result.warnings.append(
        f"libreoffice_failed:returncode={process.returncode}:stderr={process.stderr.strip()}"
    )
    return None, result


def render_spreadsheet_to_pdf(path: Path, limits: ExtractionLimits) -> tuple[Path | None, Path | None, ExtractionResult]:
    work_dir = Path(tempfile.mkdtemp(prefix="renamer_excel_pdf_"))
    output_pdf = work_dir / "rendered.pdf"

    excel_result = render_spreadsheet_with_excel(path, output_pdf)
    if output_pdf.exists():
        return output_pdf, work_dir, excel_result

    libreoffice_pdf, libreoffice_result = render_spreadsheet_with_libreoffice(
        path,
        work_dir,
        limits,
    )
    excel_result.extend(libreoffice_result)
    if libreoffice_pdf and libreoffice_pdf.exists():
        return libreoffice_pdf, work_dir, excel_result

    shutil.rmtree(work_dir, ignore_errors=True)
    return None, None, excel_result


def ocr_pdf(
    path: Path,
    limits: ExtractionLimits,
    *,
    page_segmentation_mode: int = 6,
    dpi: int | None = None,
    grayscale: bool = False,
) -> ExtractionResult:
    result = ExtractionResult(fallback_used=True)
    pdftoppm = find_pdftoppm()
    if not pdftoppm:
        result.warnings.append("pdftoppm_missing")
        return result

    with tempfile.TemporaryDirectory(prefix="renamer_pdf_ocr_") as temp_dir:
        prefix = Path(temp_dir) / "page"
        active_dpi = dpi or limits.ocr_dpi
        render_arguments = [
            str(pdftoppm),
            "-f",
            "1",
            "-l",
            str(limits.max_pages),
            "-r",
            str(active_dpi),
        ]
        if grayscale:
            render_arguments.append("-gray")
        render_arguments.extend(["-png", str(path), str(prefix)])
        process = _run(
            render_arguments,
            timeout_seconds=limits.timeout_seconds,
        )
        if process.returncode != 0:
            result.warnings.append(
                f"pdftoppm_failed:returncode={process.returncode}:stderr={process.stderr.strip()}"
            )
            return result

        result.methods.extend(
            [
                "pdftoppm",
                f"pdftoppm-dpi{active_dpi}{'-gray' if grayscale else ''}",
            ]
        )
        for image_path in sorted(Path(temp_dir).glob("page-*.png")):
            result.extend(
                _ocr_image(
                    image_path,
                    limits,
                    page_segmentation_mode=page_segmentation_mode,
                )
            )
            if len(result.text) >= limits.max_characters:
                break

    result.text = _truncate(result.text, limits.max_characters)
    return result


def extract_primary_text(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    extension = path.suffix.casefold()
    if extension in PDF_EXTENSIONS:
        return extract_pdf_text(path, limits)

    if extension in SPREADSHEET_EXTENSIONS:
        result = extract_spreadsheet_cells(path, limits)
        result.extend(extract_ooxml_drawing_text(path, limits))
        return result

    return ExtractionResult(warnings=[f"unsupported_extension:{extension}"])


def extract_spreadsheet_fallback(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    result = extract_ooxml_embedded_images(path, limits)

    rendered_pdf, work_dir, render_result = render_spreadsheet_to_pdf(path, limits)
    result.extend(render_result)
    try:
        if rendered_pdf:
            result.extend(extract_pdf_text(rendered_pdf, limits))
            result.extend(ocr_pdf(rendered_pdf, limits))
    finally:
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
    return result


def health_report() -> dict[str, str]:
    def display(path: Path | None) -> str:
        return str(path) if path else "missing"

    return {
        "installation_root": str(installation_root()),
        "pdftotext": display(find_pdftotext()),
        "pdftoppm": display(find_pdftoppm()),
        "tesseract": display(find_tesseract()),
        "libreoffice": display(find_libreoffice()),
    }
