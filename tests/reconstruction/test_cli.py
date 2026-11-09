import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.build_reconstruction_manifest import build_run


def make_training_source(root: Path) -> Path:
    train = root / "data/pubtables-v2/extracted/Full Documents/train"
    (train / "images").mkdir(parents=True)
    (train / "tables").mkdir()
    for number in range(1, 21):
        doc = f"PMC{number}"
        for page in (0, 1):
            Image.new("RGB", (120, 180), (number, page, 240)).save(
                train / "images" / f"{doc}_page_{page}.jpg"
            )
        tables = [
            {
                "html": f"<table><tr><td>Document {number}</td></tr></table>",
                "parts": [
                    {"page_num": page, "page_object_num": 0, "bbox": [5, 5, 110, 170]}
                    for page in (0, 1)
                ],
                "cells": [
                    {"row_nums": [0], "column_nums": [0], "xml_text_content": f"document {number}"}
                ],
            }
        ]
        (train / "tables" / f"{doc}_tables.json").write_text(json.dumps(tables))
    return train


def test_run_keeps_labels_separate_and_publishes_auditable_manifest(tmp_path):
    train = make_training_source(tmp_path)
    source = train / "tables/PMC1_tables.json"
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "artifacts/reconstruction/fixture"
    summary = build_run(tmp_path, output, sample_size=2, coordinate_size=1)
    assert summary["status"] == "completed"
    assert summary["training_allowed"] is False
    assert summary["prediction_status"] == "not_generated"
    inputs = [json.loads(s) for s in (output / "inputs.jsonl").read_text().splitlines()]
    targets = [json.loads(s) for s in (output / "targets.jsonl").read_text().splitlines()]
    assert len(inputs) == len(targets) == 20
    assert {s["group_id"] for s in inputs} == {s["group_id"] for s in targets}
    assert "html" not in json.dumps(inputs)
    assert "xml_text_content" not in json.dumps(inputs)
    hashes = json.loads((output / "result-hashes.json").read_text())
    for relative, expected in hashes.items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == expected
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
    assert (output / "review/index.html").exists()


def test_run_never_overwrites_existing_directory(tmp_path):
    output = tmp_path / "artifacts/reconstruction/existing"
    output.mkdir(parents=True)
    keep = output / "previous-result.json"
    keep.write_text("keep")
    with pytest.raises(FileExistsError):
        build_run(tmp_path, output)
    assert keep.read_text() == "keep"


@pytest.mark.parametrize("relative", ["data/new-run", "outputs/new-run", "../escape"])
def test_run_rejects_output_outside_new_reconstruction_artifacts(tmp_path, relative):
    with pytest.raises(ValueError):
        build_run(tmp_path, tmp_path / relative)


def test_run_preserves_failed_attempt_and_does_not_publish_completed(tmp_path):
    output = tmp_path / "artifacts/reconstruction/missing-inputs"
    with pytest.raises((FileNotFoundError, NotADirectoryError, ValueError)):
        build_run(tmp_path, output)
    assert (output / "failure.json").exists()
    assert not (output / "summary.json").exists()


def test_partial_scan_stays_marked_partial(tmp_path):
    make_training_source(tmp_path)
    output = tmp_path / "artifacts/reconstruction/partial"
    summary = build_run(tmp_path, output, limit_documents=2, sample_size=2, coordinate_size=1)
    assert summary["scope"] == "partial_train_technical_smoke"
    assert summary["data_audit"]["documents"] == 2
    assert summary["training_allowed"] is False
