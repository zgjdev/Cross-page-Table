import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts import run_reconstruction_upstream_batch as batch


def fixture(root):
    source = root / "artifacts/reconstruction-upstream/source"
    source.mkdir(parents=True)
    inputs = root / "inputs.jsonl"
    inputs.write_text("{}\n", encoding="utf-8")
    row = dict(
        group_id="PMC101-table-0",
        fragment_id="PMC101-table-0-part-0",
        page_num=5,
        part_index=0,
        crop_sha256=hashlib.sha256(b"test crop").hexdigest(),
    )
    prepared = source / "prepared.json"
    prepared.write_text(json.dumps(dict(status="prepared", fragments=[row])), encoding="utf-8")
    manifest = dict(
        inputs=str(inputs),
        inputs_sha256=batch.sha(inputs),
        input_track="image-only",
        protocol=batch.PROTOCOL,
        dataset_revision=batch.DATASET_REVISION,
        model_revision=batch.MODEL_REVISION,
        group_ids=[row["group_id"]],
    )
    (source / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    job = dict(
        index=0,
        run="20261115T124426Z-paddle-fit-shard-0000",
        group_ids=[row["group_id"]],
        expected_fragments=1,
    )
    job["argv"] = [
        batch.PADDLE_PYTHON,
        "scripts/run_reconstruction_upstream.py",
        "--project-root",
        str(root),
        "--inputs",
        inputs.relative_to(root).as_posix(),
        "--run",
        job["run"],
        "--reuse-prepared-run",
        source.relative_to(root).as_posix(),
        "--gpu",
        "0",
        "--group-id",
        row["group_id"],
    ]
    plan = dict(
        dataset_revision=batch.DATASET_REVISION,
        model_revision=batch.MODEL_REVISION,
        research_readiness="G0_pending_no_large_GPU_expansion",
        source_prepared=prepared.relative_to(root).as_posix(),
        source_prepared_sha256=batch.sha(prepared),
        max_groups_per_shard=25,
        groups=1,
        fragments=1,
        shards=1,
        jobs=[job],
    )
    file = root / "plan.json"
    file.write_text(json.dumps(plan), encoding="utf-8")
    return file, source, row, manifest, plan


def test_reject_extra_argv_and_source_drift(tmp_path):
    file, source, _, _, plan = fixture(tmp_path)
    batch.load_plan(tmp_path, file)
    plan["jobs"][0]["argv"].append("--prepare-only")
    file.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ValueError, match="argv"):
        batch.load_plan(tmp_path, file)
    (source / "prepared.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA"):
        batch.load_plan(tmp_path, file)


def write_child(out, row, manifest):
    fragment = out / "fragments/000000"
    fragment.mkdir(parents=True)
    crop = fragment / "crop.png"
    crop.write_bytes(b"test crop")
    record = dict(row, crop_relpath=crop.relative_to(out).as_posix())
    for path, content in (
        (out / "run-manifest.json", manifest),
        (out / "summary.json", dict(status="completed", expected=1, completed=1)),
        (out / "prepared.json", dict(status="prepared", fragments=[record])),
        (fragment / "source.json", record),
        (fragment / "prediction.json", dict(row, status="completed", html="<table></table>")),
    ):
        path.write_text(json.dumps(content), encoding="utf-8")
    return fragment / "prediction.json"


def test_child_validation_pins_identity_and_membership(tmp_path):
    file, _, row, manifest, _ = fixture(tmp_path)
    spec = batch.load_plan(tmp_path, file)
    out = tmp_path / "artifacts/reconstruction-upstream/20261122T180000Z-fit-shard-0000"
    prediction = write_child(out, row, manifest)
    assert batch.verify_shard(tmp_path, spec, 0, out)["fragments"] == 1
    prediction.write_text(
        json.dumps(dict(row, part_index=1, status="completed", html="x")), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="identity"):
        batch.verify_shard(tmp_path, spec, 0, out)
    assert Path(file).is_file()


def test_resume_failed_shard_into_new_run_and_reuse_verified_success(tmp_path, monkeypatch):
    file, _, row, manifest, _ = fixture(tmp_path)
    plan = batch.load_plan(tmp_path, file)
    runs = []
    monkeypatch.setattr(batch, "gpu_free_mib", lambda gpu: 40000)

    def worker(argv, **kwargs):
        assert Path(argv[0]) == tmp_path / batch.PADDLE_PYTHON
        out = tmp_path / batch.UPSTREAM / argv[argv.index("--run") + 1]
        runs.append(out)
        if len(runs) == 1:
            out.mkdir(parents=True)
            (out / "partial.txt").write_bytes(b"interrupted")
            raise subprocess.CalledProcessError(3, argv)
        write_child(out, row, manifest)

    monkeypatch.setattr(batch.subprocess, "run", worker)
    first = "20261122T180000Z-test"
    second = "20261122T180001Z-test"
    third = "20261122T180002Z-test"
    with pytest.raises(subprocess.CalledProcessError):
        batch.execute(tmp_path, plan, [0], {}, first, 0)
    batch.execute(
        tmp_path, plan, [0], batch.resumed_runs(tmp_path, plan, [batch.BATCHES / first]), second, 0
    )
    batch.execute(
        tmp_path, plan, [0], batch.resumed_runs(tmp_path, plan, [batch.BATCHES / second]), third, 0
    )
    assert len(runs) == 2
    assert (runs[0] / "partial.txt").read_bytes() == b"interrupted"
    with pytest.raises(FileExistsError):
        batch.execute(tmp_path, plan, [0], {}, second, 0)
    receipt = batch.read(tmp_path / batch.BATCHES / third, "shard-0000.json")
    assert receipt["status"] == "reused"
    assert receipt["run"] == runs[1].relative_to(tmp_path).as_posix()
