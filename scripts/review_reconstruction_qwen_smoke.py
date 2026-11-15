"""受限smoke原样生成与独立评分；生成阶段绝不读取targets。"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from cptla.evaluation.pubtables_v2 import parse_full_document_image_id
from cptla.reconstruction.data import DATASET_REVISION, TRAIN_RELATIVE_PATH
from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
from cptla.reconstruction.scoring import score_groups


def safe(root, path):
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError("path escapes project")
    return result


def probe_config(training_config, groups, upstreams):
    """显式、未参与该smoke训练的train_fit接口探针；不修改训练记录。"""
    if (
        not 1 <= len(groups) <= 16
        or len(set(groups)) != len(groups)
        or set(groups) & set(training_config["group_id"])
        or not upstreams
        or len(upstreams) != len(set(upstreams))
    ):
        raise ValueError("probe requires 1–16 distinct untrained groups and upstream runs")
    return dict(training_config, group_id=list(groups), upstream_run=list(upstreams))


def generate(examples, backend, budget, *, on_prediction=None):
    groups = [row["group_id"] for row in examples]
    if not 1 <= len(groups) <= 16 or len(set(groups)) != len(groups) or not 1 <= budget <= 32768:
        raise ValueError("invalid group/token scope")
    predictions = []
    for row in examples:
        if any(message.get("role") != "user" for message in row["messages"]):
            raise ValueError("generation must not contain labels/assistant messages")
        raw, tokens, eos = backend(row["messages"], budget)
        truncated = not eos and tokens >= budget
        predictions.append(
            dict(
                group_id=row["group_id"],
                source_pages=list(row["source_pages"]),
                html=raw,
                generated_tokens=tokens,
                eos_reached=eos,
                truncated=truncated,
                status="truncated" if truncated else "completed",
            )
        )
        if on_prediction is not None:
            on_prediction(predictions[-1])
    return predictions


def input_examples(root, config, read):
    groups = config["group_id"]
    if not 1 <= len(groups) <= 16 or len(set(groups)) != len(groups):
        raise ValueError("invalid smoke groups")
    originals = {}
    for line in read(safe(root, config["inputs"])).decode("utf-8-sig").split("\n"):
        if line.strip():
            row = json.loads(line)
            if row["group_id"] in originals:
                raise ValueError("duplicate input group")
            originals[row["group_id"]] = row
    members, seen = {}, set()
    for run in config["upstream_run"]:
        run = safe(root, run)
        prepared = json.loads(read(run / "prepared.json"))
        summary = json.loads(read(run / "summary.json"))
        fragments = prepared["fragments"]
        if (
            prepared["status"] != "prepared"
            or summary["status"] != "completed"
            or any(summary[k] != len(fragments) for k in ["expected", "completed"])
        ):
            raise ValueError("upstream incomplete")
        run_groups = {r["group_id"] for r in fragments}
        if run_groups & seen:
            raise ValueError("overlapping groups")
        seen.update(run_groups)
        for record in fragments:
            if record["group_id"] in groups:
                members.setdefault(record["group_id"], []).append((run, record))
    examples, images = [], {}
    for group in groups:
        original = originals[group]
        if (
            original.get("split") != "train_fit"
            or original.get("source_split") != "train"
            or original.get("dataset_revision") != DATASET_REVISION
        ):
            raise ValueError("nontrain input forbidden")
        expected = {f["fragment_id"]: f for f in original["fragments"]}
        selected = members.get(group, [])
        if len(selected) != len(expected) or {r["fragment_id"] for _, r in selected} != set(
            expected
        ):
            raise ValueError("fragment coverage mismatch")
        content = [
            {
                "type": "text",
                "text": (
                    "根据按顺序提供的表格片段图像及局部预测，恢复完整表格。只输出完整 HTML table。"
                ),
            }
        ]
        pages = []
        for upstream, record in sorted(
            selected, key=lambda pair: (pair[1]["page_num"], pair[1]["part_index"])
        ):
            if any(record.get(k) != v for k, v in expected[record["fragment_id"]].items()):
                raise ValueError("original/prepared mismatch")
            crop = safe(upstream, record["crop_relpath"])
            if crop.name != "crop.png" or not crop.is_relative_to(upstream / "fragments"):
                raise ValueError("invalid crop location")
            if json.loads(read(crop.parent / "source.json")) != record:
                raise ValueError("source mismatch")
            original_image = safe(root, record["image_relpath"])
            train_images = root / TRAIN_RELATIVE_PATH / "images"
            if train_images.resolve() != train_images or not original_image.is_relative_to(
                train_images
            ):
                raise ValueError("source outside train images")
            if parse_full_document_image_id(original_image.name) != (
                original["document_id"],
                record["page_num"],
            ):
                raise ValueError("source document/page mismatch")
            read(original_image, record["image_sha256"])
            read(crop, record["crop_sha256"])
            prediction = json.loads(read(crop.parent / "prediction.json"))
            if prediction.get("status") != "completed" or any(
                prediction.get(k) != record[k]
                for k in ["group_id", "fragment_id", "page_num", "part_index"]
            ):
                raise ValueError("prediction identity mismatch")
            name = crop.relative_to(root).as_posix()
            images[name] = record["crop_sha256"]
            content.extend(
                [{"type": "image", "image": name}, {"type": "text", "text": prediction["html"]}]
            )
            pages.append(record["page_num"])
        examples.append(
            dict(
                group_id=group,
                source_pages=sorted(set(pages)),
                messages=[{"role": "user", "content": content}],
            )
        )
    return examples, images


def gpu_guard(gpu, minimum):
    output = subprocess.run(
        ["nvidia-smi", "-i", str(gpu), "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
    )
    if int(output.stdout.strip()) < minimum:
        raise RuntimeError("insufficient GPU free memory")
    processes = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        check=True,
    )
    return dict(free_mib=int(output.stdout.strip()), processes=processes.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["generate", "score"])
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--smoke-run", required=True)
    parser.add_argument("--generation-run")
    parser.add_argument("--run", required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    parser.add_argument("--probe-group-id", action="append")
    parser.add_argument("--probe-upstream-run", action="append")
    args = parser.parse_args()
    root = args.project_root.resolve()
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z(?:-[A-Za-z0-9_-]+)?", args.run):
        raise ValueError("timestamp run required")
    output = safe(root, "artifacts/reconstruction-qwen-review/" + args.run)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def write(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)

    def read(path, expected=None):
        path = safe(root, path)
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        name = path.relative_to(root).as_posix()
        if (expected and digest != expected) or (name in hashes and hashes[name] != digest):
            raise ValueError("SHA mismatch")
        hashes[name] = digest
        return raw

    try:
        smoke = safe(root, args.smoke_run)
        summary = json.loads(read(smoke / "summary.json"))
        if summary.get("status") != "completed_smoke":
            raise ValueError("smoke not completed")
        config = json.loads(read(smoke / "run-manifest.json"))["config"]
        if bool(args.probe_group_id) != bool(args.probe_upstream_run):
            raise ValueError("probe requires both explicit groups and upstream runs")
        if args.probe_group_id:
            if args.action != "generate":
                raise ValueError("score obtains probe scope from generation receipt")
            config = probe_config(config, args.probe_group_id, args.probe_upstream_run)
        if not 1 <= len(config["group_id"]) <= 16 or len(set(config["group_id"])) != len(
            config["group_id"]
        ):
            raise ValueError("invalid smoke group scope")
        write(
            "run-manifest.json",
            dict(
                argv=sys.argv,
                action=args.action,
                smoke_run=smoke.relative_to(root).as_posix(),
                max_new_tokens=args.max_new_tokens,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                utc=datetime.now(UTC).isoformat(),
                G2_passed=False,
                probe_group_ids=args.probe_group_id,
                probe_upstream_runs=args.probe_upstream_run,
            ),
        )
        if args.action == "generate":
            examples, images = input_examples(root, config, read)
            pinned = json.loads(read(smoke / "input-hashes.json"))
            for name, digest in list(hashes.items()):
                if name in pinned and pinned[name] != digest:
                    raise ValueError("smoke input drift")
            write("input-examples.json", examples)
            model_path = safe(root, config["model"])
            model_hashes = json.loads(read(smoke / "model-hashes.json"))
            for name, digest in model_hashes.items():
                read(safe(root, name), digest)
            optimization = json.loads(read(smoke / "optimization.json"))
            adapter = smoke / "lora-checkpoint"
            for name, digest in optimization["checkpoint_hashes"].items():
                read(safe(adapter, name), digest)
            for key in ["HF_HOME", "XDG_CACHE_HOME", "TMPDIR"]:
                directory = output / key.lower()
                directory.mkdir()
                os.environ[key] = str(directory)
            os.environ.update(
                HF_HUB_OFFLINE="1",
                HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                TRANSFORMERS_OFFLINE="1",
                CUDA_VISIBLE_DEVICES=str(args.gpu),
            )
            write("gpu-before.json", gpu_guard(args.gpu, 20480))
            import torch
            from peft import PeftModel
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            processor = AutoProcessor.from_pretrained(
                str(model_path), local_files_only=True, min_pixels=65536, max_pixels=262144
            )
            encoder = QwenProcessorAdapter(processor, root, images)
            model = Qwen3VLForConditionalGeneration.from_pretrained(
                str(model_path),
                local_files_only=True,
                dtype=torch.bfloat16,
                attn_implementation="sdpa",
            ).to("cuda")
            model = PeftModel.from_pretrained(model, str(adapter), local_files_only=True).eval()

            def backend(messages, budget):
                gpu_guard(args.gpu, 8192)
                encoded = encoder(messages, add_generation_prompt=True, truncation=False)
                batch = {
                    k: torch.tensor([v], device="cuda") if isinstance(v, list) else v.to("cuda")
                    for k, v in encoded.items()
                    if k != "token_type_ids"
                }
                with torch.inference_mode():
                    result = model.generate(**batch, max_new_tokens=budget, do_sample=False)
                tokens = result[0, len(encoded["input_ids"]) :].tolist()
                eos = model.generation_config.eos_token_id
                eos_ids = eos if isinstance(eos, list) else [eos]
                raw = processor.tokenizer.decode(
                    tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )
                gpu_guard(args.gpu, 8192)
                return raw, len(tokens), bool(tokens and tokens[-1] in eos_ids)

            completed = 0

            def persist_prediction(prediction):
                nonlocal completed
                completed += 1
                write(f"prediction-{completed:03d}.json", prediction)
                print(
                    json.dumps(
                        dict(
                            completed=completed,
                            expected=len(examples),
                            group_id=prediction["group_id"],
                            status=prediction["status"],
                        )
                    ),
                    flush=True,
                )

            predictions = generate(
                examples, backend, args.max_new_tokens, on_prediction=persist_prediction
            )
            write("predictions.json", predictions)
        else:
            if not args.generation_run:
                raise ValueError("score requires completed generation run")
            generation = safe(root, args.generation_run)
            receipt = json.loads(read(generation / "summary.json"))
            if receipt.get("status") != "completed" or receipt.get("action") != "generate":
                raise ValueError("generation incomplete")
            provenance = json.loads(
                read(
                    generation / "run-manifest.json",
                    receipt["artifact_hashes"]["run-manifest.json"],
                )
            )
            if provenance["smoke_run"] != smoke.relative_to(root).as_posix():
                raise ValueError("generation belongs to another smoke")
            predictions = json.loads(
                read(
                    generation / "predictions.json", receipt["artifact_hashes"]["predictions.json"]
                )
            )
            if provenance.get("probe_group_ids"):
                config = probe_config(
                    config, provenance["probe_group_ids"], provenance["probe_upstream_runs"]
                )
            groups = config["group_id"]
            targets = []
            pinned = json.loads(read(smoke / "input-hashes.json"))
            target_path = safe(root, config["targets"])
            target_name = target_path.relative_to(root).as_posix()
            if not re.fullmatch("[a-f0-9]{64}", pinned.get(target_name, "")):
                raise ValueError("missing training target SHA")
            for line in read(target_path, pinned[target_name]).decode("utf-8-sig").split("\n"):
                if line.strip():
                    row = json.loads(line)
                    if row["group_id"] in groups:
                        targets.append(row)
            if len(targets) != len(groups) or {r["group_id"] for r in targets} != set(groups):
                raise ValueError("target coverage mismatch")
            write("scores.json", score_groups(targets, predictions))
        write("input-hashes.json", hashes)
        for name, digest in list(hashes.items()):
            read(root / name, digest)
        write(
            "summary.json",
            dict(
                status="completed",
                action=args.action,
                groups=len(config["group_id"]),
                G2_passed=False,
                artifact_hashes={
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in output.iterdir()
                    if p.is_file()
                },
            ),
        )
    except (Exception, KeyboardInterrupt) as error:
        write("failure.json", dict(status="failed", exception_type=type(error).__name__))
        raise


if __name__ == "__main__":
    main()
