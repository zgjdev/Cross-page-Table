"""两臂独立运行的跨页整表探索实验。保留每组输出及严格网格评分。"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from contextlib import nullcontext
from pathlib import Path


def document_split(inputs, train, heldout, *, overlay=None):
    if overlay is None and (len(train) != 8 or len(heldout) != 8):
        raise ValueError("expected eight unique train and eight unique heldout groups")
    if (
        not train
        or not heldout
        or len(set(train)) != len(train)
        or len(set(heldout)) != len(heldout)
    ):
        raise ValueError("expected unique groups in both splits")
    by_id = {row["group_id"]: row for row in inputs}
    if len(by_id) != len(inputs):
        raise ValueError("duplicate input group")
    docs = {g: by_id[g]["document_id"] for g in train + heldout}
    if set(train) & set(heldout) or {docs[g] for g in train} & {docs[g] for g in heldout}:
        raise ValueError("train and heldout overlap by document")
    if overlay is not None:
        by_doc = {r["document_id"]: r for r in overlay}
        if len(by_doc) != len(overlay):
            raise ValueError("duplicate document overlay")
        if {by_id[g]["cluster_id"] for g in train} & {by_id[g]["cluster_id"] for g in heldout}:
            raise ValueError("train and heldout overlap by cluster")
        for groups, split in ((train, "train_fit"), (heldout, "train_dev")):
            for g in groups:
                row, proof = by_id[g], by_doc.get(docs[g], {})
                if (
                    row["split"] != split
                    or proof.get("effective_split") != split
                    or proof.get("cluster_id") != row["cluster_id"]
                    or (split == "train_dev" and proof.get("observed_cluster") is not False)
                ):
                    raise ValueError(f"group is excluded by document overlay: {g}")
    return {g: docs[g] for g in train + heldout}


class TrainableState:
    """Checkpoint only trainable tensors; the immutable backbone is hashed separately."""

    def __init__(self, tensors):
        self.tensors = dict(tensors)

    def state_dict(self):
        return {name: value.detach().cpu() for name, value in self.tensors.items()}

    def load_state_dict(self, state, strict=True):
        import torch

        if strict and self.tensors.keys() != state.keys():
            raise ValueError("trainable checkpoint parameter names changed")
        with torch.no_grad():
            for name, value in self.tensors.items():
                saved = state[name]
                if saved.shape != value.shape or saved.dtype != value.dtype:
                    raise ValueError(f"trainable checkpoint tensor changed: {name}")
                value.copy_(saved)


def main():
    import review_reconstruction_qwen_smoke as review
    import run_reconstruction_qwen_smoke as smoke

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--arm", choices=["direct", "structure"], required=True)
    parser.add_argument("--train-selection", required=True)
    parser.add_argument("--heldout-selection", required=True)
    parser.add_argument("--upstream-run", action="append", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20261122)
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--max-new-tokens", type=int, default=8192)
    parser.add_argument("--output-format", choices=("grid", "html"), default="grid")
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--resume-state")
    parser.add_argument("--document-overlay")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{8}T\d{6}Z-[a-zA-Z0-9_-]+", args.run):
        raise ValueError("timestamped run required")
    if (
        not 1 <= args.steps <= (500 if args.train_only else 50)
        or not 1 <= args.max_new_tokens <= 8192
    ):
        raise ValueError("pilot exceeds bounded budget")
    if args.train_only:
        if args.epochs != 2 or not 1 <= args.checkpoint_every <= 50 or not args.document_overlay:
            raise ValueError("scaled pilot requires a document overlay and two epochs")
    elif args.prepare_only or args.resume_state or args.document_overlay:
        raise ValueError("prepare, resume and overlay options require --train-only")
    root = args.project_root.resolve()
    out = smoke.safe(root, "artifacts/reconstruction-paired-pilot/" + args.run)
    out.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        with (out / name).open("x", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

    hashes = {}

    def read(path, expected=None):
        path = smoke.safe(root, path)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        name = path.relative_to(root).as_posix()
        if (expected and sha != expected) or hashes.setdefault(name, sha) != sha:
            raise ValueError(f"input changed: {name}")
        return data

    def rows(path):
        return [json.loads(line) for line in read(path).decode("utf-8-sig").split("\n") if line]

    try:
        train = json.loads(read(args.train_selection))["groups"]
        heldout = json.loads(read(args.heldout_selection))["groups"]
        overlay = rows(args.document_overlay) if args.train_only else None
        docs = document_split(rows(args.inputs), train, heldout, overlay=overlay)
        expected_steps = len(train) * args.epochs if args.train_only else args.steps
        if args.train_only and (
            len(train) > 250 or len(heldout) != 16 or args.steps > expected_steps
        ):
            raise ValueError("scaled pilot requires at most 250 fit and exactly 16 dev tables")
        write(
            "manifest.json",
            dict(
                argv=sys.argv,
                config=vars(args) | {"project_root": str(root)},
                commit=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=root, text=True
                ).strip(),
                revision=smoke.DATASET_REVISION,
                model_revision="89644892e4d85e24eaac8bacfd4f463576704203",
                train=train,
                heldout=heldout,
                documents=docs,
                track="image-only",
                dtype="float32",
                split=(
                    "train_fit / train_dev fixed whole-table pilot"
                    if args.train_only
                    else "train_fit historical short-table exploratory pilot"
                ),
                lora_rank=16,
                lora_alpha=32,
                dropout=0.05,
                lr=1e-4,
                weight_decay=0.0,
                seed=args.seed,
                epochs=args.epochs if args.train_only else None,
                microbatch=1,
                tolerate_invalid_html=args.train_only,
            ),
        )
        model_path = smoke.safe(root, args.model)
        official = json.loads(read("configs/models/qwen3-vl-2b-instruct-2026-11-14.json"))[
            "models"
        ][0]
        pinned = json.loads(read(model_path / "download-manifest.json"))
        if (
            pinned["revision"] != "89644892e4d85e24eaac8bacfd4f463576704203"
            or pinned["status"] != "complete"
            or pinned["revision"] != official["revision"]
            or pinned["repo"] != official["repo"]
        ):
            raise ValueError("unverified model")
        files = {r["path"]: r for r in official["files"]}
        if set(files) != {r["file"] for r in pinned["verified"]}:
            raise ValueError("incomplete model")
        model_hashes = {}
        for rec in pinned["verified"]:
            path = smoke.safe(model_path, rec["file"])
            with path.open("rb") as f:
                if (
                    hashlib.file_digest(f, "sha256").hexdigest() != rec["sha256"]
                    or path.stat().st_size != files[rec["file"]]["size"]
                ):
                    raise ValueError("model SHA/size mismatch")
            model_hashes[path.relative_to(root).as_posix()] = rec["sha256"]
        write("model-hashes.json", model_hashes)
        examples, images = smoke.load_examples(
            root, args.inputs, args.targets, args.upstream_run, train, read
        )
        if not args.train_only:
            evaluation, extra_images = review.input_examples(
                root,
                dict(
                    inputs=args.inputs,
                    group_id=heldout,
                    upstream_run=args.upstream_run,
                    output_format=args.output_format,
                ),
                read,
            )
            images.update(extra_images)
        write("input-hashes.json", hashes)
        if not args.prepare_only:
            write("gpu-before.json", smoke.gpu_guard(args.gpu, 40960))
        os.environ["CUDA_VISIBLE_DEVICES"] = "" if args.prepare_only else str(args.gpu)
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        for var, directory in [
            ("HF_HOME", "hf-home"),
            ("TMPDIR", "tmp"),
            ("XDG_CACHE_HOME", "cache"),
        ]:
            (out / directory).mkdir()
            os.environ[var] = str(out / directory)
        import peft
        import torch
        import transformers
        from peft import LoraConfig, get_peft_model
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        from cptla.reconstruction.checkpoint_state import load_state, save_state
        from cptla.reconstruction.chunked_loss import chunked_causal_loss
        from cptla.reconstruction.prefix_injection import (
            inject_prefix_embeddings,
            prepend_prefix_inputs,
        )
        from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
        from cptla.reconstruction.scoring import score_groups
        from cptla.reconstruction.sft_data import SFTCollator
        from cptla.reconstruction.structure_features import prediction_nodes, structure_evidence
        from cptla.reconstruction.structure_memory import StructureMemory

        write(
            "versions.json",
            dict(
                torch=torch.__version__,
                transformers=transformers.__version__,
                peft=peft.__version__,
                gpu=None if args.prepare_only else torch.cuda.get_device_name(),
            ),
        )
        torch.manual_seed(args.seed)
        random.seed(args.seed)
        torch.use_deterministic_algorithms(True)
        processor = AutoProcessor.from_pretrained(
            model_path, local_files_only=True, min_pixels=65536, max_pixels=262144
        )
        adapter = QwenProcessorAdapter(processor, root, images)
        collate = SFTCollator(adapter, args.max_tokens, output_format=args.output_format)
        if args.prepare_only:
            lengths = []
            for model_input, target in examples:
                item = collate([(model_input, target)])[0]
                lengths.append(
                    dict(
                        group_id=model_input["group_id"],
                        tokens=len(item["input_ids"]),
                        supervised_tokens=sum(label != -100 for label in item["labels"]),
                        valid_structure_nodes=len(
                            prediction_nodes(model_input["fragments"], tolerate_invalid_html=True)
                        ),
                    )
                )
            write("lengths.json", lengths)
            write("summary.json", dict(status="prepared_only", groups=len(lengths)))
            return
        enc = None if args.train_only else collate(examples)
        base = Qwen3VLForConditionalGeneration.from_pretrained(
            model_path, dtype=torch.float32, attn_implementation="sdpa", local_files_only=True
        ).cuda()
        base.requires_grad_(False)
        wrapped = get_peft_model(
            base,
            LoraConfig(
                r=16,
                lora_alpha=32,
                lora_dropout=0.05,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=smoke.lora_modules([n for n, _ in base.named_modules()]),
            ),
        )
        base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        base.config.use_cache = False
        dim = base.get_input_embeddings().weight.shape[1]
        memory = (
            StructureMemory(dim + 1, dim + 5, dim, hidden_dim=64, num_blocks=2, num_heads=4).cuda()
            if args.arm == "structure"
            else None
        )
        trainables = {name: p for name, p in wrapped.named_parameters() if p.requires_grad}
        if memory is not None:
            trainables.update({f"structure.{name}": p for name, p in memory.named_parameters()})
        params = list(trainables.values())
        optimizer = torch.optim.AdamW(params, lr=1e-4, weight_decay=0.0)
        placeholder = processor.tokenizer.encode("x", add_special_tokens=False)
        if len(placeholder) != 1 or placeholder[0] in processor.tokenizer.all_special_ids:
            raise ValueError("invalid placeholder")

        def prepare(item, fragments):
            batch = {
                k: torch.tensor([v], device="cuda") if isinstance(v, list) else v.cuda()
                for k, v in item.items()
                if k != "token_type_ids"
            }
            if memory is None:
                return batch, nullcontext()
            v, n = structure_evidence(
                base, processor, batch, fragments, tolerate_invalid_html=args.train_only
            )
            prefix = memory(
                v,
                n,
                torch.ones(v.shape[:2], device="cuda", dtype=torch.bool),
                torch.ones(n.shape[:2], device="cuda", dtype=torch.bool),
            )["prefix"]
            batch = prepend_prefix_inputs(batch, prefix.shape[1], placeholder[0])
            return batch, inject_prefix_embeddings(
                base.get_input_embeddings(), batch["input_ids"], prefix
            )

        wrapped.train()
        torch.manual_seed(args.seed)
        start_step = 0
        if args.train_only:
            contract = dict(
                schema="paired-whole-table-fp32-v1",
                arm=args.arm,
                epochs=args.epochs,
                output=args.output_format,
                max_tokens=args.max_tokens,
                seed=args.seed,
                order=train,
                input_hashes=hashes,
                model_hashes=model_hashes,
                implementation_sha256={
                    name: hashlib.sha256(smoke.safe(root, name).read_bytes()).hexdigest()
                    for name in (
                        "scripts/run_reconstruction_paired_pilot.py",
                        "scripts/run_reconstruction_qwen_smoke.py",
                        "src/cptla/reconstruction/checkpoint_state.py",
                        "src/cptla/reconstruction/chunked_loss.py",
                        "src/cptla/reconstruction/prefix_injection.py",
                        "src/cptla/reconstruction/qwen_processor.py",
                        "src/cptla/reconstruction/sft_data.py",
                        "src/cptla/reconstruction/structure_features.py",
                        "src/cptla/reconstruction/structure_memory.py",
                    )
                },
            )
            state = TrainableState(trainables)
            if args.resume_state:
                resume = smoke.safe(root, args.resume_state)
                if not resume.is_relative_to(out.parent) or resume.parent.name != "training-state":
                    raise ValueError("resume requires a project paired training-state directory")
                restored = load_state(root, resume, state, optimizer, config=contract, trusted=True)
                start_step = restored["step"]
                if restored["cursor"] != start_step:
                    raise ValueError("checkpoint cursor does not match the paired schedule")
                write("resume-source.json", dict(path=args.resume_state, **restored))
            write("resume-config.json", contract)
        end_step = start_step + args.steps
        if end_step > expected_steps:
            raise ValueError("requested steps exceed paired schedule")
        for step in range(start_step, end_step):
            started = time.monotonic()
            torch.cuda.reset_peak_memory_stats()
            index = step % len(train)
            example = examples[index]
            encoded = collate([example])[0] if enc is None else enc[index]
            batch, hook = prepare(encoded, example[0]["fragments"])
            labels = batch.pop("labels")
            with hook:
                hidden = base.model(**batch, use_cache=False).last_hidden_state
                loss = chunked_causal_loss(hidden, base.lm_head, labels, chunk_size=128)
                if not torch.isfinite(loss):
                    raise RuntimeError("nonfinite training loss")
                loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
            slot_grad = None
            if memory is not None and memory.slot_queries.grad is not None:
                slot_grad = float(memory.slot_queries.grad.norm())
            check_names = (
                [next(name for name in trainables if ".lora_B." in name)]
                + (["structure.slot_queries"] if memory is not None else [])
                if step == start_step
                else []
            )
            before = {name: trainables[name].detach().clone() for name in check_names}
            optimizer.step()
            deltas = {
                name: float((trainables[name].detach() - value).norm())
                for name, value in before.items()
            }
            if args.train_only and any(not delta > 0 for delta in deltas.values()):
                raise RuntimeError("optimizer did not update the probed trainable tensors")
            optimizer.zero_grad(set_to_none=True)
            write(
                f"step-{step + 1:03d}.json",
                dict(
                    group=train[index],
                    step=step + 1,
                    epoch=step // len(train) + 1,
                    loss=float(loss.detach()),
                    norm=float(norm),
                    slot_grad_norm=slot_grad,
                    probed_parameter_deltas=deltas,
                    tokens=labels.shape[1],
                    elapsed_s=time.monotonic() - started,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                ),
            )
            del loss, hidden
            if args.train_only and (
                (step + 1) % args.checkpoint_every == 0 or step + 1 == end_step
            ):
                name = out / "training-state" / f"step-{step + 1:06d}"
                save_state(
                    root, name, state, optimizer, step=step + 1, cursor=step + 1, config=contract
                )
        wrapped.save_pretrained(out / "lora", safe_serialization=True)
        if memory is not None:
            torch.save(memory.state_dict(), out / "structure.pt")
            memory.eval()
        if args.train_only:
            paths = sorted((out / "lora").glob("*"))
            if memory is not None:
                paths.append(out / "structure.pt")
            write(
                "checkpoint-hashes.json",
                {
                    p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in paths
                    if p.is_file()
                },
            )
            write(
                "summary.json",
                dict(
                    status="completed",
                    scope="train_only",
                    train_steps=end_step,
                    expected_steps=expected_steps,
                    complete=end_step == expected_steps,
                    evaluated=0,
                ),
            )
            return
        wrapped.eval()
        base.gradient_checkpointing_disable()
        base.config.use_cache = True
        predictions = []
        with torch.inference_mode():
            for idx, row in enumerate(evaluation):

                def backend(messages, budget):
                    content = messages[0]["content"]
                    fragments = [
                        dict(image_path=content[i]["image"], prediction_html=content[i + 1]["text"])
                        for i in range(1, len(content), 2)
                    ]
                    item = adapter(messages, add_generation_prompt=True, truncation=False)
                    batch, hook = prepare(item, fragments)
                    with hook:
                        tokens = base.generate(
                            **batch, max_new_tokens=budget, do_sample=False, use_cache=True
                        )[0, batch["input_ids"].shape[1] :].tolist()
                    eos = base.generation_config.eos_token_id
                    return (
                        processor.tokenizer.decode(
                            tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
                        ),
                        len(tokens),
                        bool(tokens and tokens[-1] in (eos if isinstance(eos, list) else [eos])),
                    )

                pred = review.generate(
                    [row], backend, args.max_new_tokens, output_format=args.output_format
                )[0]
                predictions.append(pred)
                write(f"prediction-{idx + 1:03d}.json", pred)
        write("predictions.json", predictions)
        targets = [r for r in rows(args.targets) if r["group_id"] in heldout]
        if {r["group_id"] for r in targets} != set(heldout):
            raise ValueError("incomplete targets")
        write("scores.json", score_groups(targets, predictions))
        write(
            "summary.json",
            dict(status="completed", train_steps=args.steps, evaluated=len(predictions)),
        )
    except BaseException as exc:
        write("failure.json", dict(type=type(exc).__name__, message=str(exc)))
        raise


if __name__ == "__main__":
    main()
