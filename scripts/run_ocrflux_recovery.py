"""User-authorized bounded recovery of unchanged OCRFlux validation protocol."""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from cptla.evaluation.ocrflux_recovery import initialization_retry_allowed, recovery_next


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--supervisor-id", required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    if not args.supervisor_id.replace("-", "").isalnum():
        raise ValueError("Invalid supervisor ID")
    stage = project / "artifacts/ocrflux-prep/20261030T015400Z/full-source-v3"
    old = project / "artifacts/ocrflux-document-runs/20261030T032500Z-ocrflux-val-full"
    expected = json.loads(
        (
            project
            / "artifacts/ocrflux-prep/20261030T015400Z/acceptance/final-full-preflight-v3.json"
        ).read_text()
    )
    for relative, sha in expected["protocol"]["source_sha"].items():
        if hashlib.sha256((stage / relative).read_bytes()).hexdigest() != sha:
            raise ValueError("Frozen source changed")
    log = project / "logs/ocrflux-recovery" / args.supervisor_id
    log.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        with (log / name).open("x") as h:
            json.dump(value, h, indent=2)

    env = os.environ.copy()
    env.update(PYTHONPATH=str(stage / "src"), PYTHONNOUSERSITE="1")
    common = [
        sys.executable,
        "-u",
        str(stage / "scripts/run_ocrflux_document_full.py"),
        "--project",
        str(project),
        "--images",
        str(project / "data/pubtables-v2/extracted/Full Documents/val/images"),
        "--manifest",
        str(
            project
            / "artifacts/input-manifests/20260921T071841Z-smoke-input-manifests"
            / "dots-full-documents-val-full.jsonl"
        ),
        "--manifest-sha",
        "2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd",
        "--expected-pages",
        "13871",
        "--expected-documents",
        "935",
        "--split",
        "val",
    ]
    resumes = [old]
    retry_counts = {}
    save(
        "supervisor.json",
        {
            "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "initial_resume": str(old),
            "command_base": common,
            "initialization_retries_per_document": 3,
            "maximum_recoveries": 20,
            "inference_protocol_changed": False,
        },
    )
    # Permit recovery only when the previous failure has the known safe signature.
    previous = old
    attempt = 0
    while True:
        summary = json.loads((previous / "summary.json").read_text())
        manifest = json.loads((previous / "run-manifest.json").read_text())
        pending = next(
            d for d in manifest["documents"] if d["document_id"] not in summary["results"]
        )
        document = pending["document_id"]
        child = previous / "documents" / document / "predictions"
        failed = json.loads((child / "summary.json").read_text())
        raw_count = sum(1 for f in (child / "raw").glob("*.json") if not f.name.startswith("."))
        if not initialization_retry_allowed(failed, raw_count):
            raise RuntimeError("Failure is not a pre-generation memory-profiling assertion")
        retry_counts = recovery_next(retry_counts, document)
        # Wait for five consecutive free-memory samples within 512MiB and >=30000MiB.
        samples = []
        stable = []
        for _ in range(24):
            free = int(
                subprocess.check_output(
                    [
                        "nvidia-smi",
                        "-i",
                        "0",
                        "--query-gpu=memory.free",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                ).strip()
            )
            samples.append(free)
            stable = (stable + [free])[-5:]
            if len(stable) == 5 and min(stable) >= 30000 and max(stable) - min(stable) <= 512:
                break
            time.sleep(5)
        else:
            save(f"gpu-not-stable-{attempt:03d}.json", samples)
            raise RuntimeError("GPU not stable/available within bounded wait")
        attempt += 1
        identifier = f"{args.supervisor_id}-a{attempt:03d}"
        output = project / "artifacts/ocrflux-document-runs" / identifier
        command = common + ["--run-id", identifier]
        for source in resumes:
            command += ["--resume", str(source)]
        save(
            f"attempt-{attempt:03d}.json",
            {
                "run_id": identifier,
                "command": command,
                "gpu_free_samples": samples,
                "retry_counts": retry_counts,
                "source_failure": str(previous),
                "failed_document": document,
                "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
                "processes": subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-compute-apps=gpu_uuid,pid,used_memory",
                        "--format=csv,noheader",
                    ],
                    text=True,
                ),
            },
        )
        print(
            json.dumps(
                {"event": "recovery_start", "run_id": identifier, "failed_document": document}
            ),
            flush=True,
        )
        with (log / f"attempt-{attempt:03d}.log").open("x") as handle:
            result = subprocess.run(
                command, cwd=project, env=env, stdout=handle, stderr=subprocess.STDOUT
            )
        save(
            f"exit-{attempt:03d}.json",
            {
                "returncode": result.returncode,
                "ended_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            },
        )
        if result.returncode == 0:
            if not (output / "export-complete.json").exists():
                raise RuntimeError("No complete export")
            save("completed.json", {"run_id": identifier, "status": "completed"})
            return
        if not (output / "summary.json").exists():
            raise RuntimeError("Failed before run summary; will not blindly retry")
        previous = output
        # Failed runs hold only newly completed checkpoints, so add each once.
        resumes.append(output)


if __name__ == "__main__":
    main()
