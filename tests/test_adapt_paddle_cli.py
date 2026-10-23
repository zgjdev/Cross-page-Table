import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts.adapt_paddle_document_predictions import adapt_run


@pytest.fixture
def bundle(tmp_path):
    source = os.environ.get("PADDLE_MERGE_SOURCE")
    if source is None:
        pytest.skip("Pinned server source required for end-to-end integration")
    inputs, predictions = tmp_path / "inputs", tmp_path / "predictions"
    inputs.mkdir()
    (predictions / "PMC1").mkdir(parents=True)

    def block(index, label, content):
        return {
            "block_label": label,
            "block_content": content,
            "block_bbox": [0, 0, 100, 100],
            "global_block_id": index,
            "global_group_id": index,
        }

    html = "<table><tr><td>H</td></tr><tr><td>data</td></tr></table>"
    blocks = [
        [block(0, "table", html)],
        [block(1, "figure_title", "Continued"), block(2, "table", html)],
    ]
    pages = [
        {"res": {"page_index": i, "page_count": 2, "parsing_res_list": b}}
        for i, b in enumerate(blocks)
    ]
    (inputs / "packing-manifest.json").write_text(
        json.dumps({"pdfs": [{"document_id": "PMC1", "file": "PMC1.pdf", "pages": 2}]})
    )
    rows = [
        {
            "image_id": f"PMC1_page_{i}",
            "relative_path": f"PMC1_page_{i}.jpg",
            "unit_id": "PMC1",
            "document_id": "PMC1",
            "page_number": i,
        }
        for i in range(2)
    ]
    (inputs / "input-manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (predictions / "summary.json").write_text(json.dumps({"status": "completed", "pages": 2}))
    (predictions / "pages.jsonl").write_text(
        "".join(json.dumps({"document_id": "PMC1", "prediction": p}) + "\n" for p in pages)
    )
    for name in ("no_merge", "native_merge"):
        (predictions / "PMC1" / (name + ".json")).write_text(json.dumps(pages))
    return inputs, predictions, Path(source), tmp_path / "new"


def test_existing_output_refused_before_loading_any_inputs(tmp_path):
    marker = tmp_path / "keep"
    marker.write_bytes(b"unchanged")
    with pytest.raises(FileExistsError):
        adapt_run(tmp_path / "missing", tmp_path / "missing", tmp_path / "missing", tmp_path)
    assert marker.read_bytes() == b"unchanged"


def test_three_conditions_end_to_end_preserve_sources_and_hashes(bundle):
    *_, out = bundle
    result = adapt_run(*bundle)
    assert result["official_replay"] == "identical"
    assert result["modes"]["native_merge_official"]["tables"] == 2
    assert result["modes"]["native_merge_content_compat"]["tables"] == 1
    table = json.loads((out / "native_merge_content_compat/document-tables.jsonl").read_text())
    assert table["source_pages"] == [0, 1]
    for path, digest in result["input_hashes"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    stored = json.loads((out / "summary.json").read_text())
    for path, digest in stored["output_hashes"].items():
        assert hashlib.sha256((out / path).read_bytes()).hexdigest() == digest


def test_saved_official_mismatch_is_rejected_before_writing(bundle):
    _, predictions, _, out = bundle
    target = predictions / "PMC1/native_merge.json"
    changed = json.loads(target.read_text())
    changed[0]["res"]["parsing_res_list"][0]["block_content"] = "modified"
    target.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="replay"):
        adapt_run(*bundle)
    assert not out.exists()
