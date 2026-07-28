from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

from .correspondent_config import (
    CorrespondentRule,
    _match_key,
    correspondent_path,
    load_correspondents,
)
from .runtime_paths import config_directory


STATE_SCHEMA_VERSION = 1
APPLIED_DEFAULTS_FILENAME = "correspondent.defaults.applied.txt"
STATE_FILENAME = "correspondent.defaults.state.json"
BACKUP_DIRECTORY_NAME = "correspondent-backups"


@dataclass(frozen=True, slots=True)
class CorrespondentSyncResult:
    changed: bool
    mode: str
    rule_count: int
    defaults_sha256: str
    backup_path: Path | None


@dataclass(frozen=True, slots=True)
class _SourceRule:
    source: str
    index: int
    rule: CorrespondentRule


def _rule_keys(rule: CorrespondentRule) -> set[str]:
    return {_match_key(term) for term in rule.match_terms}


def _rules_overlap(left: _SourceRule, right: _SourceRule) -> bool:
    if left.source == right.source:
        return False
    if _match_key(left.rule.display_name) == _match_key(right.rule.display_name):
        return True
    return bool(_rule_keys(left.rule) & _rule_keys(right.rule))


def _components(
    previous: tuple[CorrespondentRule, ...],
    local: tuple[CorrespondentRule, ...],
    incoming: tuple[CorrespondentRule, ...],
) -> list[list[_SourceRule]]:
    entries = [
        *(_SourceRule("previous", index, rule) for index, rule in enumerate(previous)),
        *(_SourceRule("local", index, rule) for index, rule in enumerate(local)),
        *(_SourceRule("incoming", index, rule) for index, rule in enumerate(incoming)),
    ]
    parents = list(range(len(entries)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left_index, left in enumerate(entries):
        for right_index in range(left_index + 1, len(entries)):
            if _rules_overlap(left, entries[right_index]):
                union(left_index, right_index)

    grouped: dict[int, list[_SourceRule]] = {}
    for index, entry in enumerate(entries):
        grouped.setdefault(find(index), []).append(entry)

    def component_order(component: list[_SourceRule]) -> tuple[int, int, int]:
        missing = 1_000_000
        local_index = min(
            (entry.index for entry in component if entry.source == "local"),
            default=missing,
        )
        incoming_index = min(
            (entry.index for entry in component if entry.source == "incoming"),
            default=missing,
        )
        previous_index = min(
            (entry.index for entry in component if entry.source == "previous"),
            default=missing,
        )
        return local_index, incoming_index, previous_index

    return sorted(grouped.values(), key=component_order)


def _source_rules(
    component: list[_SourceRule],
    source: str,
) -> list[CorrespondentRule]:
    return [
        entry.rule
        for entry in sorted(component, key=lambda item: item.index)
        if entry.source == source
    ]


def _terms(rules: list[CorrespondentRule]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for rule in rules:
        for term in rule.match_terms:
            key = _match_key(term)
            if key not in seen:
                seen.add(key)
                output.append(term)
    return output


def _select_display_name(
    previous: list[CorrespondentRule],
    local: list[CorrespondentRule],
    incoming: list[CorrespondentRule],
) -> str:
    previous_display = previous[0].display_name if previous else ""
    local_display = local[0].display_name if local else ""
    incoming_display = incoming[0].display_name if incoming else ""

    if local_display and (
        not previous_display
        or _match_key(local_display) != _match_key(previous_display)
    ):
        return local_display
    if incoming_display:
        return incoming_display
    return local_display or previous_display


def merge_correspondent_rules(
    previous: tuple[CorrespondentRule, ...],
    local: tuple[CorrespondentRule, ...],
    incoming: tuple[CorrespondentRule, ...],
) -> tuple[CorrespondentRule, ...]:
    """Three-way merge packaged defaults without discarding local edits."""

    output: list[CorrespondentRule] = []
    for component in _components(previous, local, incoming):
        previous_rules = _source_rules(component, "previous")
        local_rules = _source_rules(component, "local")
        incoming_rules = _source_rules(component, "incoming")

        # Deleting a previously managed rule from the local file is a user edit.
        if previous_rules and not local_rules:
            continue

        previous_terms = _terms(previous_rules)
        local_terms = _terms(local_rules)
        incoming_terms = _terms(incoming_rules)
        previous_keys = {_match_key(term) for term in previous_terms}
        local_keys = {_match_key(term) for term in local_terms}
        incoming_keys = {_match_key(term) for term in incoming_terms}

        removed_by_patch = previous_keys - incoming_keys
        removed_by_user = previous_keys - local_keys

        merged_terms = [
            term
            for term in local_terms
            if _match_key(term) not in removed_by_patch
        ]
        merged_keys = {_match_key(term) for term in merged_terms}
        for term in incoming_terms:
            key = _match_key(term)
            if key in merged_keys or key in removed_by_user:
                continue
            merged_terms.append(term)
            merged_keys.add(key)

        if not merged_terms:
            continue

        display_name = _select_display_name(
            previous_rules,
            local_rules,
            incoming_rules,
        )
        if display_name:
            output.append(CorrespondentRule(display_name, tuple(merged_terms)))

    return tuple(output)


def format_correspondent_rule(rule: CorrespondentRule) -> str:
    if (
        len(rule.match_terms) == 1
        and _match_key(rule.match_terms[0]) == _match_key(rule.display_name)
    ):
        return rule.display_name
    return f"{' | '.join(rule.match_terms)} => {rule.display_name}"


def serialize_correspondents(rules: tuple[CorrespondentRule, ...]) -> str:
    if not rules:
        return ""
    return "\n".join(format_correspondent_rule(rule) for rule in rules) + "\n"


def _atomic_write_text(path: Path, text: str, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(text, encoding=encoding)
        for attempt in range(5):
            try:
                os.replace(temporary_path, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _backup_local_file(path: Path) -> Path | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    backup_directory = config_directory() / BACKUP_DIRECTORY_NAME
    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_directory / f"correspondent.{timestamp}.txt"
    shutil.copy2(path, backup_path)
    return backup_path


def _canonical_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest().upper()


def _load_verified_previous_defaults(
    applied_defaults_path: Path,
    state_path: Path,
) -> tuple[CorrespondentRule, ...]:
    if not applied_defaults_path.is_file() or not state_path.is_file():
        return ()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        expected_hash = str(state["defaults_sha256"]).upper()
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        return ()

    previous = load_correspondents(applied_defaults_path)
    if _canonical_hash(serialize_correspondents(previous)) != expected_hash:
        return ()
    return previous


def sync_correspondent_defaults(
    defaults_path: Path,
    *,
    release_version: str,
    local_path: Path | None = None,
) -> CorrespondentSyncResult:
    if not defaults_path.is_file():
        raise FileNotFoundError(f"Correspondent defaults not found: {defaults_path}")

    incoming = load_correspondents(defaults_path)
    if not incoming:
        raise ValueError(f"Correspondent defaults have no usable rules: {defaults_path}")

    active_local_path = local_path or correspondent_path()
    active_local_path.parent.mkdir(parents=True, exist_ok=True)
    local = load_correspondents(active_local_path)

    applied_defaults_path = config_directory() / APPLIED_DEFAULTS_FILENAME
    state_path = config_directory() / STATE_FILENAME
    previous = _load_verified_previous_defaults(applied_defaults_path, state_path)
    incoming_text = serialize_correspondents(incoming)
    defaults_hash = _canonical_hash(incoming_text)

    if previous:
        mode = "three-way"
        merged = merge_correspondent_rules(previous, local, incoming)
    elif local:
        mode = "legacy-union"
        merged = merge_correspondent_rules((), local, incoming)
    else:
        mode = "initial"
        merged = incoming

    changed = merged != local or not active_local_path.exists()
    backup_path = None
    if changed:
        backup_path = _backup_local_file(active_local_path)
        _atomic_write_text(
            active_local_path,
            serialize_correspondents(merged),
            encoding="utf-8-sig",
        )

    _atomic_write_text(
        applied_defaults_path,
        incoming_text,
        encoding="utf-8-sig",
    )
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "release_version": release_version,
        "defaults_sha256": defaults_hash,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write_text(
        state_path,
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return CorrespondentSyncResult(
        changed=changed,
        mode=mode,
        rule_count=len(merged),
        defaults_sha256=defaults_hash,
        backup_path=backup_path,
    )
