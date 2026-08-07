from __future__ import annotations

import json
from pathlib import Path

from renamer_document_classifier.correspondent_config import correspondent_path
from renamer_document_classifier.correspondent_sync import (
    APPLIED_DEFAULTS_FILENAME,
    BACKUP_DIRECTORY_NAME,
    STATE_FILENAME,
    sync_correspondent_defaults,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")
    return path


def test_legacy_upgrade_unions_new_defaults_with_local_aliases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(runtime))
    local = _write(
        correspondent_path(),
        "써모피서사이언티픽 | 모피셔사이언티픽 | Thermo | ThermoFisher "
        "=> ThermoFisher Scientific\n",
    )
    defaults = _write(
        tmp_path / "defaults-v1.txt",
        "써모피서사이언티픽 | 모피셔사이언티픽 | thermofisher.com "
        "=> ThermoFisher\n",
    )

    result = sync_correspondent_defaults(
        defaults,
        release_version="7.4.2",
    )

    assert result.changed is True
    assert result.mode == "legacy-union"
    assert local.read_text(encoding="utf-8-sig") == (
        "써모피서사이언티픽 | 모피셔사이언티픽 | Thermo | ThermoFisher | "
        "thermofisher.com => ThermoFisher Scientific\n"
    )
    assert result.backup_path is not None
    assert result.backup_path.parent.name == BACKUP_DIRECTORY_NAME
    assert "thermofisher.com" not in result.backup_path.read_text(
        encoding="utf-8-sig"
    )

    config = runtime / "config"
    assert (config / APPLIED_DEFAULTS_FILENAME).is_file()
    state = json.loads((config / STATE_FILENAME).read_text(encoding="utf-8"))
    assert state["release_version"] == "7.4.2"
    assert state["defaults_sha256"] == result.defaults_sha256


def test_legacy_upgrade_adds_defaults_missing_from_local_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(runtime))
    local = _write(correspondent_path(), "에이티지코리아\n")
    defaults = _write(
        tmp_path / "defaults-v1.txt",
        "써모피서사이언티픽 => ThermoFisher Scientific\n"
        "닥터바이오\n"
        "에이티지코리아\n",
    )

    result = sync_correspondent_defaults(defaults, release_version="7.4.2")

    assert result.changed is True
    assert local.read_text(encoding="utf-8-sig") == (
        "에이티지코리아\n"
        "써모피서사이언티픽 => ThermoFisher Scientific\n"
        "닥터바이오\n"
    )


def test_followup_patch_removes_managed_alias_but_keeps_local_aliases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(runtime))
    local = _write(
        correspondent_path(),
        "써모피서사이언티픽 | 모피셔사이언티픽 | Thermo | ThermoFisher "
        "=> ThermoFisher Scientific\n",
    )
    first_defaults = _write(
        tmp_path / "defaults-v1.txt",
        "써모피서사이언티픽 | 모피셔사이언티픽 | thermofisher.com "
        "=> ThermoFisher\n",
    )
    sync_correspondent_defaults(first_defaults, release_version="7.4.2")

    second_defaults = _write(
        tmp_path / "defaults-v2.txt",
        "써모피서사이언티픽 | 모피셔사이언티픽 => ThermoFisher\n",
    )
    result = sync_correspondent_defaults(
        second_defaults,
        release_version="7.4.2",
    )

    assert result.mode == "three-way"
    assert local.read_text(encoding="utf-8-sig") == (
        "써모피서사이언티픽 | 모피셔사이언티픽 | Thermo | ThermoFisher "
        "=> ThermoFisher Scientific\n"
    )


def test_user_alias_deletion_is_not_reintroduced_by_later_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(runtime))
    first_defaults = _write(
        tmp_path / "defaults-v1.txt",
        "공급사A | 공급사B => 공급사\n",
    )
    sync_correspondent_defaults(first_defaults, release_version="7.4.2")

    local = _write(
        correspondent_path(),
        "공급사A | 사용자별칭 => 공급사\n",
    )
    second_defaults = _write(
        tmp_path / "defaults-v2.txt",
        "공급사A | 공급사B | 공급사C => 공급사\n",
    )
    sync_correspondent_defaults(second_defaults, release_version="7.4.2")

    assert local.read_text(encoding="utf-8-sig") == (
        "공급사A | 사용자별칭 | 공급사C => 공급사\n"
    )


def test_patch_updates_unmodified_display_and_preserves_deleted_rule(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(runtime))
    first_defaults = _write(
        tmp_path / "defaults-v1.txt",
        "공급사A => 이전표시\n삭제대상\n",
    )
    sync_correspondent_defaults(first_defaults, release_version="7.4.2")

    local = _write(correspondent_path(), "공급사A => 이전표시\n")
    second_defaults = _write(
        tmp_path / "defaults-v2.txt",
        "공급사A => 신규표시\n삭제대상 | 새별칭 => 삭제대상\n",
    )
    sync_correspondent_defaults(second_defaults, release_version="7.4.2")

    assert local.read_text(encoding="utf-8-sig") == "공급사A => 신규표시\n"


def test_tampered_previous_snapshot_falls_back_to_non_destructive_union(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("RENAMER_CLASSIFIER_ROOT", str(runtime))
    first_defaults = _write(
        tmp_path / "defaults-v1.txt",
        "공급사A | 공급사B => 공급사\n",
    )
    sync_correspondent_defaults(first_defaults, release_version="7.4.2")

    local = _write(
        correspondent_path(),
        "공급사A | 공급사B | 사용자별칭 => 공급사\n",
    )
    _write(
        runtime / "config" / APPLIED_DEFAULTS_FILENAME,
        "공급사A | 공급사B | 손상된기준 => 공급사\n",
    )
    second_defaults = _write(
        tmp_path / "defaults-v2.txt",
        "공급사A => 공급사\n",
    )

    result = sync_correspondent_defaults(
        second_defaults,
        release_version="7.4.2",
    )

    assert result.mode == "legacy-union"
    assert local.read_text(encoding="utf-8-sig") == (
        "공급사A | 공급사B | 사용자별칭 => 공급사\n"
    )
