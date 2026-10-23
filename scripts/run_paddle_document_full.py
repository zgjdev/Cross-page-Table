"""Frozen full-validation orchestration; immutable per-document native worker runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from cptla.evaluation.document_run import (
    canonical_manifest_bytes,
    digest,
    read_frozen_manifest,
    run_batch,
    write_new_json,
)

MANIFEST = (
    "artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/"
    "dots-full-documents-val-full.jsonl"
)
MANIFEST_SHA = "2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd"
WORKER_PYTHON = ".venvs/paddle-v15-20261023T081029Z-paddle-v15/bin/python"
VL_MODEL = "models/20261023T064109Z-public-models/paddleocr-vl-1.5"
LAYOUT_MODEL = "models/20261023T081029Z-paddle-layout/pp-doclayoutv3"


def verify_model(directory, revision):
    manifest = json.loads((directory / "download-manifest.json").read_text())
    if manifest["status"] != "complete" or manifest["revision"] != revision:
        raise ValueError("Model download manifest not complete/pinned")
    if not manifest["verified"]:
        raise ValueError("Empty model file list")
    for item in manifest["verified"]:
        path = (directory / item["file"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("Model file path escapes project model directory")
        if path.stat().st_size != item["size"] or digest(path) != item["sha256"]:
            raise ValueError(f"Model file integrity mismatch: {item['file']}")
    return digest(directory / "download-manifest.json")


def validate_child(prediction, inputs, doc, split, project):
    summary = json.loads((prediction / "summary.json").read_text())
    log = project / "logs/baselines/paddleocr-vl-1.5" / prediction.name
    metadata = json.loads((log / "run-manifest.json").read_text())
    packing = json.loads((inputs / "packing-manifest.json").read_text())
    if (
        summary["status"] != "completed"
        or summary["pages"] != doc["pages"]
        or [d["document_id"] for d in summary["documents"]] != [doc["document_id"]]
    ):
        raise ValueError("Native worker did not complete the requested document")
    if (
        metadata["split"] != split
        or metadata["input_track"] != "image-only"
        or metadata["input_manifest_sha256"] != digest(inputs / "packing-manifest.json")
        or metadata["vl_model_revision"] != "2a4195faa5e7914c12f2fc601d72c81caf8d2da5"
        or metadata["layout_model_revision"] != "241f8bdfc77a7c7bee915a5057aaee58c235a8d3"
        or metadata["data_revision"] != "aa575e798cb00a296925e2086addb3e3fd9a1903"
    ):
        raise ValueError("Native worker provenance differs from fixed protocol")
    if (
        packing["pdf_text_audit"] != "empty"
        or packing["embedded_image_audit"] != "byte-identical"
        or [p["document_id"] for p in packing["pdfs"]] != [doc["document_id"]]
    ):
        raise ValueError("Native worker did not use the audited image-only document")
    rows = [json.loads(s) for s in (prediction / "pages.jsonl").read_text().splitlines()]
    expected = [(doc["document_id"], i) for i in range(doc["pages"])]
    if [(r["document_id"], r["prediction"]["res"]["page_index"]) for r in rows] != expected:
        raise ValueError("Native worker raw page coverage mismatch")
    paths = [
        prediction / "summary.json",
        prediction / "pages.jsonl",
        log / "run-manifest.json",
        log / "pipeline-config.yaml",
        inputs / "packing-manifest.json",
        inputs / "input-manifest.jsonl",
    ]
    for mode in ("no_merge", "native_merge"):
        path = prediction / doc["document_id"] / f"{mode}.json"
        pages = json.loads(path.read_text())
        if [p["res"]["page_index"] for p in pages] != list(range(doc["pages"])):
            raise ValueError("Native worker restructured page coverage mismatch")
        paths.append(path)
    paths.extend(inputs / p["file"] for p in packing["pdfs"])
    return {
        **doc,
        "prediction_dir": str(prediction.resolve()),
        "input_dir": str(inputs.resolve()),
        "files": {str(p.resolve()): digest(p) for p in paths},
    }


def export_complete_batch(output, summary, manifest, documents, *, expected_manifest_sha):
    """Create a fresh scoring-compatible view; never move/delete original per-doc runs."""
    manifest_blob = canonical_manifest_bytes(manifest, expected_manifest_sha)
    expected = [(d["document_id"], i) for d in documents for i in range(d["pages"])]
    if [
        (r["document_id"], r["page_number"])
        for r in (json.loads(line) for line in manifest_blob.splitlines())
    ] != expected:
        raise ValueError("Export manifest differs from completed document coverage")
    inputs, predictions = output / "exported-inputs", output / "exported-predictions"
    inputs.mkdir()
    predictions.mkdir()
    with (inputs / "input-manifest.jsonl").open("xb") as handle:
        handle.write(manifest_blob)
    packing = {
        "pdf_text_audit": "empty",
        "embedded_image_audit": "byte-identical",
        "pdfs": [],
        "pages": [],
    }
    with (predictions / "pages.jsonl").open("xb") as raw:
        for doc in documents:
            result = summary["results"][doc["document_id"]]
            for name, checksum in result["files"].items():
                if digest(Path(name)) != checksum:
                    raise ValueError("Checkpoint artifact changed before final export")
            source = Path(result["prediction_dir"])
            packed_input = Path(result["input_dir"])
            original = json.loads((packed_input / "packing-manifest.json").read_text())
            for pdf in original["pdfs"]:
                packing["pdfs"].append({**pdf, "file": str((packed_input / pdf["file"]).resolve())})
            packing["pages"].extend(original["pages"])
            raw.write((source / "pages.jsonl").read_bytes())
            dest = predictions / doc["document_id"]
            dest.mkdir()
            for mode in ("no_merge", "native_merge"):
                with (dest / f"{mode}.json").open("xb") as handle:
                    handle.write((source / doc["document_id"] / f"{mode}.json").read_bytes())
    write_new_json(inputs / "packing-manifest.json", packing)
    write_new_json(
        predictions / "summary.json",
        {"status": "completed", "pages": summary["pages"], "documents": documents},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--resume-from", type=Path, nargs="*", default=[])
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--pilot-train-manifest", type=Path)
    args = parser.parse_args()
    project = Path("/data01/public/zhengguojie/paper").resolve()
    if Path.cwd().resolve() != project:
        parser.error("Run only from the server project root")
    split = "train" if args.pilot_train_manifest else "val"
    suffix = "train-pilot" if split == "train" else "val-full"
    if not re.fullmatch(rf"[0-9]{{8}}T[0-9]{{6}}Z-paddle-{suffix}", args.run_id):
        parser.error("Run ID does not match the selected split")
    manifest = args.pilot_train_manifest or project / MANIFEST
    if not manifest.resolve().is_relative_to(project):
        parser.error("Manifest outside project")
    images = project / "data/pubtables-v2/extracted/Full Documents" / split / "images"
    if split == "val":
        sha, page_count, document_count = MANIFEST_SHA, 13871, 935
    else:
        rows = [json.loads(line) for line in manifest.read_text().splitlines()]
        sha, page_count = digest(manifest), len(rows)
        document_count = len({r["document_id"] for r in rows})
    documents = read_frozen_manifest(
        manifest, images, sha, page_count, document_count, complete_directory=(split == "val")
    )
    if shutil.disk_usage(project).free < 100 * 1024**3:
        raise RuntimeError("Need at least 100 GiB free on the shared filesystem")
    worker_python = project / WORKER_PYTHON
    versions = json.loads(
        subprocess.check_output(
            [
                str(worker_python),
                "-c",
                "import importlib.metadata as m,json;"
                "print(json.dumps({n:m.version(n) for n in "
                '["paddleocr","paddlex","paddlepaddle-gpu","numpy"]}))',
            ],
            text=True,
        )
    )
    if versions != {
        "paddleocr": "3.4.0",
        "paddlex": "3.4.1",
        "paddlepaddle-gpu": "3.2.1",
        "numpy": "1.26.4",
    }:
        raise ValueError("Runtime no longer matches tested dependency versions")
    protocol = {
        "split": split,
        "input_track": "image-only",
        "manifest_sha256": sha,
        "ordered_manifest_sha256": hashlib.sha256(
            canonical_manifest_bytes(manifest, sha)
        ).hexdigest(),
        "data_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
        "versions": versions,
        "seed": 0,
        "gpu": args.gpu,
        "vl_manifest_sha256": verify_model(
            project / VL_MODEL, "2a4195faa5e7914c12f2fc601d72c81caf8d2da5"
        ),
        "layout_manifest_sha256": verify_model(
            project / LAYOUT_MODEL, "241f8bdfc77a7c7bee915a5057aaee58c235a8d3"
        ),
        "worker_sha256": digest(project / "scripts/run_paddle_v15_smoke.py"),
        "packer_sha256": digest(project / "scripts/pack_pubtables_document_images.py"),
        "orchestrator_sha256": digest(Path(__file__)),
        "checkpoint_sha256": digest(project / "src/cptla/evaluation/document_run.py"),
    }
    gpu = subprocess.check_output(
        [
            "nvidia-smi",
            f"--id={args.gpu}",
            "--query-gpu=index,memory.free,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        text=True,
    ).strip()
    if int(gpu.split(",")[1].strip()) < 20000:
        raise RuntimeError("Shared GPU has less than 20000 MiB free")
    gpu_uuid = subprocess.check_output(
        ["nvidia-smi", f"--id={args.gpu}", "--query-gpu=uuid", "--format=csv,noheader"], text=True
    ).strip()
    processes = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ],
        text=True,
    ).splitlines()
    preflight = {
        "status": "ready",
        "documents": len(documents),
        "pages": page_count,
        "protocol": protocol,
        "gpu_snapshot": gpu,
        "gpu_compute_processes": [line for line in processes if line.startswith(gpu_uuid + ",")],
        "note": "readiness snapshot, not an exclusive GPU reservation",
    }
    print(json.dumps(preflight), flush=True)
    if args.preflight:
        return
    output = project / "artifacts/paddle-document-runs" / args.run_id
    if output.exists():
        raise FileExistsError(output)
    resume = [p.resolve() for p in args.resume_from]

    def worker(doc):
        identifier = doc["document_id"]
        child_condition = "train-smoke" if split == "train" else "val-full"
        child_id = args.run_id[:16] + f"-paddle-{child_condition}-{identifier}"
        inputs = output / "inputs" / identifier
        subprocess.run(
            [
                str(project / ".venvs/eval312/bin/python"),
                "scripts/pack_pubtables_document_images.py",
                "--images",
                str(images),
                "--documents",
                identifier,
                "--output-dir",
                str(inputs),
            ],
            check=True,
        )
        command = [
            str(worker_python),
            "-u",
            "scripts/run_paddle_v15_smoke.py",
            "--inputs",
            str(inputs),
            "--vl-model",
            str(project / VL_MODEL),
            "--layout-model",
            str(project / LAYOUT_MODEL),
            "--gpu",
            str(args.gpu),
            "--run-id",
            child_id,
            "--split",
            split,
        ]
        with (output / f"{identifier}.log").open("x") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        prediction = project / "outputs/baselines/paddleocr-vl-1.5" / child_id
        return validate_child(prediction, inputs, doc, split, project)

    try:
        summary = run_batch(documents, output, protocol, worker, project=project, resume=resume)
        export_complete_batch(
            output, summary, manifest, documents, expected_manifest_sha=protocol["manifest_sha256"]
        )
        write_new_json(
            output / "export-complete.json",
            {
                "pages": summary["pages"],
                "manifest_sha256": digest(output / "exported-inputs/input-manifest.jsonl"),
            },
        )
    finally:
        if output.exists():
            write_new_json(output / "preflight.json", preflight)


if __name__ == "__main__":
    main()
