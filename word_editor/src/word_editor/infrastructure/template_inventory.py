from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import tempfile
from typing import Any

import pywintypes

from word_editor.domain.template_lifecycle import TemplateAssetInventory
from word_editor.infrastructure.header_footer_sdk import HeaderFooterSdk
from word_editor.infrastructure.word_com import WD_DO_NOT_SAVE_CHANGES, WordGatewayError
from word_editor.infrastructure.word_style_sdk import WordStyleSdkGateway


class TemplateInventoryReader:
    def __init__(self, gateway: WordStyleSdkGateway) -> None:
        self.gateway = gateway
        self.header_footer_sdk = HeaderFooterSdk(gateway)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _text_sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _same_path(left: Path, right: Path) -> bool:
        try:
            return left.resolve() == right.resolve()
        except OSError:
            return str(left).casefold() == str(right).casefold()

    def _find_template_object(
        self,
        application: Any,
        target: Path,
    ) -> Any | None:
        if self.gateway._is_normal_path(target):
            return application.NormalTemplate
        try:
            count = int(application.Templates.Count)
        except (pywintypes.com_error, TypeError, ValueError):
            return None
        for index in range(1, count + 1):
            try:
                template = application.Templates.Item(index)
                full_name = str(template.FullName)
                if full_name and self._same_path(Path(full_name), target):
                    return template
            except (pywintypes.com_error, OSError, ValueError):
                continue
        return None

    @staticmethod
    def _safe_value(obj: Any, name: str, default: Any = None) -> Any:
        try:
            return getattr(obj, name)
        except (pywintypes.com_error, AttributeError, TypeError):
            return default

    def _read_building_blocks(self, template: Any) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        try:
            collection = template.BuildingBlockEntries
            count = int(collection.Count)
        except (pywintypes.com_error, AttributeError, TypeError, ValueError):
            return entries
        for index in range(1, count + 1):
            try:
                entry = collection.Item(index)
                category = self._safe_value(entry, "Category")
                category_name = self._safe_value(category, "Name", "")
                name = str(self._safe_value(entry, "Name", ""))
                block_type = self._safe_value(entry, "Type")
                raw_value = self._safe_value(entry, "Value", None)
                if raw_value is None:
                    value_length: int | None = None
                    value_sha256 = ""
                else:
                    text_value = str(raw_value)
                    value_length = len(text_value)
                    value_sha256 = self._text_sha256(text_value)
                entries.append(
                    {
                        "key": f"{name}|{block_type}|{category_name}",
                        "name": name,
                        "type": block_type,
                        "category": str(category_name),
                        "description": str(
                            self._safe_value(entry, "Description", "")
                        ),
                        "insert_options": self._safe_value(
                            entry,
                            "InsertOptions",
                        ),
                        "value_sha256": value_sha256,
                        "value_length": value_length,
                    }
                )
            except (pywintypes.com_error, AttributeError, TypeError, ValueError):
                continue
        entries.sort(key=lambda item: str(item.get("key", "")).casefold())
        return entries

    def _read_autotext(self, template: Any) -> list[str]:
        names: list[str] = []
        try:
            collection = template.AutoTextEntries
            count = int(collection.Count)
        except (pywintypes.com_error, AttributeError, TypeError, ValueError):
            return names
        for index in range(1, count + 1):
            try:
                names.append(str(collection.Item(index).Name))
            except (pywintypes.com_error, AttributeError, TypeError, ValueError):
                continue
        return sorted(set(names), key=str.casefold)

    def make_preservation_copy(self, source: Path, destination: Path) -> Path:
        source = source.expanduser().resolve()
        destination = destination.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, destination)
            return destination
        except OSError:
            pass

        with self.gateway._session() as session:
            document, owns_document = self.gateway._open_target(
                session.application,
                source,
                read_only=True,
            )
            try:
                document.SaveCopyAs(str(destination))
            except pywintypes.com_error as exc:
                raise WordGatewayError(
                    f"템플릿 보존 복사본을 만들지 못했습니다: {source}: {exc}"
                ) from exc
            finally:
                if owns_document:
                    document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
        return destination

    def capture(self, path: Path) -> TemplateAssetInventory:
        target = self.gateway._validate_target(path)
        # The inventory requires a stable style identity hash, not every style
        # property. The fast index avoids a second full two-minute scan.
        snapshot = self.gateway.snapshot_path_index(target)
        warnings: list[str] = []
        building_blocks: list[dict[str, Any]] = []
        autotext_entries: list[str] = []
        header_footer_entries: list[dict[str, Any]] = []
        template_object_found = False

        with self.gateway._session() as session:
            document, owns_document = self.gateway._open_target(
                session.application,
                target,
                read_only=True,
            )
            try:
                header_footer_entries = (
                    self.header_footer_sdk.capture_document_object(document)
                )
                try:
                    session.application.Templates.LoadBuildingBlocks()
                except (pywintypes.com_error, AttributeError) as exc:
                    warnings.append(
                        "Word가 Building Block 강제 로드를 거부했습니다. "
                        f"현재 로드 상태로 인벤토리를 계속합니다: {exc}"
                    )
                template = self._find_template_object(
                    session.application,
                    target,
                )
                if template is None:
                    warnings.append(
                        "Word Templates 컬렉션에서 대상 템플릿 객체를 찾지 못해 "
                        "Building Block/AutoText 목록을 읽지 못했습니다. "
                        "원본 파일 전체와 머리글·바닥글은 계속 보존됩니다."
                    )
                else:
                    template_object_found = True
                    building_blocks = self._read_building_blocks(template)
                    autotext_entries = self._read_autotext(template)
            finally:
                if owns_document:
                    document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)

        try:
            file_sha256 = self._sha256(target)
            file_size = target.stat().st_size
        except OSError:
            with tempfile.TemporaryDirectory(prefix="word-template-inventory-") as temp:
                copy_path = Path(temp) / target.name
                self.make_preservation_copy(target, copy_path)
                file_sha256 = self._sha256(copy_path)
                file_size = copy_path.stat().st_size
                warnings.append(
                    "원본 파일이 사용 중이어서 Word SaveCopyAs 복사본을 기준으로 "
                    "파일 해시를 계산했습니다."
                )

        return TemplateAssetInventory(
            source_path=str(target),
            captured_at=datetime.now(timezone.utc).isoformat(),
            file_sha256=file_sha256,
            file_size=file_size,
            styles_sha256=str(
                snapshot.metadata.get("styles_sha256") or snapshot.sha256
            ),
            building_blocks=building_blocks,
            autotext_entries=autotext_entries,
            header_footer_entries=header_footer_entries,
            template_object_found=template_object_found,
            warnings=warnings,
        )
