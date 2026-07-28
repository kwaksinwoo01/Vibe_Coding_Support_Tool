from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re

from .runtime_paths import config_directory, decode_text_file


SELF_COMPANY_KEYWORDS = ("에아스텍", "ERSTEQ")
_IGNORED_LINE_PREFIX = "#"
_SEPARATOR_RE = re.compile(r"[\s\W_]+", re.UNICODE)


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


def normalize_correspondents(values: Iterable[str]) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned.startswith(_IGNORED_LINE_PREFIX):
            continue

        key = _match_key(cleaned)
        if not key or key in seen or _is_self_company(cleaned):
            continue

        output.append(cleaned)
        seen.add(key)

    return tuple(output)


def load_correspondents(path: Path | None = None) -> tuple[str, ...]:
    active_path = path or correspondent_path()
    if not active_path.exists():
        return ()
    return normalize_correspondents(decode_text_file(active_path).splitlines())


def resolve_correspondent(
    texts: str | Iterable[str],
    correspondents: tuple[str, ...] | None = None,
) -> str:
    active = correspondents if correspondents is not None else load_correspondents()
    if not active:
        return ""

    sources = (texts,) if isinstance(texts, str) else tuple(texts)
    best: tuple[int, int, str] | None = None

    for source_index, source in enumerate(sources):
        normalized_source = _match_key(source)
        if not normalized_source:
            continue

        for config_index, candidate in enumerate(active):
            position = normalized_source.find(_match_key(candidate))
            if position < 0:
                continue

            match = (source_index, position, candidate)
            if best is None or match[:2] < best[:2]:
                best = (source_index, position, candidate)

    return best[2] if best else ""
