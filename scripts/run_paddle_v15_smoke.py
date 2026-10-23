"""Run pinned Paddle v1.5 whole-document train smoke; preserve official raw results."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import random
import re
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def utc():
    return datetime.now(UTC).isoformat()


def run_documents(pipeline, inputs, manifest, output, guard=lambda: None):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    summary = {"started_utc": utc(), "status": "running", "pages": 0, "documents": []}
    try:
        with (output / "pages.jsonl").open("x", encoding="utf-8") as raw:
            for doc in manifest["pdfs"]:
                guard()
                doc_started = time.monotonic()
                doc_dir = output / doc["document_id"]
                doc_dir.mkdir()
                predictions = []
                for result in pipeline.predict_iter(str(inputs / doc["file"])):
                    prediction = result.json
                    expected_index = len(predictions)
                    data = prediction["res"]
                    if data["page_index"] != expected_index:
                        raise ValueError("Page coverage/order mismatch")
                    if data["page_count"] != doc["pages"]:
                        raise ValueError("PDF page_count coverage mismatch")
                    predictions.append(prediction)
                    raw.write(
                        json.dumps(
                            {"document_id": doc["document_id"], "prediction": prediction},
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    raw.flush()
                    summary["pages"] += 1
                    print(
                        json.dumps(
                            {
                                "utc": utc(),
                                "event": "page_complete",
                                "document": doc["document_id"],
                                "page": expected_index,
                                "elapsed": round(time.monotonic() - doc_started, 2),
                            }
                        ),
                        flush=True,
                    )
                    guard()
                if len(predictions) != doc["pages"]:
                    raise ValueError("Document page coverage mismatch")
                counts = {}
                content_counts = {}
                for mode, merge in [("no_merge", False), ("native_merge", True)]:
                    restructured = pipeline.restructure_pages(
                        copy.deepcopy(predictions),
                        merge_tables=merge,
                        relevel_titles=False,
                        concatenate_pages=False,
                    )
                    serial = [item.json for item in restructured]
                    if [p["res"]["page_index"] for p in serial] != list(range(doc["pages"])):
                        raise ValueError("Restructured page coverage/order mismatch")
                    write_json(doc_dir / f"{mode}.json", serial)
                    counts[mode] = sum(
                        b["block_label"] == "table"
                        for p in serial
                        for b in p["res"]["parsing_res_list"]
                    )
                    content_counts[mode] = sum(
                        b["block_label"] == "table" and bool(b["block_content"].strip())
                        for p in serial
                        for b in p["res"]["parsing_res_list"]
                    )
                summary["documents"].append(
                    {
                        "document_id": doc["document_id"],
                        "pages": len(predictions),
                        "seconds": round(time.monotonic() - doc_started, 2),
                        "table_blocks": counts,
                        "nonempty_table_blocks": content_counts,
                    }
                )
                print(
                    json.dumps(
                        {"utc": utc(), "event": "document_complete", **summary["documents"][-1]}
                    ),
                    flush=True,
                )
        summary["status"] = "completed"
        return summary
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        summary["ended_utc"] = utc()
        summary["seconds"] = round(time.monotonic() - started, 2)
        write_json(output / "summary.json", summary)


def gpu_sample(index):
    result = subprocess.run(
        [
            "nvidia-smi",
            f"--id={index}",
            "--query-gpu=index,memory.free,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    values = [int(v.strip()) for v in result.stdout.strip().split(",")]
    return dict(zip(("index", "free_mib", "used_mib", "utilization"), values, strict=True))


def configure_cache(root):
    for key, folder in {
        "PADDLE_PDX_CACHE_HOME": "paddlex",
        "PADDLE_HOME": "paddle",
        "PPNLP_HOME": "paddlenlp",
        "CUDA_CACHE_PATH": "cuda",
        "HF_HOME": "hf",
        "MODELSCOPE_CACHE": "modelscope",
        "XDG_CACHE_HOME": "xdg",
        "TMPDIR": "tmp",
        "MPLCONFIGDIR": "matplotlib",
        "TRITON_CACHE_DIR": "triton",
        "TORCH_HOME": "torch",
        "FLAGS_jit_kernel_cache_path": "paddle-jit",
    }.items():
        path = root / folder
        path.mkdir(parents=True, exist_ok=False)
        os.environ[key] = str(path)
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--vl-model", type=Path, required=True)
    parser.add_argument("--layout-model", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-paddle-train-smoke", args.run_id):
        parser.error("Invalid timestamped smoke run ID")
    project = Path("/data01/public/zhengguojie/paper").resolve()
    for path in (args.inputs, args.vl_model, args.layout_model):
        if not path.resolve().is_relative_to(project) or not path.is_dir():
            parser.error("All inputs and model directories must exist inside the project")
    versions = {
        name: importlib.metadata.version(name)
        for name in ("paddleocr", "paddlex", "paddlepaddle-gpu", "numpy")
    }
    for name, expected in [
        ("paddleocr", "3.4.0"),
        ("paddlex", "3.4.1"),
        ("paddlepaddle-gpu", "3.2.1"),
        ("numpy", "1.26.4"),
    ]:
        if versions[name] != expected:
            raise RuntimeError(f"Unexpected {name} version: {versions[name]}")
    inputs = args.inputs.resolve()
    manifest_path = inputs / "packing-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if (
        manifest["pdf_text_audit"] != "empty"
        or manifest["embedded_image_audit"] != "byte-identical"
    ):
        raise ValueError("Expected audited image-only input")
    for doc in manifest["pdfs"]:
        path = (inputs / doc["file"]).resolve()
        if not path.is_relative_to(inputs):
            raise ValueError("PDF path escapes input directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != doc["sha256"]:
            raise ValueError("Packed input PDF SHA mismatch")
    before = gpu_sample(args.gpu)
    if before["free_mib"] < 20000:
        raise RuntimeError(f"Preflight requires 20000 MiB free: {before}")
    output = project / "outputs/baselines/paddleocr-vl-1.5" / args.run_id
    log = project / "logs/baselines/paddleocr-vl-1.5" / args.run_id
    if output.exists() or log.exists():
        raise FileExistsError("Run paths already exist; use a new run ID")
    log.mkdir(parents=True, exist_ok=False)
    configure_cache(log / "cache")
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    write_json(
        log / "run-manifest.json",
        {
            "started_utc": utc(),
            "versions": versions,
            "seed": 0,
            "input_track": "image-only",
            "split": "train",
            "data_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
            "input_manifest": str(manifest_path),
            "input_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "vl_model": str(args.vl_model.resolve()),
            "layout_model": str(args.layout_model.resolve()),
            "vl_model_revision": "2a4195faa5e7914c12f2fc601d72c81caf8d2da5",
            "layout_model_revision": "241f8bdfc77a7c7bee915a5057aaee58c235a8d3",
            "gpu_before": before,
            "generation_parameters": "official defaults",
            "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        },
    )
    stop = threading.Event()

    def monitor():
        with (log / "gpu-samples.jsonl").open("x") as handle:
            while not stop.is_set():
                try:
                    handle.write(json.dumps({"utc": utc(), **gpu_sample(args.gpu)}) + "\n")
                    handle.flush()
                except Exception as exc:
                    print(f"GPU telemetry error: {exc}", flush=True)
                stop.wait(5)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    try:
        import numpy as np
        import paddle
        from paddleocr import PaddleOCRVL
        from paddlex.inference import load_pipeline_config

        random.seed(0)
        np.random.seed(0)
        paddle.seed(0)
        if not paddle.is_compiled_with_cuda():
            raise RuntimeError("Paddle wheel has no CUDA support")
        config = load_pipeline_config("PaddleOCR-VL-1.5")
        config["batch_size"] = 1
        config["SubModules"]["LayoutDetection"]["batch_size"] = 1
        config["SubModules"]["VLRecognition"]["batch_size"] = 1
        pipeline = PaddleOCRVL(
            pipeline_version="v1.5",
            paddlex_config=config,
            device="gpu:0",
            layout_detection_model_dir=str(args.layout_model.resolve()),
            vl_rec_model_dir=str(args.vl_model.resolve()),
            vl_rec_backend="native",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_layout_detection=True,
            use_chart_recognition=False,
            use_seal_recognition=False,
            use_ocr_for_image_block=False,
            format_block_content=False,
            use_queues=False,
        )
        pipeline.export_paddlex_config_to_yaml(str(log / "pipeline-config.yaml"))

        def guard():
            sample = gpu_sample(args.gpu)
            if sample["free_mib"] < 8192:
                raise RuntimeError(f"Shared GPU safety stop: {sample}")

        summary = run_documents(pipeline, inputs, manifest, output, guard)
        print(json.dumps(summary), flush=True)
    except Exception as exc:
        write_json(log / "failure.json", {"utc": utc(), "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        stop.set()
        monitor_thread.join(timeout=10)


if __name__ == "__main__":
    main()
