from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

import pywintypes

from word_editor.infrastructure.word_com import WordGatewayError
from word_editor.infrastructure.word_style_sdk import WordStyleSdkGateway


class SafeBackupStyleGateway(WordStyleSdkGateway):
    """Style SDK that can back up a file while Word owns the file handle."""

    def _make_target_backup(self, document, target: Path) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = self.backup_directory / (
            f"{target.stem}.{timestamp}.before-word-editor{target.suffix}"
        )
        errors: list[str] = []
        try:
            document.SaveCopyAs(str(destination))
        except (pywintypes.com_error, AttributeError) as exc:
            errors.append(f"Word SaveCopyAs: {exc}")
        if not destination.exists():
            try:
                shutil.copy2(target, destination)
            except OSError as exc:
                errors.append(f"파일 복사: {exc}")
        try:
            valid = destination.exists() and destination.stat().st_size > 0
        except OSError:
            valid = False
        if not valid:
            raise WordGatewayError(
                "수정 전 백업을 만들지 못해 작업을 중단했습니다.\n- "
                + "\n- ".join(errors or ["원인 정보 없음"])
            )
        return destination
