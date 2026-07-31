from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import MergeConflict, MergePlan, TemplateSnapshot

_MISSING = object()


def _properties(snapshot: TemplateSnapshot, style_name: str) -> dict[str, Any]:
    style = snapshot.styles.get(style_name)
    return {} if style is None else style.properties


def three_way_merge(
    baseline: TemplateSnapshot,
    normal: TemplateSnapshot,
    document: TemplateSnapshot,
) -> MergePlan:
    """Merge style properties with Git-like three-way semantics.

    Baseline is the last accepted state, normal is the current Normal.dotm, and
    document is the incoming Word document/template. A conflict exists only
    when both sides changed the same property differently from baseline.
    """

    plan = MergePlan(
        baseline_sha256=baseline.sha256,
        normal_sha256=normal.sha256,
        document_sha256=document.sha256,
    )

    style_names = sorted(
        set(baseline.styles) | set(normal.styles) | set(document.styles)
    )

    for style_name in style_names:
        base_style = baseline.styles.get(style_name)
        local_style = normal.styles.get(style_name)
        incoming_style = document.styles.get(style_name)

        if base_style is None and local_style is None and incoming_style is not None:
            plan.added_styles.append(style_name)
        elif base_style is not None and local_style is None and incoming_style is None:
            plan.removed_styles.append(style_name)

        property_names = sorted(
            set(_properties(baseline, style_name))
            | set(_properties(normal, style_name))
            | set(_properties(document, style_name))
        )

        for property_name in property_names:
            base_value = _properties(baseline, style_name).get(
                property_name, _MISSING
            )
            normal_value = _properties(normal, style_name).get(
                property_name, _MISSING
            )
            document_value = _properties(document, style_name).get(
                property_name, _MISSING
            )

            if normal_value == document_value:
                chosen = normal_value
            elif normal_value == base_value:
                chosen = document_value
            elif document_value == base_value:
                chosen = normal_value
            else:
                plan.conflicts.append(
                    MergeConflict(
                        style_name=style_name,
                        property_name=property_name,
                        baseline_value=None if base_value is _MISSING else base_value,
                        normal_value=None if normal_value is _MISSING else normal_value,
                        document_value=(
                            None if document_value is _MISSING else document_value
                        ),
                    )
                )
                continue

            if chosen is not _MISSING:
                plan.automatic_values.setdefault(style_name, {})[
                    property_name
                ] = deepcopy(chosen)

    return plan


def changed_properties(
    before: TemplateSnapshot,
    after: TemplateSnapshot,
) -> dict[str, dict[str, tuple[Any, Any]]]:
    changes: dict[str, dict[str, tuple[Any, Any]]] = {}
    for style_name in sorted(set(before.styles) | set(after.styles)):
        before_values = _properties(before, style_name)
        after_values = _properties(after, style_name)
        for property_name in sorted(set(before_values) | set(after_values)):
            old = before_values.get(property_name, _MISSING)
            new = after_values.get(property_name, _MISSING)
            if old != new:
                changes.setdefault(style_name, {})[property_name] = (
                    None if old is _MISSING else old,
                    None if new is _MISSING else new,
                )
    return changes
