import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "qwen_smoke", Path(__file__).parents[2] / "scripts/run_reconstruction_qwen_smoke.py"
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


@pytest.mark.parametrize(
    "groups,steps",
    [([], 1), (["a"] * 2, 1), ([str(i) for i in range(17)], 1), (["a"], 51), (["a"], 0)],
)
def test_limits(groups, steps):
    with pytest.raises(ValueError):
        m.validate(groups, steps)


def test_limits_valid():
    m.validate(["a"], 1)
    m.validate([str(i) for i in range(16)], 50)


def test_language_attention_only():
    names = ["model.language_model.layers.0.self_attn." + x + "_proj" for x in "qkvo"]
    assert m.lora_modules(names + ["model.visual.blocks.0.attn.q_proj"]) == names
    with pytest.raises(ValueError):
        m.lora_modules(["model.visual.blocks.0.attn.q_proj"])


def test_path_escape(tmp_path):
    with pytest.raises(ValueError):
        m.safe(tmp_path, "../outside")


def test_mapping_train_only(tmp_path):
    import hashlib
    import json

    from cptla.reconstruction.data import DATASET_REVISION, PROTOCOL

    spec = importlib.util.spec_from_file_location(
        "fixture_cli", Path(__file__).with_name("test_baseline_cli.py")
    )
    fixture_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture_module)
    upstream, targets = fixture_module.fixture(tmp_path)
    prepared = json.loads((upstream / "prepared.json").read_text())
    input_path = tmp_path / "inputs.jsonl"
    rows = []
    for record in prepared["fragments"]:
        original_image = tmp_path / record["image_relpath"]
        image = (
            tmp_path
            / "data/pubtables-v2/extracted/Full Documents/train/images"
            / f"{record['document_id']}_page_{record['page_num']}.jpg"
        )
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(original_image.read_bytes())
        record["image_relpath"] = image.relative_to(tmp_path).as_posix()
        (upstream / record["crop_relpath"]).parent.joinpath("source.json").write_text(
            json.dumps(record)
        )
        rows.append(
            {
                "group_id": record["group_id"],
                "document_id": record["document_id"],
                "split": "train_fit",
                "source_split": "train",
                "dataset_revision": DATASET_REVISION,
                "protocol": PROTOCOL,
                "fragments": [record],
            }
        )
    (upstream / "prepared.json").write_text(json.dumps(prepared))
    input_path.write_text("\n".join(json.dumps(row) for row in rows))
    hashes = {}

    def read(path, expected=None):
        value = path.read_bytes()
        digest = hashlib.sha256(value).hexdigest()
        if expected and expected != digest:
            raise ValueError("SHA")
        hashes[str(path)] = digest
        return value

    examples, images = m.load_examples(tmp_path, input_path, targets, [upstream], ["g0"], read)
    assert len(examples) == len(images) == 1
    assert examples[0][0]["fragments"][0]["prediction_html"] == fixture_module.HTML
    rows[0]["split"] = "train_confirm"
    input_path.write_text("\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError):
        m.load_examples(tmp_path, input_path, targets, [upstream], ["g0"], read)


def test_resume_config_excludes_operational_paths():
    from types import SimpleNamespace

    args = SimpleNamespace(
        group_id=["a", "b"],
        max_tokens=8192,
        gradient_checkpointing=False,
        run="first",
        resume_state=None,
        steps=1,
    )
    first = m.resume_config(args, {"inputs": "abc"}, {"weight": "def"})
    args.run, args.resume_state, args.steps = "second", "old/state", 50
    assert m.resume_config(args, {"inputs": "abc"}, {"weight": "def"}) == first
    args.gradient_checkpointing = True
    assert m.resume_config(args, {"inputs": "abc"}, {"weight": "def"}) != first
    args.gradient_checkpointing = False
    assert m.resume_config(args, {"inputs": "changed"}, {"weight": "def"}) != first
    args.supervised_logits_only = True
    assert m.resume_config(args, {"inputs": "abc"}, {"weight": "def"}) != first
    args.supervised_logits_only = False
    args.loss_chunk_size = 512
    assert m.resume_config(args, {"inputs": "abc"}, {"weight": "def"}) != first
