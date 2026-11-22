"""两臂独立运行的跨页整表探索实验。保留每组输出及严格网格评分。"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path


def document_split(inputs, train, heldout):
    if len(set(train)) != 8 or len(train) != 8 or len(set(heldout)) != 8 or len(heldout) != 8:
        raise ValueError("expected eight unique train and eight unique heldout groups")
    docs = {row["group_id"]: row["document_id"] for row in inputs}
    if set(train) & set(heldout) or {docs[g] for g in train} & {docs[g] for g in heldout}:
        raise ValueError("train and heldout overlap by document")
    return {g: docs[g] for g in train + heldout}


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
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()
    if not re.fullmatch(r"\d{8}T\d{6}Z-[a-zA-Z0-9_-]+", args.run):
        raise ValueError("timestamped run required")
    if not 1 <= args.steps <= 50 or not 1 <= args.max_new_tokens <= 8192:
        raise ValueError("pilot exceeds bounded budget")
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
        docs = document_split(rows(args.inputs), train, heldout)
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
                split="train_fit historical short-table exploratory pilot",
                lora_rank=16,
                lora_alpha=32,
                dropout=0.05,
                lr=1e-4,
                weight_decay=0.0,
                seed=args.seed,
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
        for rec in pinned["verified"]:
            path = smoke.safe(model_path, rec["file"])
            with path.open("rb") as f:
                if (
                    hashlib.file_digest(f, "sha256").hexdigest() != rec["sha256"]
                    or path.stat().st_size != files[rec["file"]]["size"]
                ):
                    raise ValueError("model SHA/size mismatch")
        examples, images = smoke.load_examples(
            root, args.inputs, args.targets, args.upstream_run, train, read
        )
        evaluation, extra_images = review.input_examples(
            root,
            dict(
                inputs=args.inputs,
                group_id=heldout,
                upstream_run=args.upstream_run,
                output_format="grid",
            ),
            read,
        )
        images.update(extra_images)
        write("input-hashes.json", hashes)
        write("gpu-before.json", smoke.gpu_guard(args.gpu, 40960))
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
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

        from cptla.reconstruction.chunked_loss import chunked_causal_loss
        from cptla.reconstruction.prefix_injection import (
            inject_prefix_embeddings,
            prepend_prefix_inputs,
        )
        from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
        from cptla.reconstruction.scoring import score_groups
        from cptla.reconstruction.sft_data import SFTCollator
        from cptla.reconstruction.structure_features import structure_evidence
        from cptla.reconstruction.structure_memory import StructureMemory

        write(
            "versions.json",
            dict(
                torch=torch.__version__,
                transformers=transformers.__version__,
                peft=peft.__version__,
                gpu=torch.cuda.get_device_name(),
            ),
        )
        torch.manual_seed(args.seed)
        random.seed(args.seed)
        torch.use_deterministic_algorithms(True)
        processor = AutoProcessor.from_pretrained(
            model_path, local_files_only=True, min_pixels=65536, max_pixels=262144
        )
        adapter = QwenProcessorAdapter(processor, root, images)
        enc = SFTCollator(adapter, args.max_tokens, output_format="grid")(examples)
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
        params = [p for p in wrapped.parameters() if p.requires_grad]
        if memory is not None:
            params.extend(memory.parameters())
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
            v, n = structure_evidence(base, processor, batch, fragments)
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
        for step in range(args.steps):
            index = step % len(train)
            batch, hook = prepare(enc[index], examples[index][0]["fragments"])
            labels = batch.pop("labels")
            with hook:
                hidden = base.model(**batch, use_cache=False).last_hidden_state
                loss = chunked_causal_loss(hidden, base.lm_head, labels, chunk_size=128)
                loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            write(
                f"step-{step + 1:03d}.json",
                dict(group=train[index], loss=float(loss.detach()), norm=float(norm)),
            )
            del loss, hidden
        wrapped.save_pretrained(out / "lora")
        if memory is not None:
            torch.save(memory.state_dict(), out / "structure.pt")
            memory.eval()
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

                pred = review.generate([row], backend, args.max_new_tokens, output_format="grid")[0]
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
