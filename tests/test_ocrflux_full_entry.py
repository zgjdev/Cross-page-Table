import importlib.util
import json
from pathlib import Path

import pytest

from cptla.evaluation.document_run import run_batch


def entry():
    spec = importlib.util.spec_from_file_location(
        "ocrflux_full", Path("scripts/run_ocrflux_document_full.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_child_requires_exact_page_and_document_coverage(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    (child / "summary.json").write_text(
        json.dumps(dict(status="completed", pages=1, documents=["PMC1"]))
    )
    (child / "PMC1.json").write_text(json.dumps(dict(document_id="PMC1", pages=[])))
    with pytest.raises(ValueError, match="coverage"):
        entry().validate_child(child, dict(document_id="PMC1", pages=1))


def test_resume_skips_gpu_worker_and_rejects_tampering(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    (child / "summary.json").write_text(
        json.dumps(dict(status="completed", pages=1, documents=["PMC1"]))
    )
    (child / "PMC1.json").write_text(json.dumps(dict(document_id="PMC1", pages=[{}])))
    doc = dict(document_id="PMC1", pages=1)
    result = entry().validate_child(child, doc)
    run_batch([doc], tmp_path / "first", {"seed": 0}, lambda _: result, project=tmp_path)

    def forbidden(_):
        raise AssertionError("GPU worker called")

    summary = run_batch(
        [doc],
        tmp_path / "second",
        {"seed": 0},
        forbidden,
        project=tmp_path,
        resume=[tmp_path / "first"],
    )
    assert summary["resumed_documents"] == 1
    with pytest.raises(ValueError, match="protocol"):
        run_batch(
            [doc],
            tmp_path / "third",
            {"seed": 1},
            forbidden,
            project=tmp_path,
            resume=[tmp_path / "first"],
        )
    (child / "PMC1.json").write_text("{}")
    with pytest.raises(ValueError, match="SHA"):
        run_batch(
            [doc],
            tmp_path / "fourth",
            {"seed": 0},
            forbidden,
            project=tmp_path,
            resume=[tmp_path / "first"],
        )
