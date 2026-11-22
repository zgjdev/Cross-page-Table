"""Recover the pinned one-step StructureMemory and generate paired complete grids."""

import argparse
import hashlib
import json
import os
import subprocess
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

from review_reconstruction_qwen_smoke import generate, gpu_guard, input_examples, safe

SOURCE = "artifacts/reconstruction-structure-prefix/20261120T125300Z-prefix-native-fp32"
CHECKPOINT_SHA = "12109474fd7f1ef0442121f47e4fcb9dc9bc97a8a4a8a94616c786e71ce932f5"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    source = safe(root, SOURCE)
    out = safe(
        root,
        "artifacts/reconstruction-prefix-review/"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-paired"),
    )
    out.mkdir(parents=True, exist_ok=False)

    def write(name, obj):
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(obj, stream, ensure_ascii=False, indent=2)

    print(out, flush=True)
    write("gpu-before.json", gpu_guard(0, 24576))
    for variable in ["HF_HOME", "XDG_CACHE_HOME", "TMPDIR"]:
        cache = out / variable.lower()
        cache.mkdir()
        os.environ[variable] = str(cache)
    os.environ.update(
        CUDA_VISIBLE_DEVICES="0", HF_HUB_OFFLINE="1", CUBLAS_WORKSPACE_CONFIG=":4096:8"
    )
    import torch
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    from cptla.reconstruction.prefix_injection import (
        inject_prefix_embeddings,
        prepend_prefix_inputs,
    )
    from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
    from cptla.reconstruction.structure_features import structure_evidence
    from cptla.reconstruction.structure_memory import StructureMemory

    config = json.loads((source / "run-manifest.json").read_bytes())["config"]
    config.update(group_id=[config["group_id"]], output_format="grid")
    pinned = json.loads((source / "input-hashes.json").read_bytes())

    def read(path, expected=None):
        raw = safe(root, path).read_bytes()
        key = path.relative_to(root).as_posix()
        if hashlib.sha256(raw).hexdigest() != pinned[key] or (expected and expected != pinned[key]):
            raise ValueError(f"input changed: {key}")
        return raw

    checkpoint = source / "structure-memory.pt"
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != CHECKPOINT_SHA:
        raise ValueError("checkpoint changed")
    hashes = json.loads((source / "validation-reference.json").read_bytes())["model_hashes"]
    for path, sha in hashes.items():
        with safe(root, path).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != sha:
                raise ValueError("model weight changed")
    write(
        "manifest.json",
        dict(
            source=SOURCE,
            checkpoint_sha=CHECKPOINT_SHA,
            config=config,
            budget=4096,
            seed=20261116,
            torch=torch.__version__,
            commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
        ),
    )
    examples, images = input_examples(root, config, read)
    path = safe(root, config["model"])
    processor = AutoProcessor.from_pretrained(
        path, local_files_only=True, min_pixels=65536, max_pixels=262144
    )
    encoder = QwenProcessorAdapter(processor, root, images)
    torch.manual_seed(20261116)
    model = (
        Qwen3VLForConditionalGeneration.from_pretrained(
            path, local_files_only=True, dtype=torch.float32, attn_implementation="sdpa"
        )
        .to("cuda")
        .eval()
    )
    outputs = {}
    with torch.inference_mode():
        for mode in ["structure", "direct"]:

            def backend(messages, budget, mode=mode):
                encoded = encoder(messages, add_generation_prompt=True, truncation=False)
                batch = {
                    k: torch.tensor([v], device="cuda") if isinstance(v, list) else v.to("cuda")
                    for k, v in encoded.items()
                    if k != "token_type_ids"
                }
                context = nullcontext()
                if mode == "structure":
                    items = messages[0]["content"][1:]
                    fragments = [
                        dict(image_path=img["image"], prediction_html=pred["text"])
                        for img, pred in zip(items[::2], items[1::2], strict=True)
                    ]
                    visual, nodes = structure_evidence(model, processor, batch, fragments)
                    embed = model.get_input_embeddings()
                    memory = (
                        StructureMemory(
                            visual.shape[-1],
                            nodes.shape[-1],
                            embed.weight.shape[1],
                            hidden_dim=64,
                            num_blocks=2,
                            num_heads=4,
                        )
                        .to("cuda")
                        .eval()
                    )
                    memory.load_state_dict(
                        torch.load(checkpoint, map_location="cpu", weights_only=True)["state_dict"],
                        strict=True,
                    )
                    prefix = memory(
                        visual,
                        nodes,
                        torch.ones_like(visual[:, :, 0], dtype=torch.bool),
                        torch.ones_like(nodes[:, :, 0], dtype=torch.bool),
                    )["prefix"]
                    batch = prepend_prefix_inputs(
                        batch,
                        prefix.shape[1],
                        processor.tokenizer.encode("x", add_special_tokens=False)[0],
                    )
                    context = inject_prefix_embeddings(embed, batch["input_ids"], prefix)
                model.model.rope_deltas = None
                with context:
                    result = model.generate(
                        **batch, use_cache=True, max_new_tokens=budget, do_sample=False
                    )
                tokens = result[0, batch["input_ids"].shape[1] :].tolist()
                eos = model.generation_config.eos_token_id
                return (
                    processor.tokenizer.decode(
                        tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
                    ),
                    len(tokens),
                    tokens[-1] in (eos if isinstance(eos, list) else [eos]),
                )

            outputs[mode] = generate(examples, backend, 4096, output_format="grid")
            write(mode + "-prediction.json", outputs[mode])
    write("scores.json", paired_scores(read(safe(root, config["targets"])), config, outputs))


def paired_scores(raw, config, outputs):
    from cptla.reconstruction.scoring import score_groups

    targets = [
        row
        for line in raw.decode("utf-8-sig").split("\n")
        if line.strip() and (row := json.loads(line))["group_id"] in config["group_id"]
    ]
    if len(targets) != 1:
        raise ValueError("target coverage mismatch")
    return {mode: score_groups(targets, rows) for mode, rows in outputs.items()}


if __name__ == "__main__":
    main()
