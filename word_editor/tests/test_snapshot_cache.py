import os
from pathlib import Path

from word_editor.domain.models import TemplateSnapshot
from word_editor.infrastructure.snapshot_cache import SnapshotCache


def make_snapshot(path: Path) -> TemplateSnapshot:
    return TemplateSnapshot(
        source_path=str(path),
        sha256="snapshot",
        captured_at="now",
        word_version="16",
    )


def test_cache_loads_only_unchanged_file(tmp_path: Path) -> None:
    source = tmp_path / "Normal.dotm"
    source.write_bytes(b"first")
    cache = SnapshotCache(tmp_path / "cache")
    cache.save(source, "index", make_snapshot(source))

    loaded = cache.load(source, "index")
    assert loaded is not None
    assert loaded.sha256 == "snapshot"

    source.write_bytes(b"changed-size")
    assert cache.load(source, "index") is None


def test_cache_rejects_same_size_and_timestamp_with_different_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Normal.dotm"
    source.write_bytes(b"DCM1")
    original_stat = source.stat()
    cache = SnapshotCache(tmp_path / "cache")
    cache.save(source, "index", make_snapshot(source))

    source.write_bytes(b"FDM2")
    os.utime(
        source,
        ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
    )

    assert source.stat().st_size == original_stat.st_size
    assert source.stat().st_mtime_ns == original_stat.st_mtime_ns
    assert cache.load(source, "index") is None


def test_cache_invalidate_removes_all_modes(tmp_path: Path) -> None:
    source = tmp_path / "Normal.dotm"
    source.write_bytes(b"file")
    cache = SnapshotCache(tmp_path / "cache")
    snapshot = make_snapshot(source)
    cache.save(source, "index", snapshot)
    cache.save(source, "full", snapshot)

    cache.invalidate(source)

    assert cache.load(source, "index") is None
    assert cache.load(source, "full") is None
