import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "readiness", Path(__file__).parents[2] / "scripts/check_reconstruction_readiness.py"
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_missing_evidence_reports_all_gaps(tmp_path):
    result = m.check(tmp_path, {"evidence": []}, "full_training")
    assert not result["ready"]
    assert {"G0", "G1", "G2", "G3"} <= {gap["gate"] for gap in result["gaps"]}


def test_forged_completed_is_not_enough(tmp_path):
    (tmp_path / "evidence.json").write_text(json.dumps({"status": "completed"}))
    result = m.check(
        tmp_path,
        {"evidence": [{"kind": "data_integrity", "path": "evidence.json"}]},
        "data_preparation",
    )
    assert not result["ready"]
    assert any("SHA" in gap["reason"] for gap in result["gaps"])


def test_valid_machine_gate_does_not_clear_human_gates(tmp_path):
    payload = {
        "status": "completed",
        "coverage": {"expected": 20, "completed": 20, "missing": 0, "extra": 0, "duplicate": 0},
        "artifacts": [],
    }
    data = json.dumps(payload).encode()
    (tmp_path / "evidence.json").write_bytes(data)
    reference = {
        "kind": "data_integrity",
        "path": "evidence.json",
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    assert m.check(tmp_path, {"evidence": [reference]}, "data_preparation")["ready"]
    result = m.check(tmp_path, {"evidence": [reference]}, "full_training")
    assert not result["ready"]
    assert any(g["kind"] == "model_smoke" for g in result["gaps"])
    assert any(g["kind"] == "research_space" for g in result["gaps"])


def test_human_gate_cannot_be_self_attested(tmp_path):
    payload = {
        "status": "completed",
        "coverage": {"expected": 1, "completed": 1, "missing": 0, "extra": 0, "duplicate": 0},
        "artifacts": [],
        "approved": True,
    }
    data = json.dumps(payload).encode()
    (tmp_path / "human.json").write_bytes(data)
    result = m.check(
        tmp_path,
        {
            "evidence": [
                {
                    "kind": "coordinate_audit",
                    "path": "human.json",
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ]
        },
        "diagnostic_inference",
    )
    assert not result["ready"]
    assert any(g["kind"] == "coordinate_audit" for g in result["gaps"])


def test_reject_outside(tmp_path):
    with pytest.raises(ValueError):
        m.check(
            tmp_path,
            {"evidence": [{"kind": "data_integrity", "path": "../x", "sha256": "a" * 64}]},
            "data_preparation",
        )
