import json

import pytest

from cptla.evaluation.document_run import canonical_manifest_bytes, digest
from scripts.run_paddle_document_full import (
    export_complete_batch,
    validate_child,
    verify_model,
)


@pytest.fixture
def child(tmp_path):
    doc = {"document_id": "PMC1", "pages": 2}
    prediction = tmp_path / "outputs/run"
    inputs = tmp_path / "inputs"
    log = tmp_path / "logs/baselines/paddleocr-vl-1.5/run"
    for folder in (prediction / "PMC1", inputs, log):
        folder.mkdir(parents=True)
    (inputs / "PMC1.pdf").write_bytes(b"original-image-pdf")
    packed = {
        "pdf_text_audit": "empty",
        "embedded_image_audit": "byte-identical",
        "pages": [],
        "pdfs": [
            {
                "document_id": "PMC1",
                "file": "PMC1.pdf",
                "pages": 2,
                "sha256": digest(inputs / "PMC1.pdf"),
            }
        ],
    }
    (inputs / "packing-manifest.json").write_text(json.dumps(packed))
    (inputs / "input-manifest.jsonl").write_text("{}\n{}\n")
    metadata = {
        "split": "train",
        "input_track": "image-only",
        "input_manifest_sha256": digest(inputs / "packing-manifest.json"),
        "vl_model_revision": "2a4195faa5e7914c12f2fc601d72c81caf8d2da5",
        "layout_model_revision": "241f8bdfc77a7c7bee915a5057aaee58c235a8d3",
        "data_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
    }
    (log / "run-manifest.json").write_text(json.dumps(metadata))
    (log / "pipeline-config.yaml").write_text("fixed")
    (prediction / "summary.json").write_text(
        json.dumps({"status": "completed", "pages": 2, "documents": [doc]})
    )
    pages = [{"res": {"page_index": i, "parsing_res_list": []}} for i in range(2)]
    (prediction / "pages.jsonl").write_text(
        "".join(json.dumps({"document_id": "PMC1", "prediction": p}) + "\n" for p in pages)
    )
    for mode in ("no_merge", "native_merge"):
        (prediction / "PMC1" / (mode + ".json")).write_text(json.dumps(pages))
    return tmp_path, prediction, inputs, doc


def test_child_provenance_and_scoring_export(child):
    project, prediction, inputs, doc = child
    result = validate_child(prediction, inputs, doc, "train", project)
    out = project / "batch"
    out.mkdir()
    manifest = project / "manifest.jsonl"
    manifest.write_text(
        "".join(json.dumps({"document_id": "PMC1", "page_number": i}) + "\n" for i in range(2))
    )
    checksum = digest(manifest)
    export_complete_batch(
        out,
        {"results": {"PMC1": result}, "pages": 2},
        manifest,
        [doc],
        expected_manifest_sha=checksum,
    )
    assert (out / "exported-inputs/input-manifest.jsonl").read_bytes() == canonical_manifest_bytes(
        manifest, checksum
    )
    assert (out / "exported-predictions/pages.jsonl").read_bytes() == (
        prediction / "pages.jsonl"
    ).read_bytes()
    assert json.loads((out / "exported-predictions/summary.json").read_text())["pages"] == 2
    assert json.loads((out / "exported-inputs/packing-manifest.json").read_text())["pdfs"][0][
        "file"
    ] == str((inputs / "PMC1.pdf").resolve())


def test_wrong_split_and_missing_raw_page_are_rejected(child):
    project, prediction, inputs, doc = child
    with pytest.raises(ValueError, match="provenance"):
        validate_child(prediction, inputs, doc, "val", project)
    rows = (prediction / "pages.jsonl").read_text().splitlines()
    (prediction / "pages.jsonl").write_text(rows[0] + "\n")
    with pytest.raises(ValueError, match="coverage"):
        validate_child(prediction, inputs, doc, "train", project)


def test_model_mutation_is_detected(tmp_path):
    model = tmp_path / "model.bin"
    model.write_bytes(b"fixed")
    record = {
        "status": "complete",
        "revision": "rev",
        "verified": [{"file": "model.bin", "size": model.stat().st_size, "sha256": digest(model)}],
    }
    (tmp_path / "download-manifest.json").write_text(json.dumps(record))
    verify_model(tmp_path, "rev")
    model.write_bytes(b"other")
    with pytest.raises(ValueError, match="integrity"):
        verify_model(tmp_path, "rev")


def test_changed_frozen_manifest_blocks_export_before_writing(child):
    project, prediction, inputs, doc = child
    result = validate_child(prediction, inputs, doc, "train", project)
    manifest = project / "manifest.jsonl"
    manifest.write_text(json.dumps({"document_id": "PMC1", "page_number": 0}) + "\n")
    checksum = digest(manifest)
    manifest.write_text("changed")
    out = project / "batch"
    out.mkdir()
    with pytest.raises(ValueError, match="SHA"):
        export_complete_batch(
            out,
            {"results": {"PMC1": result}, "pages": 2},
            manifest,
            [doc],
            expected_manifest_sha=checksum,
        )
    assert not (out / "exported-inputs").exists()
