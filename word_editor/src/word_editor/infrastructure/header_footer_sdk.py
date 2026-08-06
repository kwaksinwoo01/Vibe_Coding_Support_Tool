from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import pywintypes

from word_editor.infrastructure.word_com import (
    WD_DO_NOT_SAVE_CHANGES,
    WordGatewayError,
)
from word_editor.infrastructure.word_style_sdk import WordStyleSdkGateway

WD_HEADER_FOOTER_PRIMARY = 1
WD_HEADER_FOOTER_FIRST_PAGE = 2
WD_HEADER_FOOTER_EVEN_PAGES = 3

HEADER_FOOTER_VARIANTS: tuple[tuple[int, str], ...] = (
    (WD_HEADER_FOOTER_PRIMARY, "primary"),
    (WD_HEADER_FOOTER_FIRST_PAGE, "first-page"),
    (WD_HEADER_FOOTER_EVEN_PAGES, "even-pages"),
)


@dataclass(frozen=True, slots=True)
class HeaderFooterApplyOptions:
    section_mode: str = "match-index"
    include_headers: bool = True
    include_footers: bool = True
    copy_page_setup_flags: bool = True

    def __post_init__(self) -> None:
        if self.section_mode not in {"match-index", "repeat-first"}:
            raise ValueError(
                "section_mode must be 'match-index' or 'repeat-first'."
            )


class HeaderFooterSdk:
    """Inventory and apply company header/footer layout assets.

    Missing Word defaults are not errors. Only header/footer ranges that exist
    or contain actual content are recorded.
    """

    def __init__(self, gateway: WordStyleSdkGateway) -> None:
        self.gateway = gateway

    @staticmethod
    def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
        try:
            return getattr(obj, name)
        except (pywintypes.com_error, AttributeError, TypeError):
            return default

    @staticmethod
    def _count(collection: Any) -> int:
        try:
            return int(collection.Count)
        except (pywintypes.com_error, AttributeError, TypeError, ValueError):
            return 0

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        content = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _entry_record(
        self,
        section_index: int,
        kind: str,
        variant_name: str,
        header_footer: Any,
    ) -> dict[str, Any] | None:
        exists = bool(self._safe_get(header_footer, "Exists", False))
        range_object = self._safe_get(header_footer, "Range")
        text = str(self._safe_get(range_object, "Text", ""))
        # Word terminates header/footer ranges with a paragraph mark.
        visible_text = text.rstrip("\r\x07")
        fields = self._count(self._safe_get(range_object, "Fields"))
        tables = self._count(self._safe_get(range_object, "Tables"))
        inline_shapes = self._count(
            self._safe_get(range_object, "InlineShapes")
        )
        shapes = self._count(self._safe_get(header_footer, "Shapes"))
        has_content = bool(
            visible_text or fields or tables or inline_shapes or shapes
        )
        if not exists and not has_content:
            return None
        structure = {
            "text_sha256": hashlib.sha256(
                visible_text.encode("utf-8")
            ).hexdigest(),
            "text_length": len(visible_text),
            "fields": fields,
            "tables": tables,
            "inline_shapes": inline_shapes,
            "floating_shapes": shapes,
            "link_to_previous": bool(
                self._safe_get(header_footer, "LinkToPrevious", False)
            ),
            "exists": exists,
        }
        return {
            "key": f"section:{section_index}|{kind}|{variant_name}",
            "section": section_index,
            "kind": kind,
            "variant": variant_name,
            **structure,
            "content_sha256": self._fingerprint(structure),
        }

    def capture_document_object(self, document: Any) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        try:
            section_count = int(document.Sections.Count)
        except (pywintypes.com_error, TypeError, ValueError):
            return records
        for section_index in range(1, section_count + 1):
            try:
                section = document.Sections.Item(section_index)
            except pywintypes.com_error:
                continue
            for collection_name, kind in (
                ("Headers", "header"),
                ("Footers", "footer"),
            ):
                collection = self._safe_get(section, collection_name)
                if collection is None:
                    continue
                for variant_value, variant_name in HEADER_FOOTER_VARIANTS:
                    try:
                        header_footer = collection.Item(variant_value)
                    except pywintypes.com_error:
                        continue
                    record = self._entry_record(
                        section_index,
                        kind,
                        variant_name,
                        header_footer,
                    )
                    if record is not None:
                        records.append(record)
        records.sort(key=lambda item: str(item["key"]).casefold())
        return records

    def capture_path(self, path: Path) -> list[dict[str, Any]]:
        target = self.gateway._validate_target(path)
        with self.gateway._session() as session:
            document, owns_document = self.gateway._open_target(
                session.application,
                target,
                read_only=True,
            )
            try:
                return self.capture_document_object(document)
            finally:
                if owns_document:
                    try:
                        document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                    except pywintypes.com_error:
                        pass

    @staticmethod
    def _source_section_index(
        target_index: int,
        source_count: int,
        mode: str,
    ) -> int:
        if mode == "repeat-first":
            return 1
        return min(target_index, source_count)

    @staticmethod
    def _copy_range(source: Any, destination: Any) -> None:
        try:
            destination.FormattedText = source.FormattedText
        except pywintypes.com_error as exc:
            raise WordGatewayError(
                f"머리글·바닥글 서식을 복사하지 못했습니다: {exc}"
            ) from exc

    def apply_asset(
        self,
        source_path: Path,
        target_path: Path,
        options: HeaderFooterApplyOptions = HeaderFooterApplyOptions(),
    ) -> Path:
        source = self.gateway._validate_target(source_path)
        target = self.gateway._validate_target(target_path)
        if self.gateway._same_path(source, target):
            raise WordGatewayError("원본과 대상 Word 파일이 같습니다.")

        with self.gateway._session() as session:
            source_document, owns_source = self.gateway._open_target(
                session.application,
                source,
                read_only=True,
            )
            target_document, owns_target = self.gateway._open_target(
                session.application,
                target,
                read_only=False,
            )
            backup = Path()
            try:
                if not bool(
                    self.gateway._safe_get(target_document, "Saved", True)
                ):
                    raise WordGatewayError(
                        "대상 문서에 저장하지 않은 변경이 있습니다. 먼저 저장하십시오."
                    )
                source_count = int(source_document.Sections.Count)
                target_count = int(target_document.Sections.Count)
                if source_count < 1 or target_count < 1:
                    raise WordGatewayError(
                        "원본 또는 대상 문서에 구역이 없습니다."
                    )
                backup = self.gateway._make_target_backup(
                    target_document,
                    target,
                )
                for target_index in range(1, target_count + 1):
                    source_index = self._source_section_index(
                        target_index,
                        source_count,
                        options.section_mode,
                    )
                    source_section = source_document.Sections.Item(source_index)
                    target_section = target_document.Sections.Item(target_index)
                    if options.copy_page_setup_flags:
                        for property_name in (
                            "DifferentFirstPageHeaderFooter",
                            "OddAndEvenPagesHeaderFooter",
                            "HeaderDistance",
                            "FooterDistance",
                        ):
                            try:
                                setattr(
                                    target_section.PageSetup,
                                    property_name,
                                    getattr(source_section.PageSetup, property_name),
                                )
                            except (pywintypes.com_error, AttributeError):
                                continue
                    for collection_name, enabled in (
                        ("Headers", options.include_headers),
                        ("Footers", options.include_footers),
                    ):
                        if not enabled:
                            continue
                        source_collection = getattr(source_section, collection_name)
                        target_collection = getattr(target_section, collection_name)
                        for variant_value, _ in HEADER_FOOTER_VARIANTS:
                            source_item = source_collection.Item(variant_value)
                            target_item = target_collection.Item(variant_value)
                            source_exists = bool(
                                self._safe_get(source_item, "Exists", False)
                            )
                            source_range = self._safe_get(source_item, "Range")
                            source_text = str(
                                self._safe_get(source_range, "Text", "")
                            ).rstrip("\r\x07")
                            source_has_objects = bool(
                                self._count(
                                    self._safe_get(source_range, "Fields")
                                )
                                or self._count(
                                    self._safe_get(source_range, "Tables")
                                )
                                or self._count(
                                    self._safe_get(source_range, "InlineShapes")
                                )
                                or self._count(
                                    self._safe_get(source_item, "Shapes")
                                )
                            )
                            if not source_exists and not source_text and not source_has_objects:
                                continue
                            try:
                                target_item.LinkToPrevious = False
                            except pywintypes.com_error:
                                pass
                            self._copy_range(source_range, target_item.Range)
                target_document.Save()
                return backup
            except Exception:
                # The target has not been saved if copying fails before Save().
                # The complete timestamped backup remains available regardless.
                raise
            finally:
                if owns_source:
                    try:
                        source_document.Close(
                            SaveChanges=WD_DO_NOT_SAVE_CHANGES
                        )
                    except pywintypes.com_error:
                        pass
                if owns_target:
                    try:
                        target_document.Close(
                            SaveChanges=WD_DO_NOT_SAVE_CHANGES
                        )
                    except pywintypes.com_error:
                        pass
