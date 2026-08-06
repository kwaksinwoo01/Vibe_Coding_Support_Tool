from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import zipfile
from xml.etree import ElementTree

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NAMESPACE}}}"


class OpenXmlStyleIndexError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OpenXmlStyleRecord:
    style_id: str
    display_name: str
    style_type: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class OpenXmlStyleDifference:
    changed: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def candidate_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.changed, *self.added, *self.removed)))


class OpenXmlStyleIndexReader:
    """Read style identities and fingerprints without starting Microsoft Word."""

    @staticmethod
    def _display_name(style: ElementTree.Element, style_id: str) -> str:
        name = style.find(f"{W}name")
        if name is None:
            return style_id
        return str(name.attrib.get(f"{W}val") or style_id)

    @staticmethod
    def _style_type(style: ElementTree.Element) -> str:
        raw = str(style.attrib.get(f"{W}type") or "unknown")
        return {
            "paragraph": "Paragraph",
            "character": "Character",
            "table": "Table",
            "numbering": "List",
        }.get(raw, raw)

    def read(self, path: Path) -> dict[str, OpenXmlStyleRecord]:
        target = path.expanduser().resolve()
        try:
            with zipfile.ZipFile(target, mode="r") as package:
                xml_bytes = package.read("word/styles.xml")
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            raise OpenXmlStyleIndexError(
                f"Open XML 스타일 인덱스를 읽지 못했습니다: {target}: {exc}"
            ) from exc
        try:
            root = ElementTree.fromstring(xml_bytes)
        except ElementTree.ParseError as exc:
            raise OpenXmlStyleIndexError(
                f"styles.xml을 해석하지 못했습니다: {target}: {exc}"
            ) from exc

        records: dict[str, OpenXmlStyleRecord] = {}
        for style in root.findall(f"{W}style"):
            style_id = str(style.attrib.get(f"{W}styleId") or "")
            if not style_id:
                continue
            display_name = self._display_name(style, style_id)
            canonical = ElementTree.tostring(
                style,
                encoding="utf-8",
                method="xml",
            )
            record = OpenXmlStyleRecord(
                style_id=style_id,
                display_name=display_name,
                style_type=self._style_type(style),
                content_sha256=hashlib.sha256(canonical).hexdigest(),
            )
            # Word COM uses the localized display name. Keep styleId as a
            # fallback only when the name is absent.
            records[display_name] = record
        return records

    def compare(self, before: Path, after: Path) -> OpenXmlStyleDifference:
        left = self.read(before)
        right = self.read(after)
        left_names = set(left)
        right_names = set(right)
        changed = sorted(
            name
            for name in left_names & right_names
            if left[name].content_sha256 != right[name].content_sha256
        )
        added = sorted(right_names - left_names, key=str.casefold)
        removed = sorted(left_names - right_names, key=str.casefold)
        return OpenXmlStyleDifference(
            changed=tuple(changed),
            added=tuple(added),
            removed=tuple(removed),
        )
