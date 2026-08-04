from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Iterator

import pythoncom
import pywintypes
import win32com.client

from word_editor.domain.models import PatchOperation, StyleDefinition, TemplateSnapshot

POINTS_PER_CM = 72.0 / 2.54
WD_DO_NOT_SAVE_CHANGES = 0
WD_SAVE_CHANGES = -1
WD_ALERTS_NONE = 0
WD_ORGANIZER_OBJECT_STYLES = 3


class WordGatewayError(RuntimeError):
    pass


class ConcurrentTemplateChange(WordGatewayError):
    pass


@dataclass(slots=True)
class _WordSession:
    application: Any
    owns_application: bool


@dataclass(slots=True)
class _StyleObjectIndex:
    exact: dict[str, Any]
    folded: dict[str, Any]


class WordComGateway:
    """Read and edit Word styles through the desktop Word COM object model."""

    def __init__(self, normal_path: Path, backup_directory: Path) -> None:
        self.normal_path = normal_path
        self.backup_directory = backup_directory
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _session(self) -> Iterator[_WordSession]:
        pythoncom.CoInitialize()
        application = None
        owns_application = False
        try:
            try:
                application = win32com.client.GetActiveObject("Word.Application")
            except (pywintypes.com_error, AttributeError):
                application = win32com.client.gencache.EnsureDispatch(
                    "Word.Application"
                )
                application.Visible = False
                owns_application = True
            application.DisplayAlerts = WD_ALERTS_NONE
            try:
                application.Options.SaveNormalPrompt = False
            except pywintypes.com_error:
                pass
            yield _WordSession(application, owns_application)
        finally:
            if application is not None and owns_application:
                try:
                    save_changes = WD_DO_NOT_SAVE_CHANGES
                    application.Quit(SaveChanges=save_changes)
                except pywintypes.com_error:
                    try:
                        application.Quit()
                    except pywintypes.com_error:
                        pass
            application = None
            pythoncom.CoUninitialize()

    @staticmethod
    def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
        if obj is None:
            return default
        try:
            return getattr(obj, name)
        except (pywintypes.com_error, AttributeError, TypeError):
            return default

    @staticmethod
    def _word_bool(value: Any) -> bool | int | None:
        if value is None:
            return None
        try:
            integer = int(value)
        except (TypeError, ValueError):
            return None
        if integer == 0:
            return False
        if integer == -1:
            return True
        return integer

    @staticmethod
    def _reference_name(style: Any, property_name: str) -> str:
        try:
            reference = getattr(style, property_name)
        except (pywintypes.com_error, AttributeError):
            return ""
        if reference is None:
            return ""
        if isinstance(reference, str):
            return reference
        try:
            return str(reference.NameLocal)
        except (pywintypes.com_error, AttributeError):
            return str(reference)

    @staticmethod
    def _style_type_name(value: Any) -> str:
        names = {
            1: "Paragraph",
            2: "Character",
            3: "Table",
            4: "List",
            5: "ParagraphOnly",
            6: "Linked",
        }
        try:
            integer = int(value)
        except (TypeError, ValueError):
            return "Unknown"
        return names.get(integer, f"Unknown({integer})")

    def _read_style(self, style: Any) -> StyleDefinition:
        style_type_value = self._safe_get(style, "Type")
        style_type = self._style_type_name(style_type_value)
        font = self._safe_get(style, "Font")
        paragraph = None if style_type == "Character" else self._safe_get(
            style, "ParagraphFormat"
        )

        properties: dict[str, Any] = {
            "style.base_style": self._reference_name(style, "BaseStyle"),
            "style.next_style": self._reference_name(
                style, "NextParagraphStyle"
            ),
            "style.priority": self._safe_get(style, "Priority"),
            "style.quick_style": self._word_bool(
                self._safe_get(style, "QuickStyle")
            ),
            "style.hidden": self._word_bool(self._safe_get(style, "Hidden")),
            "style.unhide_when_used": self._word_bool(
                self._safe_get(style, "UnhideWhenUsed")
            ),
            "style.automatically_update": self._word_bool(
                self._safe_get(style, "AutomaticallyUpdate")
            ),
            "style.no_space_same_style": self._word_bool(
                self._safe_get(
                    style, "NoSpaceBetweenParagraphsOfSameStyle"
                )
            ),
            "font.name": self._safe_get(font, "Name"),
            "font.name_ascii": self._safe_get(font, "NameAscii"),
            "font.name_far_east": self._safe_get(font, "NameFarEast"),
            "font.name_other": self._safe_get(font, "NameOther"),
            "font.size_pt": self._safe_get(font, "Size"),
            "font.bold": self._word_bool(self._safe_get(font, "Bold")),
            "font.italic": self._word_bool(self._safe_get(font, "Italic")),
            "font.underline": self._safe_get(font, "Underline"),
            "font.scaling_percent": self._safe_get(font, "Scaling"),
            "paragraph.alignment": self._safe_get(paragraph, "Alignment"),
            "paragraph.left_indent_cm": self._points_to_cm(
                self._safe_get(paragraph, "LeftIndent")
            ),
            "paragraph.right_indent_cm": self._points_to_cm(
                self._safe_get(paragraph, "RightIndent")
            ),
            "paragraph.first_line_indent_cm": self._points_to_cm(
                self._safe_get(paragraph, "FirstLineIndent")
            ),
            "paragraph.space_before_pt": self._safe_get(
                paragraph, "SpaceBefore"
            ),
            "paragraph.space_after_pt": self._safe_get(
                paragraph, "SpaceAfter"
            ),
            "paragraph.line_spacing_rule": self._safe_get(
                paragraph, "LineSpacingRule"
            ),
            "paragraph.outline_level": self._safe_get(
                paragraph, "OutlineLevel"
            ),
            "paragraph.keep_together": self._word_bool(
                self._safe_get(paragraph, "KeepTogether")
            ),
            "paragraph.keep_with_next": self._word_bool(
                self._safe_get(paragraph, "KeepWithNext")
            ),
            "paragraph.page_break_before": self._word_bool(
                self._safe_get(paragraph, "PageBreakBefore")
            ),
        }

        list_binding: dict[str, Any] = {}
        try:
            list_template = style.ListTemplate
            list_binding["template_name"] = str(
                self._safe_get(list_template, "Name", "")
            )
            level = int(style.ListLevelNumber)
            list_binding["level"] = level if 1 <= level <= 9 else None
        except (pywintypes.com_error, TypeError, ValueError):
            pass

        return StyleDefinition(
            name=str(style.NameLocal),
            style_type=style_type,
            built_in=bool(self._word_bool(self._safe_get(style, "BuiltIn"))),
            in_use=bool(self._word_bool(self._safe_get(style, "InUse"))),
            properties={key: value for key, value in properties.items()},
            list_binding=list_binding,
        )

    def _read_list_templates(self, document: Any) -> dict[str, dict[str, Any]]:
        templates: dict[str, dict[str, Any]] = {}
        try:
            count = int(document.ListTemplates.Count)
        except pywintypes.com_error:
            return templates

        for template_index in range(1, count + 1):
            template = document.ListTemplates.Item(template_index)
            name = str(self._safe_get(template, "Name", ""))
            key = f"{template_index:03d}|{name}"
            levels: list[dict[str, Any]] = []
            for level_index in range(1, 10):
                try:
                    level = template.ListLevels.Item(level_index)
                except pywintypes.com_error:
                    continue
                level_font = self._safe_get(level, "Font")
                levels.append(
                    {
                        "index": level_index,
                        "linked_style": self._safe_get(
                            level, "LinkedStyle", ""
                        ),
                        "number_style": self._safe_get(level, "NumberStyle"),
                        "number_format": self._safe_get(
                            level, "NumberFormat", ""
                        ),
                        "alignment": self._safe_get(level, "Alignment"),
                        "number_position_cm": self._points_to_cm(
                            self._safe_get(level, "NumberPosition")
                        ),
                        "text_position_cm": self._points_to_cm(
                            self._safe_get(level, "TextPosition")
                        ),
                        "tab_position_cm": self._points_to_cm(
                            self._safe_get(level, "TabPosition")
                        ),
                        "trailing_character": self._safe_get(
                            level, "TrailingCharacter"
                        ),
                        "start_at": self._safe_get(level, "StartAt"),
                        "reset_on_higher": self._safe_get(
                            level, "ResetOnHigher"
                        ),
                        "font_name": self._safe_get(level_font, "Name"),
                    }
                )
            templates[key] = {
                "name": name,
                "outline_numbered": self._word_bool(
                    self._safe_get(template, "OutlineNumbered")
                ),
                "levels": levels,
            }
        return templates

    @staticmethod
    def _points_to_cm(value: Any) -> float | None:
        try:
            return round(float(value) / POINTS_PER_CM, 4)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _snapshot_hash(
        styles: dict[str, StyleDefinition],
        list_templates: dict[str, dict[str, Any]],
    ) -> str:
        payload = {
            "styles": {
                name: style.to_dict() for name, style in sorted(styles.items())
            },
            "list_templates": list_templates,
        }
        content = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _styles_hash(styles: dict[str, StyleDefinition]) -> str:
        content = json.dumps(
            {
                name: style.to_dict()
                for name, style in sorted(styles.items())
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _snapshot_document_object(
        self,
        application: Any,
        document: Any,
        source_path: Path,
    ) -> TemplateSnapshot:
        styles: dict[str, StyleDefinition] = {}
        for index in range(1, int(document.Styles.Count) + 1):
            try:
                style = document.Styles.Item(index)
                definition = self._read_style(style)
                styles[definition.name] = definition
            except pywintypes.com_error:
                continue
        list_templates = self._read_list_templates(document)
        snapshot_hash = self._snapshot_hash(styles, list_templates)
        metadata: dict[str, Any] = {}
        metadata["styles_sha256"] = self._styles_hash(styles)
        try:
            metadata["file_modified_at"] = source_path.stat().st_mtime
        except OSError:
            pass
        try:
            first_range = document.Paragraphs.Item(1).Range
            first_style = first_range.Style
            metadata["default_paragraph_style"] = str(
                self._safe_get(first_style, "NameLocal", first_style)
            )
        except (pywintypes.com_error, AttributeError):
            pass
        return TemplateSnapshot(
            source_path=str(source_path),
            sha256=snapshot_hash,
            captured_at=datetime.now(timezone.utc).isoformat(),
            word_version=str(application.Version),
            styles=styles,
            list_templates=list_templates,
            metadata=metadata,
        )

    def snapshot_normal(self) -> TemplateSnapshot:
        if not self.normal_path.exists():
            raise WordGatewayError(f"Normal.dotm not found: {self.normal_path}")
        with self._session() as session:
            document = session.application.NormalTemplate.OpenAsDocument()
            try:
                return self._snapshot_document_object(
                    session.application, document, self.normal_path
                )
            finally:
                document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)

    def snapshot_document(self, path: Path) -> TemplateSnapshot:
        if not path.exists():
            raise WordGatewayError(f"Word document not found: {path}")
        with self._session() as session:
            document = session.application.Documents.Open(
                FileName=str(path),
                ReadOnly=True,
                AddToRecentFiles=False,
                Visible=False,
            )
            try:
                return self._snapshot_document_object(
                    session.application, document, path
                )
            finally:
                document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)

    def _make_backup(self, document: Any) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self.backup_directory / f"Normal.{timestamp}.dotm"
        document.SaveCopyAs(str(destination))
        return destination

    @staticmethod
    def _to_word_bool(value: Any) -> int:
        return -1 if bool(value) else 0

    def _build_style_object_index(self, styles: Any) -> _StyleObjectIndex:
        exact: dict[str, Any] = {}
        folded: dict[str, Any] = {}
        try:
            count = int(styles.Count)
        except (pywintypes.com_error, TypeError, ValueError) as exc:
            raise WordGatewayError(
                f"Could not enumerate the Word Styles collection: {exc}"
            ) from exc

        for index in range(1, count + 1):
            try:
                style = styles.Item(index)
            except pywintypes.com_error:
                continue
            names = (
                self._safe_get(style, "NameLocal", ""),
                self._safe_get(style, "Name", ""),
            )
            for raw_name in names:
                if not raw_name:
                    continue
                name = str(raw_name)
                exact.setdefault(name, style)
                folded.setdefault(name.casefold(), style)
        return _StyleObjectIndex(exact=exact, folded=folded)

    @staticmethod
    def _resolve_style_object(
        style_index: _StyleObjectIndex,
        value: Any,
        *,
        context: str,
    ) -> Any:
        if not isinstance(value, str):
            if hasattr(value, "NameLocal"):
                return value
            raise WordGatewayError(
                f"{context} requires a style name, got {value!r}."
            )
        resolved = style_index.exact.get(value)
        if resolved is None:
            resolved = style_index.folded.get(value.casefold())
        if resolved is None:
            raise WordGatewayError(
                f"{context} references a style that is not present in the "
                f"open Word template: {value!r}. Refresh the snapshot and "
                "select an existing style."
            )
        return resolved

    def _set_property(
        self,
        style: Any,
        property_name: str,
        value: Any,
        style_index: _StyleObjectIndex | None = None,
    ) -> None:
        if property_name == "style.base_style":
            if not value:
                style.BaseStyle = ""
                return
            if style_index is None:
                raise WordGatewayError(
                    "A Word style index is required to set style.base_style."
                )
            reference = self._resolve_style_object(
                style_index,
                value,
                context=f"{self._safe_get(style, 'NameLocal', '<style>')}.BaseStyle",
            )
            if reference is style:
                raise WordGatewayError(
                    f"{self._safe_get(style, 'NameLocal', '<style>')} cannot "
                    "use itself as its base style."
                )
            style.BaseStyle = reference
            return
        if property_name == "style.next_style":
            if style_index is None:
                raise WordGatewayError(
                    "A Word style index is required to set style.next_style."
                )
            reference_name = value or str(style.NameLocal)
            reference = self._resolve_style_object(
                style_index,
                reference_name,
                context=(
                    f"{self._safe_get(style, 'NameLocal', '<style>')}"
                    ".NextParagraphStyle"
                ),
            )
            style.NextParagraphStyle = reference
            return

        direct_style = {
            "style.priority": "Priority",
            "style.quick_style": "QuickStyle",
            "style.hidden": "Hidden",
            "style.unhide_when_used": "UnhideWhenUsed",
            "style.automatically_update": "AutomaticallyUpdate",
            "style.no_space_same_style": (
                "NoSpaceBetweenParagraphsOfSameStyle"
            ),
        }
        if property_name in direct_style:
            attribute = direct_style[property_name]
            if property_name in {
                "style.quick_style",
                "style.hidden",
                "style.unhide_when_used",
                "style.automatically_update",
                "style.no_space_same_style",
            }:
                value = self._to_word_bool(value)
            setattr(style, attribute, value)
            return

        font_mapping = {
            "font.name": "Name",
            "font.name_ascii": "NameAscii",
            "font.name_far_east": "NameFarEast",
            "font.name_other": "NameOther",
            "font.size_pt": "Size",
            "font.bold": "Bold",
            "font.italic": "Italic",
            "font.underline": "Underline",
            "font.scaling_percent": "Scaling",
        }
        if property_name in font_mapping:
            if property_name in {"font.bold", "font.italic"}:
                value = self._to_word_bool(value)
            setattr(style.Font, font_mapping[property_name], value)
            return

        paragraph_mapping = {
            "paragraph.alignment": "Alignment",
            "paragraph.space_before_pt": "SpaceBefore",
            "paragraph.space_after_pt": "SpaceAfter",
            "paragraph.line_spacing_rule": "LineSpacingRule",
            "paragraph.outline_level": "OutlineLevel",
            "paragraph.keep_together": "KeepTogether",
            "paragraph.keep_with_next": "KeepWithNext",
            "paragraph.page_break_before": "PageBreakBefore",
        }
        if property_name in paragraph_mapping:
            if property_name in {
                "paragraph.keep_together",
                "paragraph.keep_with_next",
                "paragraph.page_break_before",
            }:
                value = self._to_word_bool(value)
            setattr(style.ParagraphFormat, paragraph_mapping[property_name], value)
            return

        indent_mapping = {
            "paragraph.left_indent_cm": "LeftIndent",
            "paragraph.right_indent_cm": "RightIndent",
            "paragraph.first_line_indent_cm": "FirstLineIndent",
        }
        if property_name in indent_mapping:
            setattr(
                style.ParagraphFormat,
                indent_mapping[property_name],
                float(value) * POINTS_PER_CM,
            )
            return
        raise WordGatewayError(f"Unsupported property: {property_name}")

    def apply_operations(
        self,
        operations: list[PatchOperation],
        expected_snapshot_sha256: str,
    ) -> tuple[TemplateSnapshot, Path]:
        if not operations:
            snapshot = self.snapshot_normal()
            return snapshot, Path()
        with self._session() as session:
            document = session.application.NormalTemplate.OpenAsDocument()
            backup_path: Path | None = None
            try:
                current = self._snapshot_document_object(
                    session.application, document, self.normal_path
                )
                if current.sha256 != expected_snapshot_sha256:
                    raise ConcurrentTemplateChange(
                        "Normal.dotm changed after the editor loaded it. "
                        "Refresh and merge before applying."
                    )
                backup_path = self._make_backup(document)
                style_index = self._build_style_object_index(document.Styles)
                for operation in operations:
                    definition = current.styles.get(operation.style_name)
                    if definition is None:
                        raise WordGatewayError(
                            f"Style not found: {operation.style_name}"
                        )
                    actual_old = definition.properties.get(
                        operation.property_name
                    )
                    if actual_old != operation.expected_old_value:
                        raise ConcurrentTemplateChange(
                            f"{operation.style_name}.{operation.property_name} "
                            "changed concurrently."
                        )
                    style = self._resolve_style_object(
                        style_index,
                        operation.style_name,
                        context="Patch operation",
                    )
                    self._set_property(
                        style,
                        operation.property_name,
                        operation.value,
                        style_index,
                    )
                document.Save()
                updated = self._snapshot_document_object(
                    session.application, document, self.normal_path
                )
                return updated, backup_path
            except Exception:
                try:
                    document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                except pywintypes.com_error:
                    pass
                raise
            finally:
                try:
                    document.Close(SaveChanges=WD_SAVE_CHANGES)
                except pywintypes.com_error:
                    pass

    def inject_styles_into_document(
        self,
        document_path: Path,
        style_names: list[str],
    ) -> None:
        if not document_path.exists():
            raise WordGatewayError(f"Word document not found: {document_path}")
        with self._session() as session:
            for style_name in style_names:
                session.application.OrganizerCopy(
                    Source=str(self.normal_path),
                    Destination=str(document_path),
                    Name=style_name,
                    Object=WD_ORGANIZER_OBJECT_STYLES,
                )

    def update_document_from_normal(
        self,
        document_path: Path,
        keep_existing_attachment: bool = True,
    ) -> None:
        with self._session() as session:
            document = session.application.Documents.Open(
                FileName=str(document_path),
                ReadOnly=False,
                AddToRecentFiles=False,
                Visible=False,
            )
            try:
                previous_template = str(document.AttachedTemplate.FullName)
                document.AttachedTemplate = str(self.normal_path)
                document.UpdateStyles()
                document.UpdateStylesOnOpen = False
                if keep_existing_attachment and previous_template:
                    document.AttachedTemplate = previous_template
                document.Save()
            finally:
                document.Close(SaveChanges=WD_SAVE_CHANGES)

    def restore_backup(self, backup_path: Path) -> None:
        if not backup_path.exists():
            raise WordGatewayError(f"Backup not found: {backup_path}")
        with self._session() as session:
            normal_document = session.application.NormalTemplate.OpenAsDocument()
            try:
                normal_document.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
            except pywintypes.com_error:
                pass
        shutil.copy2(backup_path, self.normal_path)
