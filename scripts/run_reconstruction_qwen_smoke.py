"""受限Qwen LoRA技术smoke：最多16表/50步，默认只准备，不放行G2。"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from cptla.evaluation.pubtables_v2 import parse_full_document_image_id
from cptla.reconstruction.checkpoint_state import load_state, save_state
from cptla.reconstruction.data import DATASET_REVISION, PROTOCOL, TRAIN_RELATIVE_PATH
from cptla.reconstruction.grid import GRID_VERSION
from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
from cptla.reconstruction.sft_data import SFTCollator, build_messages


def safe(root, path):
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError("path escapes project")
    return result


def validate(groups, steps):
    if not 1 <= len(groups) <= 16 or len(set(groups)) != len(groups):
        raise ValueError("require 1–16 explicit unique train_fit groups")
    if type(steps) is not int or not 1 <= steps <= 50:
        raise ValueError("smoke steps must be 1–50")


def lora_modules(names):
    suffixes = ("q_proj", "k_proj", "v_proj", "o_proj")
    found = [
        name
        for name in names
        if ".language_model." in "." + name
        and ".self_attn." in name
        and name.rsplit(".", 1)[-1] in suffixes
        and "visual" not in name
    ]
    if {name.rsplit(".", 1)[-1] for name in found} != set(suffixes):
        raise ValueError("actual language q/k/v/o module names not verified")
    return found


def load_examples(root, inputs, targets, upstreams, groups, read):
    def rows(path):
        result = {}
        for line in read(safe(root, path)).decode("utf-8-sig").split("\n"):
            if not line.strip():
                continue
            row = json.loads(line)
            if row["group_id"] in result:
                raise ValueError("duplicate group")
            result[row["group_id"]] = row
        return result

    input_rows, target_rows = rows(inputs), rows(targets)
    records, seen_groups = {}, set()
    for upstream_path in upstreams:
        upstream = safe(root, upstream_path)
        prepared = json.loads(read(upstream / "prepared.json"))
        summary = json.loads(read(upstream / "summary.json"))
        fragments = prepared["fragments"]
        if (
            prepared.get("status") != "prepared"
            or summary.get("status") != "completed"
            or not fragments
            or summary.get("expected") != len(fragments)
            or summary.get("completed") != len(fragments)
        ):
            raise ValueError("upstream not completed with full coverage")
        run_groups = {r["group_id"] for r in fragments}
        if run_groups & seen_groups:
            raise ValueError("overlapping upstream groups")
        seen_groups.update(run_groups)
        for record in fragments:
            if record["group_id"] in groups:
                records.setdefault(record["group_id"], []).append((upstream, record))
    examples, images = [], {}
    for group in groups:
        original = input_rows[group]
        if (
            original.get("split") != "train_fit"
            or original.get("source_split") != "train"
            or original.get("dataset_revision") != DATASET_REVISION
            or original.get("protocol") != PROTOCOL
        ):
            raise ValueError("original input is not fixed train_fit R0")
        expected = {f["fragment_id"]: f for f in original["fragments"]}
        if len(expected) != len(original["fragments"]):
            raise ValueError("duplicate original fragment")
        selected = records.get(group, [])
        if len(selected) != len(expected) or {r["fragment_id"] for _, r in selected} != set(
            expected
        ):
            raise ValueError("selected group fragment coverage mismatch")
        mapped = []
        for upstream, record in sorted(
            selected, key=lambda item: (item[1]["page_num"], item[1]["part_index"])
        ):
            original_fragment = expected[record["fragment_id"]]
            for key, value in original_fragment.items():
                if record.get(key) != value:
                    raise ValueError("prepared/original fragment mismatch")
            crop = safe(upstream, record["crop_relpath"])
            if crop.name != "crop.png" or not crop.is_relative_to(upstream / "fragments"):
                raise ValueError("invalid crop location")
            if json.loads(read(crop.parent / "source.json")) != record:
                raise ValueError("prepared/source mismatch")
            source_image = safe(root, record["image_relpath"])
            train_images = root / TRAIN_RELATIVE_PATH / "images"
            if train_images.resolve() != train_images or not source_image.is_relative_to(
                train_images
            ):
                raise ValueError("source outside official train images")
            identity = parse_full_document_image_id(source_image.name)
            if identity != (original["document_id"], record["page_num"]):
                raise ValueError("source document/page identity mismatch")
            read(source_image, record["image_sha256"])
            read(crop, record["crop_sha256"])
            prediction = json.loads(read(crop.parent / "prediction.json"))
            if prediction.get("status") != "completed" or any(
                prediction.get(k) != record[k]
                for k in ("group_id", "fragment_id", "page_num", "part_index")
            ):
                raise ValueError("prediction identity/status mismatch")
            image = crop.relative_to(root).as_posix()
            images[image] = record["crop_sha256"]
            mapped.append(dict(image_path=image, prediction_html=prediction["html"]))
        model_input = dict(group_id=group, split="train_fit", track="image-only", fragments=mapped)
        target = dict(group_id=group, grid_version=GRID_VERSION, html=target_rows[group]["html"])
        build_messages(model_input, target)
        examples.append((model_input, target))
    return examples, images


def gpu_guard(gpu, minimum):
    result = subprocess.run(
        ["nvidia-smi", "-i", str(gpu), "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
    )
    if int(result.stdout.strip()) < minimum:
        raise RuntimeError("insufficient GPU free memory")
    processes = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_memory", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        check=True,
    )
    return dict(free_mib=int(result.stdout.strip()), processes=processes.stdout.strip())


def resume_config(args, input_hashes, model_hashes):
    """恢复契约排除运行位置和本次步数，保留影响数值路径的配置。"""
    return dict(
        schema="qwen-bounded-smoke-resume-v1",
        groups=list(args.group_id),
        seed=20261109,
        max_tokens=args.max_tokens,
        min_pixels=65536,
        max_pixels=262144,
        gradient_checkpointing=args.gradient_checkpointing,
        use_reentrant=False,
        input_hashes=dict(input_hashes),
        model_hashes=dict(model_hashes),
        optimizer=dict(name="AdamW", lr=1e-4, weight_decay=0.01),
        lora=dict(r=16, alpha=32, dropout=0.05, targets=["q_proj", "k_proj", "v_proj", "o_proj"]),
        dtype="bfloat16",
        attention="sdpa",
        grad_accumulation=1,
        clip_grad_norm=1.0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--upstream-run", action="append", required=True)
    parser.add_argument("--group-id", action="append", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--execute-smoke", action="store_true")
    parser.add_argument("--resume-state")
    parser.add_argument("--gradient-checkpointing", action="store_true")
    args = parser.parse_args()
    validate(args.group_id, args.steps)
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z(?:-[A-Za-z0-9_-]+)?", args.run):
        raise ValueError("timestamp run required")
    if not 1 <= args.max_tokens <= 32768 or args.gpu < 0:
        raise ValueError("invalid token or GPU budget")
    root = args.project_root.resolve()
    output = safe(root, "artifacts/reconstruction-qwen-smoke/" + args.run)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def write(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)

    def read(path, expected=None):
        path = safe(root, path)
        value = path.read_bytes()
        digest = hashlib.sha256(value).hexdigest()
        key = path.relative_to(root).as_posix()
        if (expected is not None and expected != digest) or (
            key in hashes and hashes[key] != digest
        ):
            raise ValueError("input SHA mismatch")
        hashes[key] = digest
        return value

    try:
        model_path = safe(root, args.model)
        if not model_path.is_dir():
            raise ValueError("local model directory required")
        write(
            "run-manifest.json",
            dict(
                argv=sys.argv,
                config=vars(args) | {"project_root": str(root)},
                utc=datetime.now(UTC).isoformat(),
                seed=20261109,
                python=platform.python_version(),
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                code_commit=subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip(),
                dataset_revision=DATASET_REVISION,
                mode="technical_smoke_not_formal_training",
                G2_passed=False,
                full_training_authorized=False,
                optimizer=dict(name="AdamW", lr=1e-4),
                lora=dict(r=16, alpha=32, dropout=0.05),
            ),
        )
        examples, image_hashes = load_examples(
            root, args.inputs, args.targets, args.upstream_run, args.group_id, read
        )
        write("prepared.json", dict(groups=args.group_id, images=image_hashes))
        pinned = json.loads(read(model_path / "download-manifest.json"))
        if (
            pinned.get("status") != "complete"
            or pinned.get("revision") != "89644892e4d85e24eaac8bacfd4f463576704203"
            or pinned.get("repo") != "Qwen/Qwen3-VL-2B-Instruct"
            or not pinned.get("verified")
        ):
            raise ValueError("model manifest not complete/pinned")
        official = json.loads(read(root / "configs/models/qwen3-vl-2b-instruct-2026-11-14.json"))[
            "models"
        ][0]
        if official["revision"] != pinned["revision"] or official["repo"] != pinned["repo"]:
            raise ValueError("official manifest revision mismatch")
        authoritative = {entry["path"]: entry for entry in official["files"]}
        if set(authoritative) != {item["file"] for item in pinned["verified"]}:
            raise ValueError("official/download file inventory mismatch")
        model_hashes = {}
        for item in pinned["verified"]:
            model_file = safe(model_path, item["file"])
            if any(part in {".metadata", ".cache"} for part in Path(item["file"]).parts):
                raise ValueError("hidden model metadata forbidden")
            name = model_file.relative_to(root).as_posix()
            if name in model_hashes or model_file.stat().st_size != item["size"]:
                raise ValueError("model manifest duplicate/size mismatch")
            expected = authoritative[item["file"]]
            if item["size"] != expected["size"]:
                raise ValueError("official size mismatch")
            checksum = hashlib.sha256()
            blob = hashlib.sha1(f"blob {expected['size']}\0".encode())
            with model_file.open("rb") as stream:
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                    checksum.update(chunk)
                    blob.update(chunk)
            digest = checksum.hexdigest()
            if (expected.get("sha256") and digest != expected["sha256"]) or (
                not expected.get("sha256") and blob.hexdigest() != expected.get("git_blob_id")
            ):
                raise ValueError("official checksum mismatch")
            if digest != item["sha256"]:
                raise ValueError("pinned model SHA mismatch")
            model_hashes[name] = digest
        write("model-hashes.json", model_hashes)
        cache_config = {}
        for variable, name in [
            ("HF_HOME", "hf-home"),
            ("XDG_CACHE_HOME", "xdg-cache"),
            ("TMPDIR", "tmp"),
        ]:
            directory = output / name
            directory.mkdir()
            os.environ[variable] = str(directory)
            cache_config[variable] = str(directory)
        for variable in ["HF_HUB_OFFLINE", "HF_HUB_DISABLE_IMPLICIT_TOKEN", "TRANSFORMERS_OFFLINE"]:
            os.environ[variable] = "1"
            cache_config[variable] = "1"
        write(
            "runtime-policy.json",
            dict(
                environment=cache_config,
                min_pixels=65536,
                max_pixels=262144,
                clip_grad_norm=1.0,
                removed_processor_fields=["token_type_ids"],
            ),
        )
        if args.resume_state:
            resume_directory = safe(root, args.resume_state)
            receipt_path = safe(resume_directory, "manifest.json")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                receipt.get("format") != "cptla-self-produced-training-state-v1"
                or receipt.get("status") != "completed"
            ):
                raise ValueError("resume requires completed self-produced training state")
            contract = resume_config(args, hashes, model_hashes)
            canonical = json.dumps(
                contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
            if receipt.get("config_hash") != hashlib.sha256(canonical.encode()).hexdigest():
                raise ValueError("resume config mismatch")
            state_path = safe(resume_directory, "state.pt")
            with state_path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != receipt.get("sha256"):
                    raise ValueError("resume state SHA mismatch")
            write(
                "resume-source.json",
                dict(
                    path=resume_directory.relative_to(root).as_posix(),
                    manifest_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    state_sha256=receipt["sha256"],
                ),
            )
        if args.execute_smoke:
            write("gpu-before.json", gpu_guard(args.gpu, 20480))
            os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
            import torch
            from peft import (
                LoraConfig,
                get_peft_model,
                get_peft_model_state_dict,
                set_peft_model_state_dict,
            )
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            write(
                "versions.json",
                {
                    name: importlib.metadata.version(name)
                    for name in ("torch", "transformers", "peft", "accelerate", "Pillow")
                },
            )
            random.seed(20261109)
            torch.manual_seed(20261109)
            torch.cuda.manual_seed_all(20261109)
            processor = AutoProcessor.from_pretrained(
                str(model_path), local_files_only=True, min_pixels=65536, max_pixels=262144
            )
            collator = SFTCollator(
                QwenProcessorAdapter(processor, root, image_hashes), args.max_tokens
            )
            encoded = collator(examples)
            model = Qwen3VLForConditionalGeneration.from_pretrained(
                str(model_path),
                local_files_only=True,
                dtype=torch.bfloat16,
                attn_implementation="sdpa",
            ).to("cuda")
            modules = lora_modules([name for name, _ in model.named_modules()])
            write("lora-targets.json", modules)
            model.requires_grad_(False)
            model = get_peft_model(
                model,
                LoraConfig(
                    r=16,
                    lora_alpha=32,
                    lora_dropout=0.05,
                    target_modules=modules,
                    bias="none",
                    task_type="CAUSAL_LM",
                ),
            )
            trainable = {
                name: value for name, value in model.named_parameters() if value.requires_grad
            }
            if not trainable or any("lora_" not in name or "visual" in name for name in trainable):
                raise ValueError("unexpected trainable parameter")
            write("trainable.json", {name: list(value.shape) for name, value in trainable.items()})
            optimizer = torch.optim.AdamW(trainable.values(), lr=1e-4)
            resume_contract = resume_config(args, hashes, model_hashes)
            write("resume-config.json", resume_contract)
            start_step, cursor = 0, 0
            if args.resume_state:
                restored = load_state(
                    root, args.resume_state, model, optimizer, config=resume_contract, trusted=True
                )
                start_step, cursor = restored["step"], restored["cursor"]
            initial = {name: value.detach().cpu().clone() for name, value in trainable.items()}
            model.config.use_cache = False
            if args.gradient_checkpointing:
                model.gradient_checkpointing_enable(
                    gradient_checkpointing_kwargs={"use_reentrant": False}
                )
            model.train()
            torch.cuda.reset_peak_memory_stats()
            losses = []
            for step in range(args.steps):
                gpu_guard(args.gpu, 8192)
                item = encoded[cursor % len(encoded)]
                batch = {
                    key: torch.tensor([value], device="cuda")
                    if isinstance(value, list)
                    else value.to("cuda")
                    for key, value in item.items()
                    if key != "token_type_ids"
                }
                optimizer.zero_grad(set_to_none=True)
                started = time.monotonic()
                loss = model(**batch).loss
                if not torch.isfinite(loss):
                    raise RuntimeError("nonfinite loss")
                loss.backward()
                gradient = sum(
                    float(p.grad.detach().float().norm().item())
                    for p in trainable.values()
                    if p.grad is not None
                )
                clipnorm = float(
                    torch.nn.utils.clip_grad_norm_(
                        list(trainable.values()), 1.0, error_if_nonfinite=True
                    ).item()
                )
                optimizer.step()
                torch.cuda.synchronize()
                event = dict(
                    step=start_step + step + 1,
                    invocation_step=step + 1,
                    cursor=cursor,
                    loss=float(loss.detach().item()),
                    gradient_norm_sum=gradient,
                    preclip_global_norm=clipnorm,
                    clip_grad_norm=1.0,
                    seconds=time.monotonic() - started,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                )
                cursor += 1
                losses.append(event)
                write(f"step-{step + 1:03d}.json", event)
                gpu_guard(args.gpu, 8192)
            changed = [
                name
                for name, value in trainable.items()
                if not torch.equal(initial[name], value.detach().cpu())
            ]
            if not changed or not any(row["gradient_norm_sum"] > 0 for row in losses):
                raise RuntimeError("no nonzero gradient or parameter change")
            checkpoint = output / "lora-checkpoint"
            model.save_pretrained(str(checkpoint), safe_serialization=True)
            from safetensors.torch import load_file

            saved = load_file(str(checkpoint / "adapter_model.safetensors"))
            current = get_peft_model_state_dict(model)
            if set(saved) != set(current) or any(
                not torch.equal(saved[k], current[k].detach().cpu()) for k in saved
            ):
                raise RuntimeError("saved adapter mismatch")
            with torch.no_grad():
                for value in trainable.values():
                    value.zero_()
            set_peft_model_state_dict(model, saved)
            reloaded = get_peft_model_state_dict(model)
            if any(not torch.equal(saved[k], reloaded[k].detach().cpu()) for k in saved):
                raise RuntimeError("adapter reload mismatch")
            write(
                "optimization.json",
                dict(
                    changed_parameters=changed,
                    losses=losses,
                    reload_equal=True,
                    checkpoint_hashes={
                        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in checkpoint.iterdir()
                        if p.is_file()
                    },
                ),
            )
            saved_state = save_state(
                root,
                output / "training-state",
                model,
                optimizer,
                step=start_step + args.steps,
                cursor=cursor,
                config=resume_contract,
            )
            write(
                "training-state-reference.json",
                dict(
                    path=saved_state.relative_to(root).as_posix(),
                    manifest_sha256=hashlib.sha256(
                        (saved_state / "manifest.json").read_bytes()
                    ).hexdigest(),
                    total_steps=start_step + args.steps,
                    cursor=cursor,
                ),
            )
            write("gpu-after.json", gpu_guard(args.gpu, 8192))
        for model_name, digest in model_hashes.items():
            with safe(root, model_name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                    raise ValueError("model artifact changed")
        write("input-hashes.json", hashes)
        for path, digest in list(hashes.items()):
            read(root / path, digest)
        write(
            "summary.json",
            dict(
                status="completed_smoke" if args.execute_smoke else "prepared_only",
                groups=len(examples),
                steps=args.steps if args.execute_smoke else 0,
                G2_passed=False,
                full_training_authorized=False,
                ended_utc=datetime.now(UTC).isoformat(),
            ),
        )
    except (Exception, KeyboardInterrupt) as error:
        write(
            "failure.json",
            dict(
                status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                type=type(error).__name__,
                utc=datetime.now(UTC).isoformat(),
            ),
        )
        raise


if __name__ == "__main__":
    main()
