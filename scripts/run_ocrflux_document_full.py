"""Immutable per-document OCRFlux runs and hash-verified checkpoint recovery."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from cptla.evaluation.document_run import (
    canonical_manifest_bytes,
    digest,
    read_frozen_manifest,
    run_batch,
    write_new_json,
)


def validate_child(child, doc):
    summary = json.loads((child / "summary.json").read_text())
    saved = json.loads((child / (doc["document_id"] + ".json")).read_text())
    if (
        summary["status"] != "completed"
        or summary["documents"] != [doc["document_id"]]
        or summary["pages"] != doc["pages"]
        or saved["document_id"] != doc["document_id"]
        or len(saved["pages"]) != doc["pages"]
    ):
        raise ValueError("Native document coverage mismatch")
    return {
        **doc,
        "prediction_dir": str(child.resolve()),
        "files": {str(p.resolve()): digest(p) for p in child.rglob("*") if p.is_file()},
    }


def native_environment(project, log, source):
    log.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    prefix = project / ".venvs/20261029T162200Z-ocrflux"
    env.update(
        CUDA_VISIBLE_DEVICES="0",
        PYTHONNOUSERSITE="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        VLLM_WORKER_MULTIPROC_METHOD="spawn",
        VLLM_USE_V1="0",
        VLLM_NO_USAGE_STATS="1",
        DO_NOT_TRACK="1",
        PYTHONPATH=str(source / "src"),
    )
    env["PATH"] = str(prefix / "bin") + os.pathsep + env.get("PATH", "")
    for key in [
        "TMPDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "HF_HOME",
        "TORCH_HOME",
        "TRITON_CACHE_DIR",
        "NUMBA_CACHE_DIR",
        "VLLM_CACHE_ROOT",
        "VLLM_CONFIG_ROOT",
        "CUDA_CACHE_PATH",
        "TORCH_EXTENSIONS_DIR",
        "TORCHINDUCTOR_CACHE_DIR",
        "FLASHINFER_WORKSPACE_DIR",
        "MPLCONFIGDIR",
        "NLTK_DATA",
    ]:
        folder = log / key.lower()
        folder.mkdir()
        env[key] = str(folder)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha", required=True)
    parser.add_argument("--expected-pages", type=int, required=True)
    parser.add_argument("--expected-documents", type=int, required=True)
    parser.add_argument("--split", choices=["train", "val"], required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume", type=Path, action="append", default=[])
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    source = Path(__file__).resolve().parent.parent
    for path in [args.images, args.manifest, source, *args.resume]:
        if not path.resolve().is_relative_to(project):
            raise ValueError("Path outside project")
    if not re.fullmatch(r"[a-zA-Z0-9-]+", args.run_id):
        raise ValueError("Invalid run ID")
    documents = read_frozen_manifest(
        args.manifest,
        args.images,
        args.manifest_sha,
        args.expected_pages,
        args.expected_documents,
        complete_directory=args.split == "val",
    )
    if args.split == "val" and (
        args.expected_pages != 13871
        or args.expected_documents != 935
        or args.manifest_sha != "2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd"
    ):
        raise ValueError("Validation protocol is fixed")
    model = project / "models/20261023T064109Z-public-models/ocrflux-3b"
    pinned = json.loads((model / "download-manifest.json").read_text())
    if (
        pinned["status"] != "complete"
        or pinned["revision"] != "e68592278bbc8ab32edf7b65e6e411f1d878ef72"
        or not pinned["verified"]
    ):
        raise ValueError("Model revision mismatch")
    for item in pinned["verified"]:
        path = (model / item["file"]).resolve()
        if (
            not path.is_relative_to(model)
            or path.stat().st_size != item["size"]
            or digest(path) != item["sha256"]
        ):
            raise ValueError("Model integrity mismatch")
    native = project / ".venvs/20261029T162200Z-ocrflux/bin/python"
    installed = Path(
        subprocess.check_output(
            [
                str(native),
                "-c",
                "import importlib.util; "
                'print(next(iter(importlib.util.find_spec("ocrflux").submodule_search_locations)))',
            ],
            text=True,
            cwd=project,
        ).strip()
    ).resolve()
    if not installed.is_relative_to(project):
        raise ValueError("Official installed package outside project")
    official_hashes = {}
    for name in ["inference.py", "prompts.py", "image_utils.py", "table_format.py"]:
        actual = digest(installed / name)
        expected = digest(project / "artifacts/ocrflux-prep/20261029T162000Z/source/ocrflux" / name)
        if actual != expected:
            raise ValueError("Installed official code differs from pinned source")
        official_hashes[name] = actual
    freeze = subprocess.check_output([str(native), "-m", "pip", "freeze"], text=True, cwd=project)
    files = [
        source / "scripts" / name
        for name in [
            "run_ocrflux_document.py",
            "run_ocrflux_document_full.py",
            "adapt_ocrflux_document_predictions.py",
            "pack_pubtables_document_images.py",
        ]
    ]
    files += [
        source / "src/cptla/evaluation" / name
        for name in ["ocrflux_document.py", "document_run.py", "contracts.py"]
    ]
    protocol = {
        "name": "OCRFlux-official-API-instrumented",
        "split": args.split,
        "track": "image-only",
        "seed": 0,
        "data_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
        "manifest_sha": args.manifest_sha,
        "numeric_manifest_sha": hashlib.sha256(
            canonical_manifest_bytes(args.manifest, args.manifest_sha)
        ).hexdigest(),
        "model_manifest_sha": digest(model / "download-manifest.json"),
        "environment_sha": hashlib.sha256(freeze.encode()).hexdigest(),
        "official_sha": official_hashes,
        "source_sha": {str(p.relative_to(source)): digest(p) for p in files},
    }
    if args.preflight:
        print(
            json.dumps(
                {
                    "status": "input_protocol_verified",
                    "documents": len(documents),
                    "pages": sum(d["pages"] for d in documents),
                    "protocol": protocol,
                }
            )
        )
        return
    output = project / "artifacts/ocrflux-document-runs" / args.run_id

    def worker(doc):
        identifier = doc["document_id"]
        folder = output / "documents" / identifier
        folder.mkdir(parents=True)
        inputs, predictions = folder / "inputs", folder / "predictions"
        subprocess.run(
            [
                sys.executable,
                str(source / "scripts/pack_pubtables_document_images.py"),
                "--images",
                str(args.images),
                "--documents",
                identifier,
                "--output-dir",
                str(inputs),
            ],
            check=True,
        )
        env = native_environment(project, folder / "runtime", source)
        command = [
            str(native),
            "-u",
            str(source / "scripts/run_ocrflux_document.py"),
            "--inputs",
            str(inputs),
            "--output-dir",
            str(predictions),
            "--model",
            str(model),
        ]
        write_new_json(folder / "command.json", {"command": command, "protocol": protocol})
        with (folder / "native.log").open("x") as log:
            subprocess.run(
                command, cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT, check=True
            )
        result = validate_child(predictions, doc)
        result["files"].update(
            {str(p.resolve()): digest(p) for p in inputs.rglob("*") if p.is_file()}
        )
        return result

    summary = run_batch(documents, output, protocol, worker, project=project, resume=args.resume)
    exported = output / "exported-predictions"
    exported.mkdir()
    for doc in documents:
        result = summary["results"][doc["document_id"]]
        for path, sha in result["files"].items():
            if digest(Path(path)) != sha:
                raise ValueError("Artifact changed before export")
        name = doc["document_id"] + ".json"
        with (exported / name).open("xb") as handle:
            handle.write((Path(result["prediction_dir"]) / name).read_bytes())
        checkpoint = output / "checkpoints" / name
        if not checkpoint.exists():
            write_new_json(checkpoint, {"protocol": protocol, "document": doc, "result": result})
    subprocess.run(
        [
            sys.executable,
            str(source / "scripts/adapt_ocrflux_document_predictions.py"),
            "--manifest",
            str(args.manifest),
            "--predictions",
            str(exported),
            "--output-dir",
            str(output / "adapted"),
        ],
        check=True,
    )
    write_new_json(
        output / "export-complete.json",
        {"status": "completed", "adapted_audit_sha": digest(output / "adapted/audit.json")},
    )


if __name__ == "__main__":
    main()
