import importlib.util
import json
from pathlib import Path

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path("scripts") / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path):
    inputs = tmp_path / "manifest.jsonl"
    inputs.write_text(
        json.dumps(
            dict(
                document_id="PMC1",
                unit_id="PMC1",
                image_id="PMC1_page_0.jpg",
                relative_path="PMC1_page_0.jpg",
                page_number=0,
            )
        )
        + "\n"
    )
    predictions = tmp_path / "predictions"
    predictions.mkdir()
    (predictions / "PMC1.json").write_text(
        json.dumps(
            dict(
                document_id="PMC1",
                pages=[dict(status="ok", elapsed_sec=1)],
                no_merge=[],
                merged=[],
                decisions=[],
            )
        )
    )
    return inputs, predictions


def test_adapter_both_modes_and_coverage(tmp_path):
    module = load("adapt_ocrflux_document_predictions")
    manifest, predictions = fixture(tmp_path)
    module.adapt(manifest, predictions, tmp_path / "adapted")
    for mode in ("no_merge", "merged"):
        row = json.loads((tmp_path / "adapted" / mode / "page-results.jsonl").read_text())
        assert row["status"] == "ok" and row["tables_html"] == []
    with pytest.raises(FileExistsError):
        module.adapt(manifest, predictions, tmp_path / "adapted")


def test_adapter_rejects_missing_page(tmp_path):
    module = load("adapt_ocrflux_document_predictions")
    manifest, predictions = fixture(tmp_path)
    (predictions / "PMC1.json").write_text(
        json.dumps(dict(document_id="PMC1", pages=[], no_merge=[], merged=[], decisions=[]))
    )
    with pytest.raises(ValueError, match="coverage"):
        module.adapt(manifest, predictions, tmp_path / "adapted")


def test_adapter_preserves_packer_stem_image_id(tmp_path):
    module = load("adapt_ocrflux_document_predictions")
    manifest, predictions = fixture(tmp_path)
    row = json.loads(manifest.read_text())
    row["image_id"] = "PMC1_page_0"
    manifest.write_text(json.dumps(row) + "\n")
    module.adapt(manifest, predictions, tmp_path / "adapted")
    saved = json.loads((tmp_path / "adapted/no_merge/page-results.jsonl").read_text())
    assert saved["image_id"] == "PMC1_page_0"


def test_twelve_page_lexical_manifest_gets_numeric_order(tmp_path):
    module = load("adapt_ocrflux_document_predictions")
    manifest, predictions = fixture(tmp_path)
    rows = []
    for page in range(12):
        name = f"PMC1_page_{page}.jpg"
        rows.append(
            dict(
                document_id="PMC1",
                unit_id="PMC1",
                image_id=name,
                relative_path=name,
                page_number=page,
            )
        )
    rows.sort(key=lambda r: r["image_id"])
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (predictions / "PMC1.json").write_text(
        json.dumps(
            dict(
                document_id="PMC1",
                pages=[dict(status="ok", elapsed_sec=1)] * 12,
                no_merge=[],
                merged=[],
                decisions=[],
            )
        )
    )
    module.adapt(manifest, predictions, tmp_path / "adapted")
    result = [
        json.loads(s) for s in (tmp_path / "adapted/input-manifest.jsonl").read_text().splitlines()
    ]
    assert [r["page_number"] for r in result] == list(range(12))


def test_gpu_entry_import_does_not_import_vllm():
    import sys

    load("run_ocrflux_document")
    assert "vllm" not in sys.modules
