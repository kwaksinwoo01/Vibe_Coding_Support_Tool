from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re

from .runtime_paths import config_directory, decode_text_file


SELF_COMPANY_KEYWORDS = ("에아스텍", "ERSTEQ")
_IGNORED_LINE_PREFIX = "#"
_MAPPING_SEPARATOR = "=>"
_ALIAS_SEPARATOR = "|"
_SEPARATOR_RE = re.compile(r"[\s\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class CorrespondentRule:
    display_name: str
    match_terms: tuple[str, ...]


def correspondent_path() -> Path:
    return config_directory() / "correspondent.txt"


def ensure_correspondent_file() -> Path:
    path = correspondent_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8-sig")
    return path


def _match_key(value: str) -> str:
    return _SEPARATOR_RE.sub("", value).casefold()


def _is_self_company(value: str) -> bool:
    key = _match_key(value)
    return any(_match_key(keyword) in key for keyword in SELF_COMPANY_KEYWORDS)


def _parse_rule(value: str) -> tuple[str, tuple[str, ...]] | None:
    if _MAPPING_SEPARATOR in value:
        raw_terms, raw_display_name = value.split(_MAPPING_SEPARATOR, 1)
        display_name = raw_display_name.strip()
        terms = tuple(part.strip() for part in raw_terms.split(_ALIAS_SEPARATOR))
    else:
        display_name = value
        terms = (value,)

    if not display_name or _is_self_company(display_name):
        return None

    filtered_terms = tuple(
        term
        for term in terms
        if term and _match_key(term) and not _is_self_company(term)
    )
    if not filtered_terms:
        return None
    return display_name, filtered_terms


def normalize_correspondents(values: Iterable[str]) -> tuple[CorrespondentRule, ...]:
    output: list[CorrespondentRule] = []
    display_indexes: dict[str, int] = {}
    seen_terms: set[str] = set()

    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned.startswith(_IGNORED_LINE_PREFIX):
            continue

        parsed = _parse_rule(cleaned)
        if parsed is None:
            continue
        display_name, terms = parsed

        new_terms: list[str] = []
        for term in terms:
            term_key = _match_key(term)
            if term_key in seen_terms:
                continue
            seen_terms.add(term_key)
            new_terms.append(term)
        if not new_terms:
            continue

        display_key = _match_key(display_name)
        existing_index = display_indexes.get(display_key)
        if existing_index is None:
            display_indexes[display_key] = len(output)
            output.append(CorrespondentRule(display_name, tuple(new_terms)))
        else:
            existing = output[existing_index]
            output[existing_index] = CorrespondentRule(
                existing.display_name,
                existing.match_terms + tuple(new_terms),
            )

    return tuple(output)


def load_correspondents(path: Path | None = None) -> tuple[CorrespondentRule, ...]:
    active_path = path or correspondent_path()
    if not active_path.exists():
        return ()
    return normalize_correspondents(decode_text_file(active_path).splitlines())


def resolve_correspondent(
    texts: str | Iterable[str],
    correspondents: tuple[CorrespondentRule, ...] | None = None,
) -> str:
    active = correspondents if correspondents is not None else load_correspondents()
    if not active:
        return ""

    sources = (texts,) if isinstance(texts, str) else tuple(texts)
    best: tuple[int, int, int, str] | None = None

    for source_index, source in enumerate(sources):
        normalized_source = _match_key(source)
        if not normalized_source:
            continue

        for config_index, rule in enumerate(active):
            for term in rule.match_terms:
                position = normalized_source.find(_match_key(term))
                if position < 0:
                    continue

                match = (source_index, position, config_index, rule.display_name)
                if best is None or match[:3] < best[:3]:
                    best = match

    return best[3] if best else ""
