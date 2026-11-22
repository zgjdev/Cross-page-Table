"""核验并逐片执行已冻结的 Paddle train_fit 计划。默认仅输出只读预检。"""

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cptla.reconstruction.data import DATASET_REVISION, PROTOCOL

PADDLE_PYTHON = ".venvs/paddle-v15-20261023T081029Z-paddle-v15/bin/python"
UPSTREAM = Path("artifacts/reconstruction-upstream")
BATCHES = Path("artifacts/reconstruction-upstream-batches")
SCRIPT = "scripts/run_reconstruction_upstream.py"
MODEL_REVISION = "2a4195faa5e7914c12f2fc601d72c81caf8d2da5"
IDENTITY = ("group_id", "fragment_id", "page_num", "part_index")


def inside(parent, value):
    path = (parent / value).resolve()
    if not path.is_relative_to(parent):
        raise ValueError(f"path escapes scoped directory: {value}")
    return path


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(parent, value):
    return json.loads(inside(parent, value).read_bytes())


def write(path, data):
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)


@dataclass(frozen=True)
class Plan:
    path: Path
    digest: str
    source: str
    source_sha: str
    inputs: str
    inputs_sha: str
    readiness: str
    jobs: list
    by_group: dict


def child_argv(root, inputs, source, run, groups, gpu):
    return [
        PADDLE_PYTHON,
        SCRIPT,
        "--project-root",
        str(root),
        "--inputs",
        inputs,
        "--run",
        run,
        "--reuse-prepared-run",
        source,
        "--gpu",
        str(gpu),
        *(part for group in groups for part in ("--group-id", group)),
    ]


def load_plan(root, path):
    path = inside(root, path)
    payload = path.read_bytes()
    plan = json.loads(payload)
    if plan["dataset_revision"] != DATASET_REVISION or plan["model_revision"] != MODEL_REVISION:
        raise ValueError("plan revision differs from the pinned data/model")
    prepared = inside(inside(root, UPSTREAM), inside(root, plan["source_prepared"]))
    if prepared.name != "prepared.json":
        raise ValueError("expected frozen prepared.json")
    prepared_bytes = prepared.read_bytes()
    if hashlib.sha256(prepared_bytes).hexdigest() != plan["source_prepared_sha256"]:
        raise ValueError("prepared SHA mismatch")
    source = prepared.parent.relative_to(root).as_posix()
    manifest = read(prepared.parent, "run-manifest.json")
    inputs = inside(root, manifest["inputs"])
    inputs_sha = sha(inputs)
    required = dict(
        input_track="image-only",
        protocol=PROTOCOL,
        dataset_revision=DATASET_REVISION,
        model_revision=MODEL_REVISION,
        inputs_sha256=inputs_sha,
    )
    if any(manifest[key] != value for key, value in required.items()):
        raise ValueError("source manifest protocol or input SHA mismatch")
    inputs = inputs.relative_to(root).as_posix()
    prepared_data = json.loads(prepared_bytes)
    if prepared_data["status"] != "prepared":
        raise ValueError("source crops are not prepared")
    by_group = defaultdict(dict)
    fragment_ids = set()
    for record in prepared_data["fragments"]:
        fid = record["fragment_id"]
        if fid in fragment_ids:
            raise ValueError("duplicate source fragment")
        fragment_ids.add(fid)
        by_group[record["group_id"]][fid] = record
    if set(by_group) != set(manifest["group_ids"]):
        raise ValueError("source manifest group coverage mismatch")
    groups = set()
    jobs = plan["jobs"]
    names = set()
    for index, job in enumerate(jobs):
        ids = job["group_ids"]
        name = job["run"]
        if (
            job["index"] != index
            or name in names
            or not re.fullmatch(r"\d{8}T\d{6}Z-[A-Za-z0-9_-]{1,90}", name)
            or not 1 <= len(ids) <= min(25, plan["max_groups_per_shard"])
            or len(set(ids)) != len(ids)
            or set(ids) - set(by_group)
            or groups.intersection(ids)
        ):
            raise ValueError("invalid or overlapping shard groups")
        if job["expected_fragments"] != sum(len(by_group[group]) for group in ids):
            raise ValueError("shard fragment count mismatch")
        if job["argv"] != child_argv(root, inputs, source, name, ids, 0):
            raise ValueError("frozen shard argv differs from the known worker contract")
        groups.update(ids)
        names.add(name)
    if (
        not jobs
        or groups != set(by_group)
        or len(groups) != plan["groups"]
        or len(fragment_ids) != plan["fragments"]
        or len(jobs) != plan["shards"]
    ):
        raise ValueError("plan coverage differs from prepared source")
    return Plan(
        path,
        hashlib.sha256(payload).hexdigest(),
        source,
        plan["source_prepared_sha256"],
        inputs,
        inputs_sha,
        plan["research_readiness"],
        jobs,
        by_group,
    )


def verify_shard(root, plan, index, run):
    run = inside(inside(root, UPSTREAM), run)
    job = plan.jobs[index]
    manifest = read(run, "run-manifest.json")
    summary = read(run, "summary.json")
    prepared = read(run, "prepared.json")
    expected = {fid: row for group in job["group_ids"] for fid, row in plan.by_group[group].items()}
    contract = dict(
        group_ids=job["group_ids"],
        inputs_sha256=plan.inputs_sha,
        input_track="image-only",
        protocol=PROTOCOL,
        dataset_revision=DATASET_REVISION,
        model_revision=MODEL_REVISION,
    )
    if any(manifest[key] != value for key, value in contract.items()):
        raise ValueError("shard manifest does not match the frozen plan")
    count = len(expected)
    if (
        (run / "failure.json").exists()
        or summary["status"] != "completed"
        or summary["expected"] != count
        or summary["completed"] != count
        or prepared["status"] != "prepared"
        or len(prepared["fragments"]) != count
    ):
        raise ValueError("shard is absent, failed, or incomplete")
    used_dirs, used_ids = set(), set()
    digests = {}
    identity_fields = (*IDENTITY, "crop_sha256")
    for row in prepared["fragments"]:
        fid = row["fragment_id"]
        if (
            fid not in expected
            or fid in used_ids
            or any(row[k] != expected[fid][k] for k in identity_fields)
        ):
            raise ValueError("duplicate or unexpected prepared fragment identity")
        crop = inside(run, row["crop_relpath"])
        if (
            crop.name != "crop.png"
            or crop.parent.parent != inside(run, "fragments")
            or crop.parent in used_dirs
            or sha(crop) != row["crop_sha256"]
            or read(crop.parent, "source.json") != row
        ):
            raise ValueError("prepared crop identity or SHA mismatch")
        pred = inside(crop.parent, "prediction.json")
        raw = pred.read_bytes()
        result = json.loads(raw)
        if (
            any(result[k] != row[k] for k in IDENTITY)
            or result["status"] != "completed"
            or not isinstance(result["html"], str)
            or not result["html"].strip()
        ):
            raise ValueError("prediction identity mismatch or incomplete fragment")
        used_ids.add(fid)
        used_dirs.add(crop.parent)
        digests[fid] = hashlib.sha256(raw).hexdigest()
    found = {path.parent.resolve() for path in inside(run, "fragments").glob("*/prediction.json")}
    if found != used_dirs:
        raise ValueError("unexpected predictions in shard directory")
    return dict(run=run.relative_to(root).as_posix(), fragments=count, predictions_sha256=digests)


def resumed_runs(root, plan, batches):
    by_index = defaultdict(list)
    for batch in batches:
        directory = inside(inside(root, BATCHES), inside(root, batch))
        manifest = read(directory, "batch.json")
        if manifest["plan_sha256"] != plan.digest:
            raise ValueError("resume batch belongs to a different plan")
        for index in manifest["selected"]:
            if type(index) is not int or not 0 <= index < len(plan.jobs):
                raise ValueError("invalid resume shard index")
            file = directory / f"shard-{index:04d}.json"
            if not file.is_file() and (directory / f"command-{index:04d}.json").is_file():
                # The child may complete just before an interrupted launcher can write its receipt.
                by_index[index].append((UPSTREAM / f"{directory.name}-shard-{index:04d}", None))
                continue
            if not file.is_file():
                continue
            receipt = read(directory, file.name)
            if receipt["index"] != index:
                raise ValueError("resume receipt shard index mismatch")
            if receipt["status"] in ("completed", "reused"):
                by_index[index].append((receipt["run"], receipt["predictions_sha256"]))
    return by_index


def gpu_free_mib(gpu):
    response = subprocess.check_output(
        ["nvidia-smi", f"--id={gpu}", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        text=True,
    )
    return int(response.strip())


def execute(root, plan, selected, prior, batch_run, gpu):
    if not re.fullmatch(r"\d{8}T\d{6}Z-[A-Za-z0-9_-]{1,80}", batch_run):
        raise ValueError("a fresh timestamp batch run is required")
    if len(selected) > 2 and plan.readiness != "G0_reviewed_upstream_expansion_allowed":
        raise ValueError("G0 is pending; use at most two explicit diagnostic shards")
    out = inside(inside(root, BATCHES), batch_run)
    out.mkdir(parents=True, exist_ok=False)
    write(
        out / "batch.json",
        dict(
            plan=plan.path.relative_to(root).as_posix(),
            plan_sha256=plan.digest,
            source_prepared=(Path(plan.source) / "prepared.json").as_posix(),
            source_prepared_sha256=plan.source_sha,
            inputs=plan.inputs,
            inputs_sha256=plan.inputs_sha,
            selected=selected,
            gpu=gpu,
            started_utc=datetime.now(UTC).isoformat(),
        ),
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(inside(root, "src")),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
    }
    for index in selected:
        job = plan.jobs[index]
        receipt = out / f"shard-{index:04d}.json"
        rejected = []
        for candidate, expected_hashes in [*prior.get(index, []), (UPSTREAM / job["run"], None)]:
            run = inside(inside(root, UPSTREAM), inside(root, candidate))
            if run.exists():
                try:
                    verified = verify_shard(root, plan, index, run)
                    if (
                        expected_hashes is not None
                        and verified["predictions_sha256"] != expected_hashes
                    ):
                        raise ValueError("resumed predictions differ from their recorded SHA")
                except (ValueError, KeyError, OSError) as error:
                    rejected.append(dict(run=run.relative_to(root).as_posix(), error=str(error)))
                else:
                    write(
                        receipt, dict(status="reused", index=index, rejected=rejected, **verified)
                    )
                    break
        if receipt.exists():
            continue
        name = f"{batch_run}-shard-{index:04d}"
        run = inside(inside(root, UPSTREAM), name)
        argv = child_argv(root, plan.inputs, plan.source, name, job["group_ids"], gpu)
        # Preserve the pinned venv launcher. Resolving its leaf symlink switches
        # Python to the base interpreter and discards the venv's dependencies.
        python = Path(PADDLE_PYTHON)
        argv[0] = str(inside(root, python.parent) / python.name)
        argv[1] = str(inside(root, SCRIPT))
        write(out / f"command-{index:04d}.json", argv)
        try:
            if run.exists():
                raise FileExistsError(f"fresh shard output already exists: {run.name}")
            if sha(plan.path) != plan.digest or sha(inside(root, plan.inputs)) != plan.inputs_sha:
                raise ValueError("plan or inputs changed since batch preflight")
            if sha(inside(root, Path(plan.source) / "prepared.json")) != plan.source_sha:
                raise ValueError("prepared source changed since batch preflight")
            free_mib = gpu_free_mib(gpu)
            if free_mib < 20000:
                raise RuntimeError(f"GPU {gpu} has {free_mib} MiB free, requires 20000 MiB")
            write(out / f"gpu-{index:04d}.json", dict(gpu=gpu, free_mib=free_mib))
            with (out / f"shard-{index:04d}.log").open("x", encoding="utf-8") as log:
                subprocess.run(
                    argv, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True
                )
            verified = verify_shard(root, plan, index, run)
        except (Exception, KeyboardInterrupt) as error:
            write(
                receipt,
                dict(
                    status="failed",
                    index=index,
                    run=run.relative_to(root).as_posix(),
                    error=f"{type(error).__name__}: {error}",
                    rejected=rejected,
                ),
            )
            raise
        write(receipt, dict(status="completed", index=index, rejected=rejected, **verified))
    write(
        out / "summary.json",
        dict(status="completed", selected=selected, ended_utc=datetime.now(UTC).isoformat()),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--shard", type=int, action="append")
    parser.add_argument("--resume-from", action="append", default=[])
    parser.add_argument("--run")
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    plan = load_plan(root, args.plan)
    selected = args.shard if args.shard is not None else list(range(len(plan.jobs)))
    if len(set(selected)) != len(selected) or any(not 0 <= i < len(plan.jobs) for i in selected):
        parser.error("--shard requires unique, existing indices")
    if args.gpu < 0:
        parser.error("--gpu requires a nonnegative index")
    prior = resumed_runs(root, plan, args.resume_from)
    print(
        json.dumps(
            dict(
                mode="execute" if args.execute else "read_only",
                plan_sha256=plan.digest,
                readiness=plan.readiness,
                selected=selected,
                groups=sum(len(plan.jobs[i]["group_ids"]) for i in selected),
                fragments=sum(plan.jobs[i]["expected_fragments"] for i in selected),
            ),
            ensure_ascii=False,
        ),
        flush=True,
    )
    if args.execute:
        if args.run is None or args.shard is None:
            parser.error("--execute requires --run and explicit --shard arguments")
        execute(root, plan, selected, prior, args.run, args.gpu)


if __name__ == "__main__":
    main()
