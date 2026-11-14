import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "baseline_cli", Path(__file__).parents[2] / "scripts/score_reconstruction_baseline.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
HTML = "<table><tr><td>A</td></tr></table>"


def fixture(root):
    upstream = root / "artifacts/reconstruction-upstream/pilot"
    records = []
    for i in range(2):
        directory = upstream / "fragments" / f"{i:06d}"
        directory.mkdir(parents=True)
        image = root / f"image{i}.jpg"
        image.write_bytes(b"image")
        crop = directory / "crop.png"
        crop.write_bytes(b"crop")
        record = dict(
            group_id=f"g{i}",
            document_id=f"PMC{i}",
            fragment_id=f"g{i}-part-0",
            page_num=i,
            part_index=0,
            image_relpath=image.relative_to(root).as_posix(),
            image_sha256=hashlib.sha256(b"image").hexdigest(),
            crop_relpath=crop.relative_to(upstream).as_posix(),
            crop_sha256=hashlib.sha256(b"crop").hexdigest(),
        )
        records.append(record)
        (directory / "source.json").write_text(json.dumps(record))
        (directory / "prediction.json").write_text(
            json.dumps(
                dict(
                    group_id=f"g{i}",
                    fragment_id=f"g{i}-part-0",
                    page_num=i,
                    part_index=0,
                    html=HTML,
                    status="completed",
                )
            )
        )
    (upstream / "prepared.json").write_text(json.dumps(dict(status="prepared", fragments=records)))
    (upstream / "summary.json").write_text(
        json.dumps(dict(status="completed", expected=2, completed=2))
    )
    targets = root / "targets.jsonl"
    targets.write_text(
        "\n".join(json.dumps(dict(group_id=f"g{i}", html=HTML, source_pages=[i])) for i in range(2))
    )
    return upstream, targets


def test_scores_and_immutable(tmp_path):
    upstream, targets = fixture(tmp_path)
    output = runner.run(tmp_path, upstream, targets, "score")
    score = json.loads((output / "scores.json").read_text())
    assert score["n_targets"] == 2
    assert score["diagnostic_rates"]["joint_exact"] == 1
    assert json.loads((output / "summary.json").read_text())["status"] == "completed"
    with pytest.raises(FileExistsError):
        runner.run(tmp_path, upstream, targets, "score")


def test_jsonl_unicode_separators_remain_inside_record(tmp_path):
    upstream, targets = fixture(tmp_path)
    rows = [json.loads(line) for line in targets.read_text().splitlines()]
    rows[0]["html"] = HTML.replace("A", "A\u2028B\u2029C\u0085D")
    targets.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8"
    )
    output = runner.run(tmp_path, upstream, targets, "unicode-score")
    assert json.loads((output / "scores.json").read_text())["n_targets"] == 2


def test_missing_prediction_keeps_denominator_and_extra_report(tmp_path):
    upstream, targets = fixture(tmp_path)
    (upstream / "fragments/000000/prediction.json").unlink()
    extra = upstream / "fragments/999999"
    extra.mkdir()
    (extra / "prediction.json").write_text("{}")
    output = runner.run(tmp_path, upstream, targets, "score")
    score = json.loads((output / "scores.json").read_text())
    assert score["n_targets"] == 2
    assert score["diagnostic_rates"]["joint_exact"] == 0.5
    assert len(json.loads((output / "summary.json").read_text())["extra_prediction_paths"]) == 1


@pytest.mark.parametrize("kind", ["crop", "target", "source", "status", "outside"])
def test_reject_invalid_inputs(tmp_path, kind):
    upstream, targets = fixture(tmp_path)
    if kind == "crop":
        (upstream / "fragments/000000/crop.png").write_bytes(b"changed")
    elif kind == "target":
        targets.write_text("")
    elif kind == "source":
        (upstream / "fragments/000000/source.json").write_text("{}")
    elif kind == "status":
        (upstream / "summary.json").write_text('{"status":"running"}')
    else:
        targets = tmp_path.parent / "outside"
    with pytest.raises((ValueError, FileNotFoundError)):
        runner.run(tmp_path, upstream, targets, "bad")
    assert not (tmp_path / "artifacts/reconstruction-baselines/bad/summary.json").exists()


def test_duplicate_target_rejected(tmp_path):
    upstream, targets = fixture(tmp_path)
    targets.write_text(targets.read_text() + "\n" + targets.read_text().splitlines()[0])
    with pytest.raises(ValueError, match="duplicate target"):
        runner.run(tmp_path, upstream, targets, "duplicate")


def test_source_reverification_before_summary(tmp_path, monkeypatch):
    upstream, targets = fixture(tmp_path)
    original = runner.score_groups

    def mutate(*args):
        (upstream / "fragments/000000/prediction.json").write_text("{}")
        return original(*args)

    monkeypatch.setattr(runner, "score_groups", mutate)
    with pytest.raises(ValueError, match="SHA mismatch"):
        runner.run(tmp_path, upstream, targets, "mutated")
    output = tmp_path / "artifacts/reconstruction-baselines/mutated"
    assert (output / "failure.json").exists()
    assert not (output / "summary.json").exists()


def test_optional_header_baseline(tmp_path):
    upstream, targets = fixture(tmp_path)
    output = runner.run(tmp_path, upstream, targets, "header", baseline="explicit_header_exact_v1")
    assert (
        json.loads((output / "run-manifest.json").read_text())["baseline"]
        == "explicit_header_exact_v1"
    )
    assert (
        json.loads((output / "predictions.json").read_text())[0]["diagnostics"]["baseline"]
        == "explicit_header_exact_v1"
    )
