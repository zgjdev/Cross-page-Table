"""从 R0 的 train_fit 或显式隔离的 train_dev 生成 Paddle 局部预测。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from cptla.evaluation.pubtables_v2 import parse_full_document_image_id
from cptla.reconstruction.data import DATASET_REVISION, PROTOCOL, TRAIN_RELATIVE_PATH

MODEL = "models/20261023T064109Z-public-models/paddleocr-vl-1.5"
MODEL_REVISION = "2a4195faa5e7914c12f2fc601d72c81caf8d2da5"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def inside(root, path):
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError("path escapes project")
    return result


def failure(output, exc):
    write(
        output / "failure.json",
        {
            "status": "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
            "utc": datetime.now(UTC).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
        },
    )


def prepare(
    root, inputs, run, groups, reuse_prepared_run=None, *, split="train_fit", document_overlay=None
):
    root = root.resolve()
    inputs = inside(root, inputs)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run):
        raise ValueError("unsafe run identity")
    if not groups or len(groups) != len(set(groups)):
        raise ValueError("explicit unique group IDs required")
    if split not in {"train_fit", "train_dev"}:
        raise ValueError("only train_fit and train_dev are supported")
    if split == "train_dev" and document_overlay is None:
        raise ValueError("train_dev requires a document overlay")
    output = inside(root, Path("artifacts/reconstruction-upstream") / run)
    output.mkdir(parents=True, exist_ok=False)
    try:
        input_sha = sha(inputs)
        with inputs.open(encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        by_id = {}
        for row in rows:
            if row["group_id"] in by_id:
                raise ValueError("duplicate input group")
            by_id[row["group_id"]] = row
        overlay_sha = None
        if document_overlay is not None:
            document_overlay = inside(root, document_overlay)
            raw_overlay = document_overlay.read_bytes()
            overlay_sha = hashlib.sha256(raw_overlay).hexdigest()
            entries = [json.loads(line) for line in raw_overlay.split(b"\n") if line.strip()]
            by_document = {row["document_id"]: row for row in entries}
            if len(entries) != len(by_document):
                raise ValueError("duplicate document overlay entries")
            for group in groups:
                source_row = by_id[group]
                entry = by_document.get(source_row["document_id"], {})
                if (
                    entry.get("effective_split") != split
                    or entry.get("cluster_id") != source_row["cluster_id"]
                    or (split == "train_dev" and entry.get("observed_cluster") is not False)
                ):
                    raise ValueError("group is excluded by the document overlay")
        write(
            output / "run-manifest.json",
            dict(
                started_utc=datetime.now(UTC).isoformat(),
                input_track="image-only",
                split=split,
                document_overlay=str(document_overlay) if document_overlay is not None else None,
                document_overlay_sha256=overlay_sha,
                protocol=PROTOCOL,
                dataset_revision=DATASET_REVISION,
                inputs=str(inputs),
                inputs_sha256=input_sha,
                code_sha256=sha(Path(__file__)),
                code_commit=subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip(),
                python=platform.python_version(),
                seed=0,
                group_ids=groups,
                model_revision=MODEL_REVISION,
                argv=sys.argv,
                training_allowed=False,
            ),
        )
        reused_files = {}
        reused = {}
        provenance = None
        if reuse_prepared_run is not None:
            old = inside(root, Path(reuse_prepared_run))
            prepared_path = inside(root, old / "prepared.json")
            manifest_path = inside(root, old / "run-manifest.json")
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes)
            for key, expected in [
                ("inputs_sha256", input_sha),
                ("dataset_revision", DATASET_REVISION),
                ("protocol", PROTOCOL),
                ("input_track", "image-only"),
            ]:
                if manifest.get(key) != expected:
                    raise ValueError(f"reuse manifest {key} mismatch")
            prepared_bytes = prepared_path.read_bytes()
            prepared = json.loads(prepared_bytes)
            if prepared.get("status") != "prepared":
                raise ValueError("reuse requires prepared status")
            provenance = dict(
                run=str(old),
                prepared_sha256=hashlib.sha256(prepared_bytes).hexdigest(),
                manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            )
            for record in prepared["fragments"]:
                identity = (record["group_id"], record["fragment_id"])
                if identity in reused:
                    raise ValueError("duplicate reused fragment identity")
                reused[identity] = record
            for group in groups:
                expected = {(group, f["fragment_id"]) for f in by_id[group]["fragments"]}
                actual = {key for key in reused if key[0] == group}
                if actual != expected:
                    raise ValueError("reuse selected fragment coverage mismatch")
        records = []
        identities = set()
        image_root = inside(root, TRAIN_RELATIVE_PATH / "images")
        for group in groups:
            row = by_id[group]
            for key, expected in [
                ("source_split", "train"),
                ("split", split),
                ("dataset_revision", DATASET_REVISION),
                ("protocol", PROTOCOL),
            ]:
                if row.get(key) != expected:
                    raise ValueError(f"invalid {key}")
            if not row["fragments"]:
                raise ValueError("empty fragments")
            for fragment in row["fragments"]:
                identity = (group, fragment["fragment_id"])
                if identity in identities:
                    raise ValueError("duplicate fragment identity")
                identities.add(identity)
                source = inside(root, Path(fragment["image_relpath"]))
                if not source.is_relative_to(image_root) or sha(source) != fragment["image_sha256"]:
                    raise ValueError("source location/SHA mismatch")
                document_id, page_num = parse_full_document_image_id(source.name)
                part_index = fragment["part_index"]
                if (
                    document_id != row["document_id"]
                    or type(fragment["page_num"]) is not int
                    or page_num != fragment["page_num"]
                    or type(part_index) is not int
                    or part_index < 0
                    or fragment["fragment_id"] != f"{group}-part-{part_index}"
                ):
                    raise ValueError("fragment/image source identity mismatch")
                box = fragment["crop_box"]
                with Image.open(source) as image:
                    width, height = image.size
                    if (
                        list(image.size) != fragment["image_size"]
                        or len(box) != 4
                        or any(type(v) is not int for v in box)
                        or not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)
                    ):
                        raise ValueError("crop dimensions/bounds mismatch")
                    directory = output / "fragments" / f"{len(records):06d}"
                    directory.mkdir(parents=True)
                    crop = directory / "crop.png"
                    if reuse_prepared_run is None:
                        with crop.open("xb") as stream:
                            image.crop(tuple(box)).save(stream, format="PNG")
                    else:
                        previous = reused[identity]
                        expected_fields = dict(
                            group_id=group,
                            document_id=row["document_id"],
                            **fragment,
                            orientation="preserve_original",
                            crop_size=[box[2] - box[0], box[3] - box[1]],
                        )
                        if any(previous.get(k) != v for k, v in expected_fields.items()):
                            raise ValueError("reuse source identity mismatch")
                        old_crop = inside(root, old / previous["crop_relpath"])
                        if (
                            not old_crop.is_relative_to(old / "fragments")
                            or old_crop.name != "crop.png"
                        ):
                            raise ValueError("reuse crop escapes run")
                        source_path = inside(root, old_crop.parent / "source.json")
                        if not source_path.is_relative_to(old):
                            raise ValueError("reuse source escapes run")
                        source_bytes = source_path.read_bytes()
                        if json.loads(source_bytes) != previous:
                            raise ValueError("reuse prepared/source mismatch")
                        if sha(old_crop) != previous["crop_sha256"]:
                            raise ValueError("reuse crop SHA mismatch")
                        source_sha = hashlib.sha256(source_bytes).hexdigest()
                        reused_files[source_path] = source_sha
                        reused_files[old_crop] = previous["crop_sha256"]
                        with old_crop.open("rb") as src, crop.open("xb") as dst:
                            shutil.copyfileobj(src, dst)
                        if sha(crop) != previous["crop_sha256"] or sha(source_path) != source_sha:
                            raise ValueError("reuse files changed during copy")
                        with Image.open(crop) as copied:
                            if list(copied.size) != expected_fields["crop_size"]:
                                raise ValueError("reuse crop size mismatch")
                        write(
                            directory / "reuse-source.json",
                            dict(
                                **provenance,
                                source_path=str(source_path),
                                source_sha256=source_sha,
                                crop_path=str(old_crop),
                                crop_sha256=previous["crop_sha256"],
                            ),
                        )
                if sha(source) != fragment["image_sha256"]:
                    raise ValueError("source changed during crop")
                record = dict(
                    group_id=group,
                    document_id=row["document_id"],
                    **fragment,
                    orientation="preserve_original",
                    crop_size=[box[2] - box[0], box[3] - box[1]],
                    crop_relpath=crop.relative_to(output).as_posix(),
                    crop_sha256=sha(crop),
                )
                records.append(record)
                write(directory / "source.json", record)
        if any(sha(path) != expected for path, expected in reused_files.items()):
            raise ValueError("reuse source/crop changed during preparation")
        if provenance is not None:
            if (
                sha(prepared_path) != provenance["prepared_sha256"]
                or sha(manifest_path) != provenance["manifest_sha256"]
            ):
                raise ValueError("reuse manifests changed during preparation")
            write(output / "reuse-manifest.json", provenance)
        if sha(inputs) != input_sha:
            raise ValueError("input manifest changed during preparation")
        write(output / "prepared.json", dict(status="prepared", fragments=records))
        return output, records
    except (Exception, KeyboardInterrupt) as exc:
        failure(output, exc)
        raise


def infer(pipeline, output, records, guard=lambda: None):
    summary = dict(status="running", expected=len(records), completed=0)
    try:
        for record in records:
            guard()
            crop = output / record["crop_relpath"]
            if sha(crop) != record["crop_sha256"]:
                raise ValueError("crop SHA mismatch")
            responses = []
            for result in pipeline.predict_iter(
                str(crop), prompt_label="table", use_layout_detection=False
            ):
                payload = result.json
                write(crop.parent / f"response-{len(responses):03d}.json", payload)
                responses.append(payload)
            write(crop.parent / "response.json", responses)
            if len(responses) != 1:
                raise ValueError("expected exactly one crop result")
            blocks = [
                b for b in responses[0]["res"]["parsing_res_list"] if b["block_label"] == "table"
            ]
            if (
                len(blocks) != 1
                or not isinstance(blocks[0].get("block_content"), str)
                or not blocks[0]["block_content"].strip()
            ):
                raise ValueError("expected exactly one nonempty table")
            write(
                crop.parent / "prediction.json",
                dict(
                    group_id=record["group_id"],
                    fragment_id=record["fragment_id"],
                    page_num=record["page_num"],
                    part_index=record["part_index"],
                    html=blocks[0]["block_content"],
                    status="completed",
                ),
            )
            summary["completed"] += 1
            guard()
        summary["status"] = "completed"
        return summary
    except (Exception, KeyboardInterrupt) as exc:
        summary.update(
            status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        failure(output, exc)
        raise
    finally:
        summary["ended_utc"] = datetime.now(UTC).isoformat()
        write(output / "summary.json", summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--group-id", action="append", required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--reuse-prepared-run", type=Path)
    parser.add_argument("--split", choices=("train_fit", "train_dev"), default="train_fit")
    parser.add_argument("--document-overlay", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output, records = prepare(
        root,
        args.inputs,
        args.run,
        args.group_id,
        args.reuse_prepared_run,
        split=args.split,
        document_overlay=args.document_overlay,
    )
    if args.prepare_only:
        return
    try:
        from run_paddle_document_full import verify_model
        from run_paddle_v15_smoke import configure_cache, gpu_sample

        versions = {
            name: importlib.metadata.version(name)
            for name in ("paddleocr", "paddlex", "paddlepaddle-gpu", "numpy")
        }
        if versions != dict(
            paddleocr="3.4.0", paddlex="3.4.1", **{"paddlepaddle-gpu": "3.2.1", "numpy": "1.26.4"}
        ):
            raise RuntimeError("unexpected environment versions")
        model = inside(root, Path(MODEL))
        model_sha = verify_model(model, MODEL_REVISION)
        before = gpu_sample(args.gpu)
        processes = subprocess.check_output(
            [
                "nvidia-smi",
                f"--id={args.gpu}",
                "--query-compute-apps=pid,process_name,used_memory",
                "--format=csv",
            ],
            text=True,
        )
        write(
            output / "environment.json",
            dict(
                versions=versions,
                model_manifest_sha256=model_sha,
                gpu_before=before,
                processes=processes,
            ),
        )
        if before["free_mib"] < 20000:
            raise RuntimeError("requires 20000 MiB free")
        configure_cache(output / "cache")
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
        import numpy as np
        import paddle
        from paddleocr import PaddleOCRVL

        if not paddle.is_compiled_with_cuda():
            raise RuntimeError("Paddle has no CUDA support")
        paddle.seed(0)
        random.seed(0)
        np.random.seed(0)
        pipeline = PaddleOCRVL(
            pipeline_version="v1.5",
            device="gpu:0",
            vl_rec_model_dir=str(model),
            vl_rec_backend="native",
            use_layout_detection=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_chart_recognition=False,
            use_seal_recognition=False,
            use_ocr_for_image_block=False,
            format_block_content=False,
            use_queues=False,
        )
        pipeline.export_paddlex_config_to_yaml(str(output / "pipeline-config.yaml"))

        def guard():
            sample = gpu_sample(args.gpu)
            with (output / "gpu-samples.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(dict(utc=datetime.now(UTC).isoformat(), **sample)) + "\n")
            if sample["free_mib"] < 8192:
                raise RuntimeError("requires 8192 MiB free after loading/fragment")

        infer(pipeline, output, records, guard)
    except (Exception, KeyboardInterrupt) as exc:
        if not (output / "failure.json").exists():
            failure(output, exc)
        raise


if __name__ == "__main__":
    main()
