import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "generation", Path(__file__).parents[2] / "scripts/review_reconstruction_qwen_smoke.py"
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_generation_no_targets_and_source_inheritance():
    examples = [
        {"group_id": "a", "source_pages": [2, 4], "messages": [{"role": "user", "content": []}]}
    ]
    predictions = m.generate(examples, lambda messages, budget: ("```html\nX\n```", 12, True), 4096)
    assert predictions[0]["html"] == "```html\nX\n```"
    assert predictions[0]["source_pages"] == [2, 4]
    assert predictions[0]["status"] == "completed"
    assert len(predictions) == 1


def test_truncation_and_limits():
    example = {"group_id": "a", "source_pages": [1], "messages": []}
    prediction = m.generate([example], lambda a, b: ("X", b, False), 4096)[0]
    assert prediction["truncated"] and prediction["status"] == "truncated"
    with pytest.raises(ValueError):
        m.generate([dict(example, group_id=str(i)) for i in range(17)], lambda a, b: None, 4096)
    with pytest.raises(ValueError):
        m.generate([example, example], lambda a, b: None, 4096)


def test_assistant_message_rejected():
    with pytest.raises(ValueError):
        m.generate(
            [{"group_id": "a", "source_pages": [1], "messages": [{"role": "assistant"}]}],
            lambda a, b: None,
            4096,
        )


def test_completed_prediction_preserved_before_later_failure():
    saved = []
    examples = [dict(group_id=str(i), source_pages=[i], messages=[]) for i in range(2)]

    def backend(messages, budget):
        if saved:
            raise RuntimeError("later generation failed")
        return "raw", 1, True

    with pytest.raises(RuntimeError):
        m.generate(examples, backend, 4096, on_prediction=saved.append)
    assert len(saved) == 1 and saved[0]["group_id"] == "0"


def test_untrained_probe_preserves_training_config_and_rejects_overlap():
    config = dict(group_id=["trained"], upstream_run=["old"], inputs="input", targets="target")
    selected = m.probe_config(config, ["untrained"], ["old", "extra"])
    assert config["group_id"] == ["trained"]
    assert selected["group_id"] == ["untrained"] and selected["targets"] == "target"
    with pytest.raises(ValueError):
        m.probe_config(config, ["trained"], ["old"])
    with pytest.raises(ValueError):
        m.probe_config(config, ["untrained"], [])


def test_real_mapping_never_reads_gt_and_matches_training_prompt(tmp_path):
    import hashlib
    import json

    from cptla.reconstruction.data import DATASET_REVISION, PROTOCOL
    from cptla.reconstruction.grid import GRID_VERSION
    from cptla.reconstruction.sft_data import build_messages

    spec = importlib.util.spec_from_file_location(
        "fixture_cli", Path(__file__).with_name("test_baseline_cli.py")
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    upstream, targets = fixture.fixture(tmp_path)
    prepared = json.loads((upstream / "prepared.json").read_text())
    originals = []
    for record in prepared["fragments"]:
        image = (
            tmp_path
            / m.TRAIN_RELATIVE_PATH
            / "images"
            / f"{record['document_id']}_page_{record['page_num']}.jpg"
        )
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes((tmp_path / record["image_relpath"]).read_bytes())
        record["image_relpath"] = image.relative_to(tmp_path).as_posix()
        (upstream / record["crop_relpath"]).with_name("source.json").write_text(json.dumps(record))
        originals.append(
            dict(
                group_id=record["group_id"],
                document_id=record["document_id"],
                split="train_fit",
                source_split="train",
                protocol=PROTOCOL,
                dataset_revision=DATASET_REVISION,
                fragments=[record],
            )
        )
    (upstream / "prepared.json").write_text(json.dumps(prepared))
    inputs = tmp_path / "inputs.jsonl"
    inputs.write_text("\n".join(map(json.dumps, originals)))
    visited = []

    def read(path, expected=None):
        assert path != targets, "generation read GT"
        visited.append(path)
        raw = path.read_bytes()
        if expected:
            assert hashlib.sha256(raw).hexdigest() == expected
        return raw

    config = dict(group_id=["g0"], inputs=inputs, targets=targets, upstream_run=[upstream])
    examples, images = m.input_examples(tmp_path, config, read)
    assert len(examples) == len(images) == 1 and targets not in visited
    assert examples[0]["source_pages"] == [originals[0]["fragments"][0]["page_num"]]
    expected = build_messages(
        dict(
            group_id="g0",
            split="train_fit",
            track="image-only",
            fragments=[dict(image_path=next(iter(images)), prediction_html=fixture.HTML)],
        ),
        dict(group_id="g0", grid_version=GRID_VERSION, html=fixture.HTML),
    )[:1]
    assert examples[0]["messages"] == expected
