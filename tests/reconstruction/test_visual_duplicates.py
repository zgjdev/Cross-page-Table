import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "visual_duplicates",
    Path(__file__).parents[2] / "scripts/audit_reconstruction_visual_duplicates.py",
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_candidates_match_exhaustive():
    values = [0, 1, 3, 7, 15, 31, (1 << 63), (1 << 63) | 7, 0xFFFFFFFFFFFFFFFF]
    rows = [{"document_id": str(i), "dhash": v} for i, v in enumerate(values)]
    actual = {(a, b) for a, b, distance in m.candidates(rows)}
    expected = {
        (a, b)
        for b in range(len(rows))
        for a in range(b)
        if (values[a] ^ values[b]).bit_count() <= 4
    }
    assert actual == expected
    assert list(m.candidates([{"document_id": "a", "dhash": 0}] * 2)) == []


def setup_inputs(tmp_path):
    image = tmp_path / "data/pubtables-v2/extracted/Full Documents/train/images/PMC123_page_1.jpg"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (40, 30), "white").save(image)
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    rows = [
        {
            "source_split": "train",
            "dataset_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
            "document_id": doc,
            "fragments": [
                {
                    "image_relpath": image.relative_to(tmp_path).as_posix(),
                    "image_sha256": digest,
                    "page_num": 1,
                }
            ],
        }
        for doc in ["PMC123"]
    ]
    inputs = tmp_path / "inputs.jsonl"
    inputs.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    return inputs


def test_run_exclusive_partial_and_sha(tmp_path):
    inputs = setup_inputs(tmp_path)
    output = m.audit(tmp_path, inputs, "20261114T120000Z-test", limit_images=1)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["status"] == "partial"
    assert summary["training_authorized"] is False
    assert summary["images"] == 1
    with pytest.raises(FileExistsError):
        m.audit(tmp_path, inputs, "20261114T120000Z-test")
    (tmp_path / json.loads(inputs.read_text())["fragments"][0]["image_relpath"]).write_bytes(b"bad")
    with pytest.raises(ValueError, match="SHA"):
        m.audit(tmp_path, inputs, "20261114T120001Z-test")
    assert (
        tmp_path / "artifacts/reconstruction-visual-duplicates/20261114T120001Z-test/failure.json"
    ).exists()


def test_reject_nontrain_and_escape(tmp_path):
    inputs = setup_inputs(tmp_path)
    inputs.write_text(inputs.read_text().replace("train", "test"))
    with pytest.raises(ValueError, match="train"):
        m.audit(tmp_path, inputs, "20261114T120002Z-test")
    with pytest.raises(ValueError):
        m.audit(tmp_path, tmp_path.parent / "outside.jsonl", "20261114T120003Z-test")


def test_band_recall_mutations():
    import random

    rng = random.Random(20261114)
    values = []
    for _ in range(40):
        base = rng.getrandbits(64)
        values.append(base)
        for distance in range(1, 6):
            mask = sum(1 << bit for bit in rng.sample(range(64), distance))
            values.append(base ^ mask)
    rows = [{"document_id": str(i), "dhash": value} for i, value in enumerate(values)]
    expected = {
        (a, b)
        for b in range(len(values))
        for a in range(b)
        if (values[a] ^ values[b]).bit_count() <= 4
    }
    assert {(a, b) for a, b, _ in m.candidates(rows)} == expected


@pytest.mark.parametrize("mutation", ["val_path", "revision", "document", "page"])
def test_reject_forged_train(tmp_path, mutation):
    inputs = setup_inputs(tmp_path)
    row = json.loads(inputs.read_text())
    if mutation == "val_path":
        source = tmp_path / row["fragments"][0]["image_relpath"]
        row["fragments"][0]["image_relpath"] = row["fragments"][0]["image_relpath"].replace(
            "/train/", "/val/"
        )
        target = tmp_path / row["fragments"][0]["image_relpath"]
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
    elif mutation == "revision":
        row["dataset_revision"] = "wrong"
    elif mutation == "document":
        row["document_id"] = "PMC999"
    else:
        row["fragments"][0]["page_num"] = 2
    inputs.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        m.audit(tmp_path, inputs, "20261114T130000Z-forged")
