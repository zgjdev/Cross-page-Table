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
    image = root / "data/pubtables-v2/extracted/Full Documents/train/images/PMC1_page_0.jpg"
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
                fragment_id="PMC1-table-0-part-0",
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


def test_train_dev_requires_unobserved_overlay(tmp_path):
    inputs, row = fixture(tmp_path)
    row.update(split="train_dev", cluster_id="PMC1")
    inputs.write_text(json.dumps(row), encoding="utf-8")
    overlay = tmp_path / "overlay.jsonl"
    overlay_row = dict(
        document_id="PMC1", cluster_id="PMC1", effective_split="train_dev", observed_cluster=True
    )
    overlay.write_text(json.dumps(overlay_row), encoding="utf-8")
    groups = [row["group_id"]]
    with pytest.raises(ValueError, match="overlay"):
        runner.prepare(tmp_path, inputs, "no-overlay", groups, split="train_dev")
    with pytest.raises(ValueError, match="overlay"):
        runner.prepare(
            tmp_path, inputs, "seen", groups, split="train_dev", document_overlay=overlay
        )
    overlay_row["observed_cluster"] = False
    overlay.write_text(json.dumps(overlay_row), encoding="utf-8")
    output, records = runner.prepare(
        tmp_path, inputs, "allowed", groups, split="train_dev", document_overlay=overlay
    )
    assert len(records) == 1
    manifest = json.loads((output / "run-manifest.json").read_text())
    assert manifest["split"] == "train_dev"
    assert manifest["document_overlay_sha256"] == runner.sha(overlay)


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


@pytest.mark.parametrize(
    "field,value", [("page_num", 1), ("fragment_id", "wrong"), ("part_index", 1)]
)
def test_reject_source_identity(tmp_path, field, value):
    inputs, row = fixture(tmp_path)
    row["fragments"][0][field] = value
    inputs.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.prepare(tmp_path, inputs, "run", [row["group_id"]])


def test_reject_wrong_document(tmp_path):
    inputs, row = fixture(tmp_path)
    row["document_id"] = "PMC2"
    inputs.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.prepare(tmp_path, inputs, "run", [row["group_id"]])


def test_keyboard_interrupt_records_terminal_state(tmp_path):
    inputs, row = fixture(tmp_path)
    output, records = runner.prepare(tmp_path, inputs, "run", [row["group_id"]])

    class Pipeline:
        def predict_iter(self, *args, **kwargs):
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        runner.infer(Pipeline(), output, records)
    assert json.loads((output / "summary.json").read_text())["status"] == "interrupted"
    assert json.loads((output / "failure.json").read_text())["status"] == "interrupted"


def test_prepare_interrupt_preserves_failure(tmp_path, monkeypatch):
    inputs, row = fixture(tmp_path)

    def interrupt(*args):
        raise KeyboardInterrupt()

    monkeypatch.setattr(runner, "sha", interrupt)
    with pytest.raises(KeyboardInterrupt):
        runner.prepare(tmp_path, inputs, "run", [row["group_id"]])
    output = tmp_path / "artifacts/reconstruction-upstream/run"
    assert json.loads((output / "failure.json").read_text())["status"] == "interrupted"


def test_reuse_copy_and_new_inference(tmp_path, monkeypatch):
    inputs, row = fixture(tmp_path)
    old, records = runner.prepare(tmp_path, inputs, "old", [row["group_id"]])
    (old / "fragments/000000/prediction.json").write_text("old prediction")
    before = {p: p.read_bytes() for p in old.rglob("*") if p.is_file()}
    monkeypatch.setattr(Image.Image, "crop", lambda *a: pytest.fail("recropped"))
    new, copied = runner.prepare(tmp_path, inputs, "new", [row["group_id"]], old)
    assert not (new / "fragments/000000/prediction.json").exists()
    assert json.loads((new / "fragments/000000/source.json").read_text()) == copied[0]

    class Pipeline:
        def predict_iter(self, path, **kwargs):
            assert Path(path).is_relative_to(new)
            yield SimpleNamespace(
                json={
                    "res": {
                        "parsing_res_list": [dict(block_label="table", block_content="<table/>")]
                    }
                }
            )

    runner.infer(Pipeline(), new, copied)
    assert all(p.read_bytes() == value for p, value in before.items())
    with pytest.raises(FileExistsError):
        runner.prepare(tmp_path, inputs, "new", [row["group_id"]], old)


@pytest.mark.parametrize(
    "damage", ["sha", "identity", "escape", "duplicate", "missing", "manifest"]
)
def test_reuse_rejects_bad_sources(tmp_path, damage):
    inputs, row = fixture(tmp_path)
    old, records = runner.prepare(tmp_path, inputs, "old", [row["group_id"]])
    prepared = json.loads((old / "prepared.json").read_text())
    record = prepared["fragments"][0]
    if damage == "sha":
        (old / record["crop_relpath"]).write_bytes(b"bad")
    elif damage == "identity":
        record["document_id"] = "wrong"
    elif damage == "escape":
        record["crop_relpath"] = "../../../../../escape.png"
    elif damage == "duplicate":
        prepared["fragments"].append(record)
    elif damage == "missing":
        prepared["fragments"] = []
    else:
        manifest = json.loads((old / "run-manifest.json").read_text())
        manifest["inputs_sha256"] = "bad"
        (old / "run-manifest.json").write_text(json.dumps(manifest))
    (old / "prepared.json").write_text(json.dumps(prepared))
    with pytest.raises(ValueError):
        runner.prepare(tmp_path, inputs, "new", [row["group_id"]], old)
    assert (tmp_path / "artifacts/reconstruction-upstream/new/failure.json").exists()


@pytest.mark.parametrize(
    "target", ["prepared.json", "run-manifest.json", "fragments/000000/source.json"]
)
def test_reuse_detects_read_window_mutation(tmp_path, monkeypatch, target):
    inputs, row = fixture(tmp_path)
    old, _ = runner.prepare(tmp_path, inputs, "old", [row["group_id"]])
    changed = old / target
    original = Path.read_bytes

    def read_then_mutate(path):
        data = original(path)
        if path == changed:
            path.write_bytes(data + b" ")
        return data

    monkeypatch.setattr(Path, "read_bytes", read_then_mutate)
    with pytest.raises(ValueError, match="changed"):
        runner.prepare(tmp_path, inputs, "new", [row["group_id"]], old)
    assert (tmp_path / "artifacts/reconstruction-upstream/new/failure.json").exists()


@pytest.mark.parametrize("subset", [False, True])
def test_reuse_reordered_groups(tmp_path, subset):
    inputs, row = fixture(tmp_path)
    second = json.loads(json.dumps(row))
    second["group_id"] = "PMC1-table-1"
    second["fragments"][0]["fragment_id"] = "PMC1-table-1-part-0"
    inputs.write_text("\n".join(json.dumps(r) for r in [row, second]))
    old, _ = runner.prepare(tmp_path, inputs, "old", [row["group_id"], second["group_id"]])
    selected = [second["group_id"]] if subset else [second["group_id"], row["group_id"]]
    new, records = runner.prepare(tmp_path, inputs, "new", selected, old)
    assert [r["group_id"] for r in records] == selected
    assert len(list(new.rglob("crop.png"))) == len(selected)
    for index, record in enumerate(records):
        assert record["crop_relpath"] == f"fragments/{index:06d}/crop.png"
        assert (
            json.loads((new / record["crop_relpath"]).with_name("source.json").read_text())
            == record
        )
