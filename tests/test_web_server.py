from pathlib import Path

import pytest

from poker_hand_review.web_server import (
    WebServerConfig,
    _cache_path,
    _solve_target_path,
    analyze_data_payload,
    list_data_files_payload,
)


def _config(root: Path, report_path: Path | None = None) -> WebServerConfig:
    return WebServerConfig(root, report_path, None, 120)


def test_analyze_data_payload_returns_one_report_per_file(tmp_path: Path) -> None:
    root = tmp_path
    data_dir = root / "data"
    data_dir.mkdir()
    sample = Path("data/sample.txt").read_text(encoding="utf-8")
    (data_dir / "first.txt").write_text(sample, encoding="utf-8")
    (data_dir / "second.txt").write_text(sample, encoding="utf-8")

    result = analyze_data_payload({"postflop": "equity"}, _config(root))

    reports = result["reports"]
    assert [report["hands"][0]["source_file"] for report in reports] == ["first.txt", "second.txt"]
    assert [len(report["hands"]) for report in reports] == [2, 2]
    assert all(report["from_cache"] is False for report in reports)


def test_list_data_files_payload_lists_project_data_txt_files(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "b.txt").write_text("Poker Hand #B", encoding="utf-8")
    (data_dir / "a.txt").write_text("Poker Hand #A", encoding="utf-8")
    (data_dir / "ignore.json").write_text("{}", encoding="utf-8")

    result = list_data_files_payload(_config(tmp_path))

    assert result["files"] == [
        {"name": "a.txt", "size": 13, "hand_count": 1},
        {"name": "b.txt", "size": 13, "hand_count": 1},
    ]


def test_analyze_data_payload_reads_selected_data_files_only(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sample = Path("data/sample.txt").read_text(encoding="utf-8")
    (data_dir / "selected.txt").write_text(sample, encoding="utf-8")
    (data_dir / "other.txt").write_text(sample, encoding="utf-8")

    result = analyze_data_payload(
        {"postflop": "equity", "files": ["selected.txt"]},
        _config(tmp_path),
    )

    reports = result["reports"]
    assert len(reports) == 1
    assert {hand["source_file"] for hand in reports[0]["hands"]} == {"selected.txt"}


def test_analyze_data_payload_reuses_cache_until_source_changes(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sample = Path("data/sample.txt").read_text(encoding="utf-8")
    target = data_dir / "hand.txt"
    target.write_text(sample, encoding="utf-8")
    config = _config(tmp_path)

    first = analyze_data_payload({"postflop": "equity"}, config)
    assert first["reports"][0]["from_cache"] is False
    assert _cache_path(config, "hand.txt").exists()

    # Second analysis of the unchanged file is served straight from cache.
    second = analyze_data_payload({"postflop": "equity"}, config)
    assert second["reports"][0]["from_cache"] is True

    # refresh=True forces a re-analysis even when the cache is valid.
    refreshed = analyze_data_payload({"postflop": "equity", "refresh": True}, config)
    assert refreshed["reports"][0]["from_cache"] is False

    # Editing the file invalidates the cache by content hash.
    target.write_text(sample + sample, encoding="utf-8")
    changed = analyze_data_payload({"postflop": "equity"}, config)
    assert changed["reports"][0]["from_cache"] is False


def test_solve_target_path_prefers_source_file_cache(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    config = _config(tmp_path, report_path)

    # No cache file yet: fall back to the --report path.
    assert _solve_target_path({"source_file": "hand.txt"}, config) == report_path

    cache_file = _cache_path(config, "hand.txt")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{}", encoding="utf-8")

    # Once the per-file cache exists, solver results target it.
    assert _solve_target_path({"source_file": "hand.txt"}, config) == cache_file
    # Without a source_file the --report path is still used.
    assert _solve_target_path({}, config) == report_path


def test_analyze_data_payload_rejects_data_file_path_traversal(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()

    with pytest.raises(ValueError, match="invalid data file"):
        analyze_data_payload({"files": ["../outside.txt"]}, _config(tmp_path))


def test_analyze_data_payload_rejects_empty_data_folder(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()

    with pytest.raises(ValueError, match="data 資料夾沒有 .txt"):
        analyze_data_payload({}, _config(tmp_path))
