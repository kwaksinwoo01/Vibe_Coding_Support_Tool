from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from word_editor.domain.diff import three_way_merge
from word_editor.domain.models import MergePlan, StyleDefinition, TemplateSnapshot
from word_editor.infrastructure.openxml_style_index import (
    OpenXmlStyleIndexError,
    OpenXmlStyleIndexReader,
)
from word_editor.infrastructure.word_style_sdk import WordStyleSdkGateway


class FastStyleCompareService:
    """Compare only styles whose Open XML definitions differ."""

    def __init__(self, gateway: WordStyleSdkGateway) -> None:
        self.gateway = gateway
        self.reader = OpenXmlStyleIndexReader()

    @staticmethod
    def _snapshot(
        path: Path,
        styles: dict[str, StyleDefinition],
        label: str,
    ) -> TemplateSnapshot:
        return TemplateSnapshot(
            source_path=str(path),
            sha256=label,
            captured_at=datetime.now(timezone.utc).isoformat(),
            word_version="OpenXML+COM",
            styles=styles,
            list_templates={},
            metadata={"comparison_mode": "openxml-candidates"},
        )

    def compare(
        self,
        target_path: Path,
        incoming_path: Path,
    ) -> MergePlan:
        difference = self.reader.compare(target_path, incoming_path)
        target_names = list((*difference.changed, *difference.removed))
        incoming_names = list((*difference.changed, *difference.added))
        target_details = self.gateway.read_style_details(
            target_path,
            target_names,
        )
        incoming_details = self.gateway.read_style_details(
            incoming_path,
            incoming_names,
        )

        baseline = self._snapshot(
            target_path,
            deepcopy(target_details),
            "fast-baseline",
        )
        target = self._snapshot(
            target_path,
            target_details,
            "fast-target",
        )
        incoming = self._snapshot(
            incoming_path,
            incoming_details,
            "fast-incoming",
        )
        plan = three_way_merge(baseline, target, incoming)
        plan.added_styles = sorted(
            {
                definition.name
                for definition in incoming_details.values()
                if definition.name not in target_details
            },
            key=str.casefold,
        )
        plan.removed_styles = sorted(
            {
                definition.name
                for definition in target_details.values()
                if definition.name not in incoming_details
            },
            key=str.casefold,
        )
        plan.added_style_definitions = {
            definition.name: definition
            for definition in incoming_details.values()
            if definition.name in plan.added_styles
        }
        return plan

    def compare_or_none(
        self,
        target_path: Path,
        incoming_path: Path,
    ) -> MergePlan | None:
        try:
            return self.compare(target_path, incoming_path)
        except OpenXmlStyleIndexError:
            return None
