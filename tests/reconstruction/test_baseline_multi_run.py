import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "existing_cli_test", Path(__file__).with_name("test_baseline_cli.py")
)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def fixture(root):
    first, targets = base.fixture(root / "one")
    second, targets2 = base.fixture(root / "two")
    # Fixtures nested beneath one project must reference paths from the joint root.
    for run, prefix in [(first, "one"), (second, "two")]:
        prepared = json.loads((run / "prepared.json").read_text())
        for record in prepared["fragments"]:
            record["image_relpath"] = prefix + "/" + record["image_relpath"]
            if prefix == "two":
                record["group_id"] = "new-" + record["group_id"]
                record["fragment_id"] = "new-" + record["fragment_id"]
            directory = (run / record["crop_relpath"]).parent
            (directory / "source.json").write_text(json.dumps(record))
            prediction = json.loads((directory / "prediction.json").read_text())
            prediction.update(group_id=record["group_id"], fragment_id=record["fragment_id"])
            (directory / "prediction.json").write_text(json.dumps(prediction))
        (run / "prepared.json").write_text(json.dumps(prepared))
    merged = root / "targets.jsonl"
    merged.write_text(targets.read_text() + "\n" + targets2.read_text().replace(': "g', ': "new-g'))
    return first, second, merged


def test_joint_union_and_hashes(tmp_path):
    first, second, targets = fixture(tmp_path)
    output = base.runner.run(tmp_path, first, targets, "joint", additional_upstream_runs=[second])
    assert json.loads((output / "scores.json").read_text())["n_targets"] == 4
    manifest = json.loads((output / "run-manifest.json").read_text())
    assert len(manifest["parameters"]["upstream_runs"]) == 2
    hashes = json.loads((output / "input-hashes.json").read_text())
    assert any(key.startswith("two/") for key in hashes)


@pytest.mark.parametrize("kind", ["duplicate_run", "duplicate_group", "incomplete"])
def test_invalid_additional(tmp_path, kind):
    first, second, targets = fixture(tmp_path)
    if kind == "duplicate_run":
        second = first
    elif kind == "duplicate_group":
        path = second / "prepared.json"
        path.write_text(path.read_text().replace("new-g", "g"))
    else:
        (second / "summary.json").write_text('{"status":"running"}')
    with pytest.raises(ValueError):
        base.runner.run(tmp_path, first, targets, "bad", additional_upstream_runs=[second])


def test_joint_missing_prediction_preserved(tmp_path):
    first, second, targets = fixture(tmp_path)
    (second / "fragments/000000/prediction.json").unlink()
    output = base.runner.run(tmp_path, first, targets, "missing", additional_upstream_runs=[second])
    assert json.loads((output / "scores.json").read_text())["n_targets"] == 4
    assert len(json.loads((output / "summary.json").read_text())["missing_prediction_paths"]) == 1


def test_additional_run_reverified(tmp_path, monkeypatch):
    first, second, targets = fixture(tmp_path)
    original = base.runner.score_groups

    def mutate(*args):
        (second / "fragments/000000/prediction.json").write_text("{}")
        return original(*args)

    monkeypatch.setattr(base.runner, "score_groups", mutate)
    with pytest.raises(ValueError, match="SHA mismatch"):
        base.runner.run(tmp_path, first, targets, "mutated", additional_upstream_runs=[second])
    assert not (tmp_path / "artifacts/reconstruction-baselines/mutated/summary.json").exists()
