"""Generate an untouched train_dev cohort from a completed paired LoRA arm."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

from cptla.reconstruction.data import DATASET_REVISION
from cptla.reconstruction.scoring import score_groups

DEV_UPSTREAM = "artifacts/reconstruction-upstream/20261122T164938Z-dev16-paddle"
OVERLAY = (
    "artifacts/reconstruction-quarantine/20261115T074000Z-known-overlap-overlay/"
    "document-overlay.jsonl"
)
TIMESTAMP_RUN = r"\d{8}T\d{6}Z-[a-zA-Z0-9_-]+"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def write(directory, name, value):
    with (directory / name).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def read_rows(payload, identity):
    rows = {}
    for line in payload.decode("utf-8-sig").split("\n"):
        if line.strip():
            row = json.loads(line)
            key = row[identity]
            if key in rows:
                raise ValueError(f"duplicate {identity}: {key}")
            rows[key] = row
    return rows


def resumable_predictions(previous, contract, examples):
    """Read only independently completed, matching per-table receipts."""
    if previous is None:
        return {}

    def read(path):
        resolved = path.resolve()
        if not resolved.is_relative_to(previous):
            raise ValueError("resumed prediction path escapes its run")
        return json.loads(resolved.read_bytes())

    old = read(previous / "manifest.json")
    if old["contract"] != contract:
        raise ValueError("prior generation contract differs")
    restored = {}
    for path in sorted(previous.glob("prediction-*.json")):
        match = re.fullmatch(r"prediction-(\d{3})\.json", path.name)
        if not match:
            raise ValueError("unexpected prediction file name")
        index = int(match[1])
        if not 1 <= index <= len(examples):
            raise ValueError("resumed prediction index is outside scope")
        receipt_path = previous / f"receipt-{index:03d}.json"
        if not receipt_path.is_file():
            # An interrupted write left no completion receipt. Recompute in the fresh run.
            continue
        row = read(path)
        receipt = read(receipt_path)
        expected = examples[index - 1]
        if (
            receipt != {"contract_sha256": digest(contract), "prediction_sha256": digest(row)}
            or row["group_id"] != expected["group_id"]
            or row["source_pages"] != expected["source_pages"]
        ):
            raise ValueError("resumed prediction identity or checksum mismatch")
        restored[index] = row
    return restored


def generation_backend(root, output, model_path, checkpoint, arm, dtype_name, images, gpu):
    from review_reconstruction_qwen_smoke import gpu_guard

    write(output, "gpu-before.json", gpu_guard(gpu, 20480))
    for name in ("HF_HOME", "XDG_CACHE_HOME", "TMPDIR"):
        directory = output / name.lower()
        directory.mkdir()
        os.environ[name] = str(directory)
    os.environ.update(
        HF_HUB_OFFLINE="1",
        HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
        TRANSFORMERS_OFFLINE="1",
        CUDA_VISIBLE_DEVICES=str(gpu),
    )
    import torch
    from peft import PeftModel
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    from cptla.reconstruction.prefix_injection import (
        inject_prefix_embeddings,
        prepend_prefix_inputs,
    )
    from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
    from cptla.reconstruction.structure_features import structure_evidence
    from cptla.reconstruction.structure_memory import StructureMemory

    write(
        output,
        "runtime.json",
        {name: importlib.metadata.version(name) for name in ("torch", "transformers", "peft")}
        | {"gpu": gpu, "gpu_model": torch.cuda.get_device_name(), "dtype": dtype_name},
    )
    dtype = {"float32": torch.float32, "bfloat16": torch.bfloat16}[dtype_name]
    processor = AutoProcessor.from_pretrained(
        str(model_path), local_files_only=True, min_pixels=65536, max_pixels=262144
    )
    encoder = QwenProcessorAdapter(processor, root, images)
    base = Qwen3VLForConditionalGeneration.from_pretrained(
        str(model_path), local_files_only=True, dtype=dtype, attn_implementation="sdpa"
    ).cuda()
    model = PeftModel.from_pretrained(base, str(checkpoint / "lora"), local_files_only=True).eval()
    base.config.use_cache = True
    embedding = base.get_input_embeddings()
    memory, placeholder = None, None
    if arm == "structure":
        dim = embedding.weight.shape[1]
        memory = StructureMemory(dim + 1, dim + 5, dim, hidden_dim=64, num_blocks=2, num_heads=4)
        memory.load_state_dict(
            torch.load(checkpoint / "structure.pt", map_location="cpu", weights_only=True)
        )
        memory.cuda().eval()
        ids = processor.tokenizer.encode("x", add_special_tokens=False)
        if len(ids) != 1 or ids[0] in processor.tokenizer.all_special_ids:
            raise ValueError("invalid placeholder token")
        placeholder = ids[0]

    def generate(messages, budget):
        gpu_guard(gpu, 8192)
        encoded = encoder(messages, add_generation_prompt=True, truncation=False)
        batch = {
            k: torch.tensor([v], device="cuda") if isinstance(v, list) else v.cuda()
            for k, v in encoded.items()
            if k != "token_type_ids"
        }
        with torch.inference_mode():
            hook = nullcontext()
            if memory is not None:
                content = messages[0]["content"]
                fragments = [
                    dict(image_path=content[i]["image"], prediction_html=content[i + 1]["text"])
                    for i in range(1, len(content), 2)
                ]
                visual, nodes = structure_evidence(
                    base, processor, batch, fragments, tolerate_invalid_html=True
                )
                prefix = memory(
                    visual,
                    nodes,
                    torch.ones(visual.shape[:2], device="cuda", dtype=torch.bool),
                    torch.ones(nodes.shape[:2], device="cuda", dtype=torch.bool),
                )["prefix"].to(embedding.weight.dtype)
                batch = prepend_prefix_inputs(batch, prefix.shape[1], placeholder)
                hook = inject_prefix_embeddings(embedding, batch["input_ids"], prefix)
            with hook:
                ids = model.generate(
                    **batch, max_new_tokens=budget, do_sample=False, use_cache=True
                )
            tokens = ids[0, batch["input_ids"].shape[1] :].tolist()
        eos = base.generation_config.eos_token_id
        eos_ids = eos if isinstance(eos, list) else [eos]
        raw = processor.tokenizer.decode(
            tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return raw, len(tokens), bool(tokens and tokens[-1] in eos_ids)

    return generate


def run(args):
    from evaluate_reconstruction_boundary_edit_dev import validate_selection
    from review_reconstruction_qwen_smoke import generate, input_examples, safe

    root = args.project_root.resolve()
    if not re.fullmatch(TIMESTAMP_RUN, args.run) or not 1 <= args.max_new_tokens <= 32768:
        raise ValueError("invalid run ID or generation token budget")
    output = safe(root, "artifacts/reconstruction-paired-training-eval/" + args.run)
    output.mkdir(parents=True, exist_ok=False)

    def read(path, expected=None):
        path = safe(root, path)
        raw = path.read_bytes()
        if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"SHA mismatch for {path.relative_to(root)}")
        return raw

    try:
        training = safe(root, args.training_run)
        checkpoint = json.loads(read(training / "summary.json"))
        manifest = json.loads(read(training / "manifest.json"))
        config = manifest["config"]
        if (
            checkpoint["status"] != "completed"
            or checkpoint["scope"] != "train_only"
            or checkpoint["complete"] is not True
            or checkpoint["train_steps"] != 500
            or manifest["revision"] != DATASET_REVISION
            or config["arm"] not in {"direct", "structure"}
            or len(set(manifest["train"])) != 250
            or len(manifest["train"]) != 250
        ):
            raise ValueError("requires a completed 250-table matched training arm")
        audit_path = safe(root, args.data_audit)
        audit_bytes = read(audit_path)
        audit = json.loads(audit_bytes)
        if (
            audit["status"] != "completed"
            or audit["dataset_revision"] != DATASET_REVISION
            or audit["training_groups"] != 250
            or audit["dev_groups"] != 16
            or any(audit[k] != 0 for k in ("input_overlap", "doc_overlap", "cluster_overlap"))
        ):
            raise ValueError("invalid or incomplete paired data audit")
        audit_dir = audit_path.parent
        audit_hashes = audit["files_sha256"]
        training_hashes = json.loads(read(training / "input-hashes.json"))

        def audited_read(path, expected=None):
            key = safe(root, path).relative_to(root).as_posix()
            sha = audit_hashes[key]
            if (expected is not None and expected != sha) or training_hashes.get(key, sha) != sha:
                raise ValueError(f"training and development input hashes differ at {key}")
            return read(path, sha)

        selection_path = safe(root, config["heldout_selection"])
        select = json.loads(
            read(selection_path, training_hashes[selection_path.relative_to(root).as_posix()])
        )
        if (
            select["dataset_revision"] != DATASET_REVISION
            or select["split"] != "train_dev"
            or select["upstream_runs"] != [audit["dev_upstream"]]
            or audit["dev_upstream"] != DEV_UPSTREAM
        ):
            raise ValueError("development receipt mismatch")
        original_select = json.loads(audited_read(select["original_selection"]))
        inputs_path = safe(root, config["inputs"])
        inputs = read_rows(
            read(inputs_path, training_hashes[inputs_path.relative_to(root).as_posix()]),
            "group_id",
        )
        groups = validate_selection(
            original_select["groups"],
            inputs,
            read_rows(audited_read(OVERLAY, original_select["overlay_sha256"]), "document_id"),
            {inputs[g]["document_id"] for g in manifest["train"]},
            {inputs[g]["cluster_id"] for g in manifest["train"]},
        )
        if select["groups"] != groups or manifest.get("heldout") != groups:
            raise ValueError("development groups differ from the matched training contract")
        examples, images = input_examples(
            root,
            dict(
                group_id=groups,
                inputs=audit_dir / "dev-inputs.jsonl",
                upstream_run=[DEV_UPSTREAM],
                output_format=config["output_format"],
            ),
            audited_read,
            expected_split="train_dev",
        )
        model_path = safe(root, config["model"])
        model_hashes = json.loads(read(training / "model-hashes.json"))
        weight_hashes = json.loads(read(training / "checkpoint-hashes.json"))
        required = {"lora/adapter_config.json", "lora/adapter_model.safetensors"}
        if config["arm"] == "structure":
            required.add("structure.pt")
        if not required <= set(weight_hashes) or not model_hashes:
            raise ValueError("missing pinned model/checkpoint files")
        dev_target_receipt = json.loads(read(audit_dir / "dev-targets-receipt.json"))
        targets_path = safe(root, dev_target_receipt["path"])
        if (
            targets_path != audit_dir / "dev-targets.jsonl"
            or dev_target_receipt["source_targets_sha256"] != select["targets_sha256"]
            or dev_target_receipt["groups"] != groups
        ):
            raise ValueError("development target receipt mismatch")
        contract = dict(
            code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            data_audit_sha256=hashlib.sha256(audit_bytes).hexdigest(),
            training_run=training.relative_to(root).as_posix(),
            arm=config["arm"],
            model_revision=manifest["model_revision"],
            dtype=manifest["dtype"],
            output_format=config["output_format"],
            groups=groups,
            max_new_tokens=args.max_new_tokens,
            model_hashes=model_hashes,
            checkpoint_hashes=weight_hashes,
            target_sha256=dev_target_receipt["sha256"],
        )
        git = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
        )
        write(
            output,
            "manifest.json",
            dict(
                utc=datetime.now(UTC).isoformat(),
                argv=sys.argv,
                code_commit=git.stdout.strip() if git.returncode == 0 else None,
                contract=contract,
            ),
        )
        previous = safe(root, args.resume_from) if args.resume_from else None
        restored = resumable_predictions(previous, contract, examples)
        backend = None
        if len(restored) < len(examples):
            for directory, origin, pins in (
                (model_path, root, model_hashes),
                (training, training, weight_hashes),
            ):
                for filename, expected in pins.items():
                    path = safe(origin, filename)
                    if not path.is_relative_to(directory):
                        raise ValueError("checkpoint file outside expected directory")
                    with path.open("rb") as stream:
                        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                            raise ValueError(f"checkpoint SHA mismatch: {filename}")
            backend = generation_backend(
                root,
                output,
                model_path,
                training,
                config["arm"],
                manifest["dtype"],
                images,
                args.gpu,
            )
        predictions = []
        for index, example in enumerate(examples, 1):
            row = restored.get(index)
            if row is None:
                row = generate(
                    [example], backend, args.max_new_tokens, output_format=config["output_format"]
                )[0]
            write(output, f"prediction-{index:03d}.json", row)
            write(
                output,
                f"receipt-{index:03d}.json",
                {"contract_sha256": digest(contract), "prediction_sha256": digest(row)},
            )
            predictions.append(row)
            print(
                json.dumps(dict(completed=index, total=len(examples), status=row["status"])),
                flush=True,
            )
        write(output, "predictions.json", predictions)

        # The target payload is neither decoded nor hashed until every prediction is on disk.
        targets = read_rows(read(targets_path, dev_target_receipt["sha256"]), "group_id")
        if set(targets) != set(groups):
            raise ValueError("development target coverage mismatch")
        write(output, "scores.json", score_groups([targets[g] for g in groups], predictions))
        write(
            output,
            "summary.json",
            dict(
                status="completed",
                arm=config["arm"],
                groups=len(predictions),
                target_sha256=dev_target_receipt["sha256"],
                reused_predictions=len(restored),
                predictions_sha256=hashlib.sha256(
                    (output / "predictions.json").read_bytes()
                ).hexdigest(),
                ended_utc=datetime.now(UTC).isoformat(),
            ),
        )
    except (Exception, KeyboardInterrupt) as error:
        write(
            output,
            "failure.json",
            dict(status="failed", type=type(error).__name__, message=str(error)),
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--training-run", required=True)
    parser.add_argument("--data-audit", required=True)
    parser.add_argument("--gpu", default=0, type=int)
    parser.add_argument("--max-new-tokens", default=8192, type=int)
    parser.add_argument("--resume-from")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
