from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from cptla.evaluation.contracts import CoverageReport, PredictionRecord, RunManifest


def test_coverage_is_incomplete_when_prediction_is_missing() -> None:
    report = CoverageReport.from_ids(["a", "b"], ["a"])

    assert report.expected == 2
    assert report.seen == 1
    assert report.missing == ["b"]
    assert report.extra == []
    assert report.duplicates == []
    assert report.is_complete is False


def test_coverage_reports_sorted_extra_and_duplicate_ids() -> None:
    report = CoverageReport.from_ids(["b", "a"], ["c", "a", "c", "a"])

    assert report.missing == ["b"]
    assert report.extra == ["c"]
    assert report.duplicates == ["a", "c"]


def test_prediction_requires_error_message_for_error_status() -> None:
    with pytest.raises(ValidationError, match="error is required"):
        PredictionRecord(
            image_id="a.jpg",
            unit_id="a",
            status="error",
            tables_html=[],
            elapsed_sec=1,
        )


def test_prediction_rejects_error_message_for_ok_status() -> None:
    with pytest.raises(ValidationError, match="error must be empty"):
        PredictionRecord(
            image_id="a.jpg",
            unit_id="a",
            status="ok",
            tables_html=["<table></table>"],
            elapsed_sec=1,
            error="unexpected",
        )


def _manifest(tmp_path: Path, **overrides: object) -> RunManifest:
    values: dict[str, object] = {
        "run_id": "20260921T120000Z-tatr-cropped-val",
        "created_at_utc": datetime(2026, 9, 21, 12, tzinfo=UTC),
        "git_commit": "1" * 40,
        "dataset_name": "kensho/PubTables-v2",
        "dataset_split": "val",
        "dataset_revision": "a" * 40,
        "input_manifest_path": Path("input.jsonl"),
        "input_manifest_sha256": "b" * 64,
        "model_name": "tatr-v1.1-pub",
        "model_repo_id": "microsoft/table-transformer-structure-recognition-v1.1-pub",
        "model_revision": "c" * 40,
        "input_track": "pdf-text-assisted",
        "python_version": "3.12.7",
        "pytorch_version": "2.5.1",
        "transformers_version": "4.49.0",
        "cuda_version": "12.4",
        "grits_revision": "d" * 40,
        "gpu_model": "NVIDIA A100-SXM4-80GB",
        "visible_devices": ["0"],
        "command": ["python", "scripts/evaluate_tatr_pubtables_v2.py"],
        "seed": 20260724,
        "predictions_path": Path("predictions.jsonl"),
        "logs_path": Path("run.log"),
        "metrics_path": Path("metrics.json"),
        "coverage": {"expected": 1, "seen": 1, "failed": 0},
    }
    values.update(overrides)
    return RunManifest.model_validate(values)


def test_run_manifest_validates_artifact_paths(tmp_path: Path) -> None:
    for name in ("input.jsonl", "predictions.jsonl", "run.log", "metrics.json"):
        (tmp_path / name).write_text("", encoding="utf-8")

    assert _manifest(tmp_path).validate_manifest_paths(tmp_path) == []


def test_run_manifest_reports_missing_artifact_paths_in_sorted_order(tmp_path: Path) -> None:
    assert _manifest(tmp_path).validate_manifest_paths(tmp_path) == [
        tmp_path / "input.jsonl",
        tmp_path / "metrics.json",
        tmp_path / "predictions.jsonl",
        tmp_path / "run.log",
    ]
