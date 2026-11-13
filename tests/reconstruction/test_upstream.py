import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "upstream", Path(__file__).parents[2] / "scripts/run_reconstruction_upstream.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def fixture(root):
    image = root / "data/pubtables-v2/extracted/Full Documents/train/images/PMC1_0.png"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (20, 30), "white").save(image)
    row = dict(
        group_id="PMC1-table-0",
        document_id="PMC1",
        source_split="train",
        split="train_fit",
        protocol=runner.PROTOCOL,
        dataset_revision=runner.DATASET_REVISION,
        fragments=[
            dict(
                fragment_id="p0",
                part_index=0,
                page_num=0,
                page_object_num=0,
                image_relpath=image.relative_to(root).as_posix(),
                image_sha256=runner.sha(image),
                image_size=[20, 30],
                crop_box=[1, 2, 11, 22],
            )
        ],
    )
    inputs = root / "inputs.jsonl"
    inputs.write_text(json.dumps(row), encoding="utf-8")
    return inputs, row


def test_prepare_and_infer(tmp_path):
    inputs, row = fixture(tmp_path)
    output, records = runner.prepare(tmp_path, inputs, "run1", [row["group_id"]])
    assert records[0]["crop_size"] == [10, 20]
    assert records[0]["orientation"] == "preserve_original"

    class Pipeline:
        def predict_iter(self, path, **kwargs):
            assert kwargs == dict(prompt_label="table", use_layout_detection=False)
            yield SimpleNamespace(
                json={
                    "res": {
                        "parsing_res_list": [{"block_label": "table", "block_content": "<table/>"}]
                    }
                }
            )

    summary = runner.infer(Pipeline(), output, records)
    assert summary["status"] == "completed"
    assert summary["completed"] == 1
    prediction = json.loads((output / "fragments/000000/prediction.json").read_text())
    assert prediction["page_num"] == 0 and prediction["part_index"] == 0
    with pytest.raises(FileExistsError):
        runner.prepare(tmp_path, inputs, "run1", [row["group_id"]])


@pytest.mark.parametrize(
    "field,value",
    [
        ("split", "train_confirm"),
        ("source_split", "val"),
        ("protocol", "D0"),
        ("dataset_revision", "wrong"),
    ],
)
def test_reject_protocol(tmp_path, field, value):
    inputs, row = fixture(tmp_path)
    row[field] = value
    inputs.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.prepare(tmp_path, inputs, "run", [row["group_id"]])


def test_failure_preserves_raw(tmp_path):
    inputs, row = fixture(tmp_path)
    output, records = runner.prepare(tmp_path, inputs, "run", [row["group_id"]])

    class Pipeline:
        def predict_iter(self, path, **kwargs):
            yield SimpleNamespace(json={"res": {"parsing_res_list": []}})

    with pytest.raises(ValueError):
        runner.infer(Pipeline(), output, records)
    assert (output / "fragments/000000/response.json").exists()
    assert json.loads((output / "summary.json").read_text())["status"] == "failed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("image_sha256", "wrong"),
        ("crop_box", [-1, 0, 2, 3]),
        ("image_size", [3, 4]),
        ("image_relpath", "../outside.png"),
    ],
)
def test_reject_source_mutations(tmp_path, field, value):
    inputs, row = fixture(tmp_path)
    row["fragments"][0][field] = value
    inputs.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.prepare(tmp_path, inputs, "run", [row["group_id"]])
    assert (tmp_path / "artifacts/reconstruction-upstream/run/failure.json").exists()


def test_partial_iterator_retains_response(tmp_path):
    inputs, row = fixture(tmp_path)
    output, records = runner.prepare(tmp_path, inputs, "run", [row["group_id"]])

    class Pipeline:
        def predict_iter(self, path, **kwargs):
            yield SimpleNamespace(json={"res": {}})
            raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError):
        runner.infer(Pipeline(), output, records)
    assert (output / "fragments/000000/response-000.json").exists()
    assert json.loads((output / "summary.json").read_text())["completed"] == 0
