from __future__ import annotations

from pathlib import Path

from renamer_document_classifier.ocr_scheduler import (
    OcrSchedulerConfig,
    ensure_scheduler_file,
    load_scheduler_config,
)


def test_scheduler_config_loads_exact_resource_keys(tmp_path: Path) -> None:
    path = tmp_path / "ocr_scheduler.ini"
    path.write_text(
        "[ocr.scheduler]\n"
        "cpu_workers = 12\n"
        "gpu_workers = 2\n"
        "max_documents_in_flight = 3\n"
        "max_attempts_per_document = 7\n"
        "memory_budget_mb = 4096\n"
        "batch_size = 4\n",
        encoding="utf-8-sig",
    )

    config = load_scheduler_config(path)

    assert config == OcrSchedulerConfig(
        cpu_workers=12,
        gpu_workers=2,
        max_documents_in_flight=3,
        max_attempts_per_document=7,
        memory_budget_mb=4096,
        batch_size=4,
    )


def test_scheduler_memory_budget_limits_parallel_attempts() -> None:
    config = OcrSchedulerConfig(
        cpu_workers=16,
        gpu_workers=1,
        max_documents_in_flight=2,
        max_attempts_per_document=6,
        memory_budget_mb=256,
        batch_size=2,
    )

    assert config.max_parallel_attempts(dpi=300, page_count=2) == 1


def test_ensure_scheduler_file_does_not_overwrite_user_values(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config" / "ocr_scheduler.ini"
    path.parent.mkdir(parents=True)
    path.write_text("user-owned", encoding="utf-8")

    from unittest.mock import patch

    with patch(
        "renamer_document_classifier.ocr_scheduler.scheduler_path",
        return_value=path,
    ):
        ensured = ensure_scheduler_file()

    assert ensured == path
    assert path.read_text(encoding="utf-8") == "user-owned"

