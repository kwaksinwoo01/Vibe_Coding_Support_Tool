from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from renamer_document_classifier.ocr_scheduler import (
    OcrSchedulerConfig,
    SystemCapacity,
    ensure_scheduler_file,
    load_scheduler_config,
    recommended_scheduler_config,
    scheduler_profile_mode,
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


def test_recommended_profile_scales_to_detected_pc_capacity() -> None:
    config = recommended_scheduler_config(
        SystemCapacity(logical_processors=12, total_memory_mb=48 * 1024)
    )

    assert config == OcrSchedulerConfig(
        cpu_workers=10,
        gpu_workers=1,
        max_documents_in_flight=3,
        max_attempts_per_document=6,
        memory_budget_mb=12 * 1024,
        batch_size=2,
    )


def test_recommended_profile_is_conservative_on_low_memory_pc() -> None:
    config = recommended_scheduler_config(
        SystemCapacity(logical_processors=4, total_memory_mb=4 * 1024)
    )

    assert config == OcrSchedulerConfig(
        cpu_workers=3,
        gpu_workers=1,
        max_documents_in_flight=1,
        max_attempts_per_document=6,
        memory_budget_mb=1024,
        batch_size=1,
    )


def test_auto_values_resolve_from_current_hardware_recommendation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ocr_scheduler.ini"
    path.write_text(
        "[ocr.scheduler]\n"
        "profile_version = 2\n"
        "cpu_workers = auto\n"
        "gpu_workers = 0\n"
        "max_documents_in_flight = auto\n"
        "max_attempts_per_document = auto\n"
        "memory_budget_mb = 4096\n"
        "batch_size = auto\n",
        encoding="utf-8-sig",
    )
    detected = OcrSchedulerConfig(
        cpu_workers=10,
        gpu_workers=1,
        max_documents_in_flight=3,
        max_attempts_per_document=6,
        memory_budget_mb=12 * 1024,
        batch_size=2,
    )

    with patch(
        "renamer_document_classifier.ocr_scheduler.recommended_scheduler_config",
        return_value=detected,
    ):
        config = load_scheduler_config(path)

    assert config == OcrSchedulerConfig(
        cpu_workers=10,
        gpu_workers=0,
        max_documents_in_flight=3,
        max_attempts_per_document=6,
        memory_budget_mb=4096,
        batch_size=2,
    )
    assert scheduler_profile_mode(path) == "MIXED"


def test_ensure_scheduler_file_does_not_overwrite_user_values(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config" / "ocr_scheduler.ini"
    path.parent.mkdir(parents=True)
    path.write_text("user-owned", encoding="utf-8")

    with patch(
        "renamer_document_classifier.ocr_scheduler.scheduler_path",
        return_value=path,
    ):
        ensured = ensure_scheduler_file()

    assert ensured == path
    assert path.read_text(encoding="utf-8") == "user-owned"


def test_ensure_scheduler_file_creates_auto_profile(tmp_path: Path) -> None:
    path = tmp_path / "config" / "ocr_scheduler.ini"
    with (
        patch(
            "renamer_document_classifier.ocr_scheduler.scheduler_path",
            return_value=path,
        ),
        patch(
            "renamer_document_classifier.ocr_scheduler.detect_system_capacity",
            return_value=SystemCapacity(8, 16 * 1024),
        ),
    ):
        ensure_scheduler_file()

    contents = path.read_text(encoding="utf-8-sig")
    assert "profile_version = 2" in contents
    assert "detected_logical_processors = 8" in contents
    assert "detected_total_memory_mb = 16384" in contents
    assert contents.count("= auto") == 6
    assert scheduler_profile_mode(path) == "AUTO"


def test_legacy_generated_defaults_migrate_to_auto_with_backup(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config" / "ocr_scheduler.ini"
    path.parent.mkdir(parents=True)
    with patch(
        "renamer_document_classifier.ocr_scheduler._default_cpu_workers",
        return_value=6,
    ):
        path.write_text(
            "[ocr.scheduler]\n"
            "cpu_workers = 6\n"
            "gpu_workers = 1\n"
            "max_documents_in_flight = 2\n"
            "max_attempts_per_document = 6\n"
            "memory_budget_mb = 2048\n"
            "batch_size = 2\n",
            encoding="utf-8-sig",
        )
        with (
            patch(
                "renamer_document_classifier.ocr_scheduler.scheduler_path",
                return_value=path,
            ),
            patch(
                "renamer_document_classifier.ocr_scheduler.detect_system_capacity",
                return_value=SystemCapacity(12, 48 * 1024),
            ),
        ):
            ensure_scheduler_file()

    contents = path.read_text(encoding="utf-8-sig")
    assert "profile_version = 2" in contents
    assert "cpu_workers = auto" in contents
    assert path.with_suffix(".ini.legacy-default.bak").is_file()


def test_legacy_migration_preserves_only_values_changed_by_user(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config" / "ocr_scheduler.ini"
    path.parent.mkdir(parents=True)
    path.write_text(
        "[ocr.scheduler]\n"
        "cpu_workers = 6\n"
        "gpu_workers = 1\n"
        "max_documents_in_flight = 2\n"
        "max_attempts_per_document = 6\n"
        "memory_budget_mb = 8192\n"
        "batch_size = 2\n",
        encoding="utf-8-sig",
    )
    with (
        patch(
            "renamer_document_classifier.ocr_scheduler._default_cpu_workers",
            return_value=6,
        ),
        patch(
            "renamer_document_classifier.ocr_scheduler.scheduler_path",
            return_value=path,
        ),
        patch(
            "renamer_document_classifier.ocr_scheduler.detect_system_capacity",
            return_value=SystemCapacity(12, 48 * 1024),
        ),
    ):
        ensure_scheduler_file()

    contents = path.read_text(encoding="utf-8-sig")
    assert "cpu_workers = auto" in contents
    assert "max_documents_in_flight = auto" in contents
    assert "memory_budget_mb = 8192" in contents
