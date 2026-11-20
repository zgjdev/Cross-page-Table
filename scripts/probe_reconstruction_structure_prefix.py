"""单train_fit组单步：真实Qwen grid主损失到结构前缀的接口探针；不是正式训练。"""

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

from cptla.reconstruction.grid import html_to_grid


def prediction_nodes(fragments):
    """Only predicted cell text/positions; deliberately no target parameter."""
    if not fragments:
        raise ValueError("empty predicted fragments")
    nodes = []
    for index, fragment in enumerate(fragments):
        if set(fragment) != {"image_path", "prediction_html"}:
            raise ValueError("unexpected feature input fields")
        grid = html_to_grid(fragment["prediction_html"])  # No repair or GT fallback.
        for cell in grid.cells:
            nodes.append(
                (
                    cell.text,
                    [
                        cell.row_start / grid.n_rows,
                        cell.row_end / grid.n_rows,
                        cell.col_start / grid.n_cols,
                        cell.col_end / grid.n_cols,
                        index / max(1, len(fragments) - 1),
                    ],
                )
            )
    return nodes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--upstream-run", action="append", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--execute-probe", action="store_true")
    args = parser.parse_args()
    import run_reconstruction_qwen_smoke as smoke

    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z(?:-[A-Za-z0-9_-]+)?", args.run):
        raise ValueError("fresh timestamp run required")
    if not 1 <= args.max_tokens <= 65536 or args.gpu < 0:
        raise ValueError("invalid GPU/token budget")
    root = args.project_root.resolve()
    output = smoke.safe(root, "artifacts/reconstruction-structure-prefix/" + args.run)
    output.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)

    hashes = {}

    def read(path, expected=None):
        path = smoke.safe(root, path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        key = path.relative_to(root).as_posix()
        if (expected is not None and digest != expected) or (
            key in hashes and hashes[key] != digest
        ):
            raise ValueError("input changed or SHA mismatch")
        hashes[key] = digest
        return data

    try:
        write(
            "run-manifest.json",
            dict(
                argv=sys.argv,
                config=vars(args) | {"project_root": str(root)},
                started_utc=datetime.now(UTC).isoformat(),
                seed=args.seed,
                pid=os.getpid(),
                python=platform.python_version(),
                platform=platform.platform(),
                code_commit=subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip(),
                dataset_revision=smoke.DATASET_REVISION,
                protocol=smoke.PROTOCOL,
                source_split="train",
                split="train_fit",
                track="image-only",
                groups=1,
                steps=1,
                mode="technical_interface_probe_not_formal_training",
                G2_passed=False,
                full_training_authorized=False,
                model_revision="89644892e4d85e24eaac8bacfd4f463576704203",
                architecture=dict(slots=64, summaries=16, hidden_dim=64, blocks=2, heads=4),
                optimizer=dict(name="AdamW", lr=1e-4, weight_decay=0.0, clip_grad_norm=1.0),
                limitations=[
                    "nonformal reduced hidden dimension",
                    "only one cached-token check",
                    "no baseline comparison or quality claim",
                    "no auxiliary structure loss",
                    "visual evidence includes fragment index but no explicit 2D coordinates",
                ],
            ),
        )
        for relative in [
            "scripts/probe_reconstruction_structure_prefix.py",
            "scripts/run_reconstruction_qwen_smoke.py",
            *[
                "src/cptla/reconstruction/" + name + ".py"
                for name in (
                    "structure_memory",
                    "prefix_injection",
                    "sft_data",
                    "qwen_processor",
                    "grid",
                    "grid_sequence",
                    "chunked_loss",
                )
            ],
        ]:
            read(root / relative)
        # Reuse the existing full pinned-model and original/crop/prediction validation.
        validation_run = args.run + "-validation"
        validation_argv = [
            "run_reconstruction_qwen_smoke.py",
            "--project-root",
            str(root),
            "--inputs",
            args.inputs,
            "--targets",
            args.targets,
            "--group-id",
            args.group_id,
            "--model",
            args.model,
            "--run",
            validation_run,
            "--max-tokens",
            str(args.max_tokens),
            "--output-format",
            "grid",
        ]
        for upstream in args.upstream_run:
            validation_argv.extend(["--upstream-run", upstream])
        original_argv = sys.argv
        try:
            sys.argv = validation_argv
            smoke.main()  # No --execute-smoke: validation only, no model loading/GPU.
        finally:
            sys.argv = original_argv
        validation = smoke.safe(root, "artifacts/reconstruction-qwen-smoke/" + validation_run)
        validation_summary = json.loads(read(validation / "summary.json"))
        if validation_summary["status"] != "prepared_only":
            raise RuntimeError("validation did not finish")
        model_hashes = json.loads(read(validation / "model-hashes.json"))
        write(
            "validation-reference.json",
            dict(path=str(validation.relative_to(root)), model_hashes=model_hashes),
        )
        examples, image_hashes = smoke.load_examples(
            root, args.inputs, args.targets, args.upstream_run, [args.group_id], read
        )
        records = prediction_nodes(examples[0][0]["fragments"])
        write(
            "prepared.json",
            dict(
                group_id=args.group_id,
                fragments=len(image_hashes),
                nodes=len(records),
                images=image_hashes,
                features="predicted text mean embedding plus r0,r1,c0,c1,fragment",
                target_access="assistant labels only; no target features",
            ),
        )
        if args.execute_probe:
            write("gpu-before.json", smoke.gpu_guard(args.gpu, 20480))
            os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
            os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
            import torch
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            from cptla.reconstruction.chunked_loss import chunked_causal_loss
            from cptla.reconstruction.prefix_injection import (
                inject_prefix_embeddings,
                prepend_prefix_inputs,
            )
            from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
            from cptla.reconstruction.sft_data import SFTCollator
            from cptla.reconstruction.structure_memory import StructureMemory

            write(
                "versions.json",
                {
                    name: importlib.metadata.version(name)
                    for name in ("torch", "transformers", "Pillow", "accelerate")
                },
            )
            random.seed(args.seed)
            torch.manual_seed(args.seed)
            torch.cuda.manual_seed_all(args.seed)
            torch.use_deterministic_algorithms(True)
            model_path = smoke.safe(root, args.model)
            processor = AutoProcessor.from_pretrained(
                str(model_path), local_files_only=True, min_pixels=65536, max_pixels=262144
            )
            encoded = SFTCollator(
                QwenProcessorAdapter(processor, root, image_hashes),
                args.max_tokens,
                output_format="grid",
            )(examples)[0]
            batch = {
                key: torch.tensor([value], device="cuda")
                if isinstance(value, list)
                else value.to("cuda")
                for key, value in encoded.items()
                if key != "token_type_ids"
            }
            model = Qwen3VLForConditionalGeneration.from_pretrained(
                str(model_path),
                local_files_only=True,
                dtype=torch.bfloat16,
                attn_implementation="sdpa",
            ).to("cuda")
            model.requires_grad_(False)
            model.eval()
            model.config.use_cache = False
            embedding = model.get_input_embeddings()
            dim = embedding.weight.shape[1]
            # Read visual features from the frozen image tower, not decoder states
            # (decoder states could depend on teacher-forced target text).
            with torch.no_grad():
                image_output = model.model.get_image_features(
                    pixel_values=batch["pixel_values"], image_grid_thw=batch["image_grid_thw"]
                )
                if hasattr(image_output, "pooler_output"):
                    image_parts = image_output.pooler_output
                elif isinstance(image_output, tuple) and len(image_output) == 2:
                    image_parts = image_output[0]
                else:
                    raise ValueError("unverified Qwen image feature return contract")
                if not isinstance(image_parts, (tuple, list)) or not image_parts:
                    raise ValueError("expected per-image visual sequences")
                if any(part.ndim != 2 or part.shape[1] != dim for part in image_parts):
                    raise ValueError("unexpected visual feature shape")
                if len(image_parts) != len(examples[0][0]["fragments"]):
                    raise ValueError("visual/fragment coverage mismatch")
                visual_parts = [
                    torch.cat(
                        (
                            part.float(),
                            part.new_full(
                                (part.shape[0], 1), index / max(1, len(image_parts) - 1)
                            ).float(),
                        ),
                        dim=-1,
                    )
                    for index, part in enumerate(image_parts)
                ]
                visual = torch.cat(visual_parts, dim=0).unsqueeze(0).detach()
                node_values = []
                for text, positions in records:
                    ids = processor.tokenizer.encode(text, add_special_tokens=False)
                    # Empty predicted cells have a zero textual vector; never fill from GT.
                    mean = (
                        embedding(torch.tensor(ids, device="cuda")).float().mean(0)
                        if ids
                        else torch.zeros(dim, device="cuda")
                    )
                    node_values.append(torch.cat((mean, mean.new_tensor(positions))))
                nodes = torch.stack(node_values).unsqueeze(0).detach()
            structure = StructureMemory(
                dim + 1,
                dim + 5,
                dim,
                hidden_dim=64,
                num_blocks=2,
                num_heads=4,
                num_slots=64,
                num_summary=16,
            ).to("cuda")
            initial = {
                name: value.detach().cpu().clone() for name, value in structure.named_parameters()
            }
            optimizer = torch.optim.AdamW(structure.parameters(), lr=1e-4, weight_decay=0.0)
            prefix = structure(
                visual,
                nodes,
                torch.ones(visual.shape[:2], dtype=torch.bool, device="cuda"),
                torch.ones(nodes.shape[:2], dtype=torch.bool, device="cuda"),
            )["prefix"].to(embedding.weight.dtype)
            prefix.retain_grad()
            candidate_ids = processor.tokenizer.encode("x", add_special_tokens=False)
            if not candidate_ids or candidate_ids[0] in processor.tokenizer.all_special_ids:
                raise ValueError("no verified ordinary placeholder token")
            prepared = prepend_prefix_inputs(batch, prefix.shape[1], candidate_ids[0])
            labels = prepared.pop("labels")
            # Prompt-only causal/cache check: no target token enters either path.
            prompt_length = int(torch.nonzero(batch["labels"][0] != -100)[0].item())
            prompt = {
                key: value[:, :prompt_length] if key in ("input_ids", "attention_mask") else value
                for key, value in batch.items()
                if key != "labels"
            }
            prompt = prepend_prefix_inputs(prompt, prefix.shape[1], candidate_ids[0])
            detached_prefix = prefix.detach()
            with torch.no_grad():
                model.model.rope_deltas = None
                with inject_prefix_embeddings(embedding, prompt["input_ids"], detached_prefix):
                    prefill = model(**prompt, use_cache=True, return_dict=True, logits_to_keep=1)
                    token = prefill.logits[:, -1].argmax(-1, keepdim=True)
                    extended_mask = torch.cat(
                        (prompt["attention_mask"], prompt["attention_mask"].new_ones((1, 1))), dim=1
                    )
                    cached = (
                        model(
                            input_ids=token,
                            attention_mask=extended_mask,
                            past_key_values=prefill.past_key_values,
                            cache_position=torch.tensor(
                                [prompt["input_ids"].shape[1]], device="cuda"
                            ),
                            use_cache=True,
                            return_dict=True,
                            logits_to_keep=1,
                        )
                        .logits[:, -1]
                        .float()
                    )
                full_prompt = dict(prompt)
                full_prompt["input_ids"] = torch.cat((prompt["input_ids"], token), dim=1)
                full_prompt["attention_mask"] = extended_mask
                model.model.rope_deltas = None
                with inject_prefix_embeddings(embedding, full_prompt["input_ids"], detached_prefix):
                    full = (
                        model(**full_prompt, use_cache=False, return_dict=True, logits_to_keep=1)
                        .logits[:, -1]
                        .float()
                    )
                equal = torch.allclose(cached, full, atol=0.05, rtol=0.01)
                write(
                    "cache-check.json",
                    dict(
                        passed=equal,
                        atol=0.05,
                        rtol=0.01,
                        max_abs_difference=float((cached - full).abs().max()),
                        next_token=int(token.item()),
                        prompt_tokens=prompt_length,
                        eval=True,
                        target_tokens_used=False,
                        native_mrope=True,
                        rope_deltas_reset=True,
                        checks=1,
                    ),
                )
                if not equal:
                    raise RuntimeError(
                        "cached/full next-token logits differ beyond fixed tolerance"
                    )
                del prefill, cached, full
            model.model.rope_deltas = None
            torch.cuda.reset_peak_memory_stats()
            started = time.monotonic()
            with inject_prefix_embeddings(embedding, prepared["input_ids"], prefix):
                hidden = model.model(
                    **prepared, use_cache=False, return_dict=True
                ).last_hidden_state
                loss = chunked_causal_loss(hidden, model.lm_head, labels, chunk_size=128)
                if not torch.isfinite(loss):
                    raise RuntimeError("nonfinite grid loss")
                loss.backward()
            grads = {
                name: float(value.grad.float().norm().item()) if value.grad is not None else None
                for name, value in structure.named_parameters()
            }
            if (
                prefix.grad is None
                or not torch.isfinite(prefix.grad).all()
                or not (prefix.grad.float().norm() > 0)
            ):
                raise RuntimeError("no finite nonzero loss-to-prefix gradient")
            for component in (
                "visual_projection",
                "node_projection",
                "slot_queries",
                "summary_queries",
                "blocks",
                "count",
                "decoder_projection",
            ):
                if not any(
                    value is not None and value > 0
                    for name, value in grads.items()
                    if name.startswith(component)
                ):
                    raise RuntimeError("missing grid-loss gradient: " + component)
            if any(value.grad is not None for value in model.parameters()):
                raise RuntimeError("frozen Qwen acquired parameter gradients")
            norm = torch.nn.utils.clip_grad_norm_(
                structure.parameters(), 1.0, error_if_nonfinite=True
            )
            optimizer.step()
            torch.cuda.synchronize()
            changes = {
                name: float((value.detach().cpu() - initial[name]).norm().item())
                for name, value in structure.named_parameters()
            }
            if not any(value > 0 for value in changes.values()):
                raise RuntimeError("no actual structure parameter update")
            checkpoint = output / "structure-memory.pt"
            torch.save(
                {
                    "state_dict": structure.state_dict(),
                    "seed": args.seed,
                    "technical_probe_only": True,
                },
                checkpoint,
            )
            write(
                "optimization.json",
                dict(
                    loss=float(loss.detach()),
                    loss_type="grid assistant causal CE only",
                    steps=1,
                    gradient_norms=grads,
                    parameter_delta_norms=changes,
                    preclip_global_norm=float(norm),
                    prefix_grad_norm=float(prefix.grad.float().norm()),
                    qwen_frozen=True,
                    seconds=time.monotonic() - started,
                    input_tokens=batch["input_ids"].shape[1],
                    prefix_tokens=prefix.shape[1],
                    supervised_tokens=int((labels != -100).sum()),
                    visual_shape=list(visual.shape),
                    node_shape=list(nodes.shape),
                    native_input_ids_retained=True,
                    positions_supplied=False,
                    cache_tested=True,
                    visual_reencoded_by_native_forward=True,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                ),
            )
        # Recheck immutable inputs and model artifacts after the probe.
        for path, digest in list(hashes.items()):
            read(root / path, digest)
        for path, digest in model_hashes.items():
            with smoke.safe(root, path).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                    raise RuntimeError("model artifact changed")
        write("input-hashes.json", hashes)
        write(
            "summary.json",
            dict(
                status="completed_probe" if args.execute_probe else "prepared_only",
                steps=int(args.execute_probe),
                groups=1,
                ended_utc=datetime.now(UTC).isoformat(),
                G2_passed=False,
                formal_training=False,
                generation_cache_acceptance="single prompt plus one token only"
                if args.execute_probe
                else False,
            ),
        )
    except (Exception, KeyboardInterrupt) as error:
        write(
            "failure.json",
            dict(
                status="failed", type=type(error).__name__, ended_utc=datetime.now(UTC).isoformat()
            ),
        )
        raise


if __name__ == "__main__":
    main()
