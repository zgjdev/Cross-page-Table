from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cptla.evaluation.provenance import build_run_manifest, credential_presence


def _spec() -> dict[str, object]:
    return {
        "run_id": "20260921T120000Z-dots-full-val",
        "dataset_name": "kensho/PubTables-v2",
        "dataset_split": "val",
        "dataset_revision": "a" * 40,
        "input_manifest_path": "artifacts/input-manifests/input.jsonl",
        "input_manifest_sha256": "b" * 64,
        "model_name": "dots-ocr",
        "model_repo_id": "rednote-hilab/dots.ocr",
        "model_revision": "c" * 40,
        "input_track": "image-only",
        "grits_revision": "d" * 40,
        "gpu_model": "NVIDIA A100-SXM4-80GB",
        "visible_devices": ["0"],
        "command": ["python", "scripts/evaluate_dotsocr_pubtables_v2.py"],
        "seed": 20260724,
        "predictions_path": "outputs/predictions.jsonl",
        "logs_path": "logs/run.log",
        "metrics_path": "outputs/metrics.json",
        "coverage": {"expected": 13871, "seen": 13871, "failed": 0},
    }


def test_build_run_manifest_adds_runtime_evidence() -> None:
    manifest = build_run_manifest(
        _spec(),
        git_commit="1" * 40,
        created_at=datetime(2026, 9, 21, 12, tzinfo=UTC),
        versions={
            "python": "3.12.7",
            "pytorch": "2.5.1",
            "transformers": "4.49.0",
            "cuda": "12.4",
        },
        credentials={"HF_TOKEN": True},
    )

    assert manifest.git_commit == "1" * 40
    assert manifest.credential_presence == {"HF_TOKEN": True}
    assert "secret-value" not in manifest.model_dump_json()


def test_build_run_manifest_rejects_missing_required_spec_field() -> None:
    spec = _spec()
    del spec["model_revision"]

    with pytest.raises(ValidationError):
        build_run_manifest(
            spec,
            git_commit="1" * 40,
            created_at=datetime(2026, 9, 21, 12, tzinfo=UTC),
            versions={
                "python": "3.12.7",
                "pytorch": "2.5.1",
                "transformers": "4.49.0",
                "cuda": "12.4",
            },
            credentials={},
        )


def test_credential_presence_records_only_boolean_state() -> None:
    assert credential_presence(["HF_TOKEN", "WANDB_API_KEY"], {"HF_TOKEN": "secret-value"}) == {
        "HF_TOKEN": True,
        "WANDB_API_KEY": False,
    }
