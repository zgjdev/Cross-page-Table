"""固定上游下，比较单片图像与相邻页证据对局部重识别的作用。"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from review_reconstruction_qwen_smoke import generate, gpu_guard, input_examples, safe

from cptla.reconstruction.alignment_baseline import align_group
from cptla.reconstruction.data import DATASET_REVISION
from cptla.reconstruction.grid import GridError, html_to_grid
from cptla.reconstruction.qwen_processor import QwenProcessorAdapter
from cptla.reconstruction.scoring import score_groups

BASELINE = Path("artifacts/reconstruction-baselines/20261114T153243Z-200table-b0")
BASELINE_PREDICTIONS_SHA = "8be80cbd0ff3e6be3064051208fed1d157b6a46939d581e7144e64d050e97f2c"
BASELINE_HASHES_SHA = "533f524b306ebfa41ea867a79f0fdab208b0677b1a8febe0cef9b07d66c2673d"
BASELINE_MANIFEST_SHA = "c5db49a49682223c0713a733eedfbea458f8db7e607bfa9a221387845a7647e2"
INPUTS = Path("artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/inputs.jsonl")
TARGETS = INPUTS.with_name("targets.jsonl")
MODEL_REFERENCE = Path(
    "artifacts/reconstruction-structure-prefix/20261120T125300Z-prefix-native-fp32"
)
MODEL_REVISION = "89644892e4d85e24eaac8bacfd4f463576704203"
ORDER = ("page_num", "part_index")
IDENTITY = ("group_id", "fragment_id", *ORDER)
ARMS = ("local_image", "adjacent_same_table")
TEXT_CONTROL = "adjacent_html_only"
PROMPT = (
    "请重新识别最后标明的目标片段。目标图像是最终依据，已有 HTML 可能错列或漏格。"
    "可用的相邻片段仅用于判断列序与跨列单元格，禁止抄入它的任何行或文字。"
    "保留目标图中的所有行、列、表头和单元格文字。只输出一个完整的 HTML <table>，"
    "使用 rowspan 和 colspan 表示合并单元格，不添加解释或代码围栏。"
)


def select_cases(rows, seed, case_count=3):
    cohort = [
        row for row in rows if row["diagnostics"].get("failure_reasons") == ["column_mismatch"]
    ]
    if len(rows) != 200 or len({row["group_id"] for row in rows}) != 200 or len(cohort) != 30:
        raise ValueError("expected frozen 200-table inventory including 30 column conflicts")
    cases = []
    for row in sorted(cohort, key=lambda row: row["group_id"]):
        fragments = sorted(
            row["diagnostics"]["raw_predictions"], key=lambda part: tuple(part[k] for k in ORDER)
        )
        if len(fragments) < 2 or any(
            part["group_id"] != row["group_id"] or part["status"] != "completed"
            for part in fragments
        ):
            raise ValueError("baseline fragment identity or status mismatch")
        widths = [html_to_grid(part["html"]).n_cols for part in fragments]
        for i, width in enumerate(widths):
            other_widths = set(widths[:i] + widths[i + 1 :])
            if len(other_widths) != 1 or width in other_widths:
                continue
            adjacent = [
                j
                for j in (i - 1, i + 1)
                if 0 <= j < len(fragments) and fragments[j]["page_num"] != fragments[i]["page_num"]
            ]
            if adjacent:
                j = min(
                    adjacent,
                    key=lambda j: (abs(fragments[j]["page_num"] - fragments[i]["page_num"]), j),
                )
                cases.append(
                    dict(
                        group_id=row["group_id"],
                        fragments=fragments,
                        target=i,
                        context=j,
                        widths=widths,
                    )
                )
                break
    if not 3 <= case_count <= min(16, len(cases)):
        raise ValueError("require 3–16 eligible column-conflict cases")
    rng = random.Random(seed)
    selected = rng.sample(cases, 3)
    first_ids = {case["group_id"] for case in selected}
    remaining = [case for case in cases if case["group_id"] not in first_ids]
    selected.extend(rng.sample(remaining, case_count - 3))
    return selected, len(cases)


def arm_messages(example, case, mode):
    if mode not in (*ARMS, TEXT_CONTROL):
        raise ValueError("unknown visual repair arm")
    items = example["messages"][0]["content"][1:]
    pairs = list(zip(items[::2], items[1::2], strict=True))
    if len(pairs) != len(case["fragments"]) or any(
        image["type"] != "image" or text["type"] != "text" or text["text"] != part["html"]
        for (image, text), part in zip(pairs, case["fragments"], strict=True)
    ):
        raise ValueError("baseline and verified upstream fragments differ")
    content = [dict(type="text", text=PROMPT)]
    if mode in ("adjacent_same_table", TEXT_CONTROL):
        image, text = pairs[case["context"]]
        content.extend(
            [
                dict(type="text", text="相邻片段及其已有识别，仅作列结构参考："),
                *([image] if mode == "adjacent_same_table" else []),
                text,
            ]
        )
    content.extend([dict(type="text", text="目标片段及其已有识别："), *pairs[case["target"]]])
    return [dict(role="user", content=content)]


def apply_repair(case, prediction):
    fragments = case["fragments"]
    index = case["target"]
    before = html_to_grid(fragments[index]["html"])
    changed = dict(original_rows=before.n_rows, original_columns=before.n_cols)
    if prediction["status"] == "completed":
        try:
            after = html_to_grid(prediction["html"])
        except GridError as err:
            prediction = dict(prediction, status="invalid_html", error=str(err))
        else:
            changed.update(
                repair_rows=after.n_rows,
                repair_columns=after.n_cols,
                row_delta=after.n_rows - before.n_rows,
                column_delta=after.n_cols - before.n_cols,
            )
    edited = list(fragments)
    edited[index] = dict(edited[index], html=prediction["html"], status=prediction["status"])
    merged = align_group(case["group_id"], edited, fragments)
    return dict(raw_prediction=prediction, changed_dimensions=changed, merged=merged)


def run(args):
    root = args.project_root.resolve()
    if not re.fullmatch(r"\d{8}T\d{6}Z-[A-Za-z0-9_-]+", args.run):
        raise ValueError("timestamped run required")
    if not 1280 <= args.max_new_tokens <= 4096 or args.gpu < 0:
        raise ValueError("probe requires 1280–4096 new tokens per arm and a nonnegative GPU")
    out = safe(root, Path("artifacts/reconstruction-diagnostics") / args.run)
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def read(path, expected=None):
        path = safe(root, path)
        raw = path.read_bytes()
        key = path.relative_to(root).as_posix()
        sha = hashlib.sha256(raw).hexdigest()
        if (expected is not None and expected != sha) or hashes.setdefault(key, sha) != sha:
            raise ValueError(f"input SHA mismatch: {key}")
        return raw

    def write(name, value):
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)

    rows = json.loads(read(BASELINE / "predictions.json", BASELINE_PREDICTIONS_SHA))
    frozen = json.loads(read(BASELINE / "input-hashes.json", BASELINE_HASHES_SHA))
    baseline_manifest = json.loads(read(BASELINE / "run-manifest.json", BASELINE_MANIFEST_SHA))
    cases, n_candidates = select_cases(rows, args.seed, case_count=args.case_count)
    arms = (*ARMS, TEXT_CONTROL) if args.text_control else ARMS
    groups = [case["group_id"] for case in cases]

    def pinned_read(path, expected=None):
        key = path.relative_to(root).as_posix()
        if path != safe(root, INPUTS):
            pinned = frozen[key]
            if expected is not None and expected != pinned:
                raise ValueError("crop/source SHA disagrees with the frozen baseline")
            expected = pinned
        return read(path, expected)

    config = dict(
        inputs=INPUTS,
        group_id=groups,
        upstream_run=baseline_manifest["parameters"]["upstream_runs"],
    )
    examples, images = input_examples(root, config, pinned_read)
    selection = []
    prompts = {arm: [] for arm in arms}
    for case, example in zip(cases, examples, strict=True):
        selection.append(
            dict(
                group_id=case["group_id"],
                widths=case["widths"],
                target={k: case["fragments"][case["target"]][k] for k in IDENTITY},
                context={k: case["fragments"][case["context"]][k] for k in IDENTITY},
            )
        )
        for arm in arms:
            prompts[arm].append(
                dict(
                    group_id=example["group_id"],
                    source_pages=[case["fragments"][case["target"]]["page_num"]],
                    messages=arm_messages(example, case, arm),
                )
            )

    model_config = json.loads(read(MODEL_REFERENCE / "run-manifest.json"))["config"]
    model_path = safe(root, Path(model_config["model"]))
    model_hashes = json.loads(read(MODEL_REFERENCE / "validation-reference.json"))["model_hashes"]
    if not model_hashes or not any(Path(name).suffix == ".safetensors" for name in model_hashes):
        raise ValueError("missing frozen Qwen weight hash")
    write(
        "manifest.json",
        dict(
            argv=sys.argv,
            started_utc=datetime.now(UTC).isoformat(),
            commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            dataset_revision=DATASET_REVISION,
            model_revision=MODEL_REVISION,
            model=str(model_path),
            model_hashes=model_hashes,
            seed=args.seed,
            n_candidates=n_candidates,
            selection_rule=(
                "sorted seed sample, one odd-width fragment, first eligible target on ties,"
                " nearest adjacent page"
            ),
            selection=selection,
            hashes=hashes,
            generation=dict(dtype="bfloat16", sample=False, budget=args.max_new_tokens),
            split="train_fit",
            scope="bounded column-conflict development probe",
            arms=arms,
            gpu=args.gpu,
            prepare_only=args.prepare_only,
        ),
    )
    write("input-examples.json", prompts)
    if args.prepare_only:
        print(json.dumps(dict(groups=selection, output=str(out)), ensure_ascii=False))
        return

    for name, digest in model_hashes.items():
        path = safe(root, Path(name))
        if not path.is_relative_to(model_path):
            raise ValueError("frozen model file outside model directory")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError(f"model SHA mismatch: {name}")
    for env in ("HF_HOME", "XDG_CACHE_HOME", "TMPDIR"):
        path = out / env.lower()
        path.mkdir()
        os.environ[env] = str(path)
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
        CUDA_VISIBLE_DEVICES=str(args.gpu),
    )
    write("gpu-before.json", gpu_guard(args.gpu, 20480))
    import torch
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    torch.manual_seed(args.seed)
    processor = AutoProcessor.from_pretrained(
        model_path, local_files_only=True, min_pixels=65536, max_pixels=262144
    )
    encoder = QwenProcessorAdapter(processor, root, images)
    model = (
        Qwen3VLForConditionalGeneration.from_pretrained(
            model_path, local_files_only=True, dtype=torch.bfloat16, attn_implementation="sdpa"
        )
        .to("cuda")
        .eval()
    )
    write("environment.json", dict(torch=torch.__version__, gpu=torch.cuda.get_device_name()))

    def backend(messages, budget):
        gpu_guard(args.gpu, 8192)
        encoded = encoder(messages, add_generation_prompt=True, truncation=False)
        batch = {
            key: torch.tensor([value], device="cuda")
            if isinstance(value, list)
            else value.to("cuda")
            for key, value in encoded.items()
            if key != "token_type_ids"
        }
        model.model.rope_deltas = None
        with torch.inference_mode():
            result = model.generate(**batch, use_cache=True, max_new_tokens=budget, do_sample=False)
        tokens = result[0, batch["input_ids"].shape[1] :].tolist()
        eos = model.generation_config.eos_token_id
        raw = processor.tokenizer.decode(
            tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return (
            raw,
            len(tokens),
            bool(tokens and tokens[-1] in (eos if isinstance(eos, list) else [eos])),
        )

    predictions = {
        "unchanged": [align_group(c["group_id"], c["fragments"], c["fragments"]) for c in cases]
    }
    for arm in arms:
        predictions[arm] = []
        for index, (example, case) in enumerate(zip(prompts[arm], cases, strict=True), 1):
            raw = generate([example], backend, args.max_new_tokens)[0]
            repair = apply_repair(case, raw)
            write(f"{arm}-{index:02d}.json", repair)
            predictions[arm].append(repair["merged"])
    write("predictions.json", predictions)

    # Ground truth is allowed only after all input-only arms have been persisted.
    targets = [
        row
        for line in read(TARGETS, frozen[TARGETS.as_posix()]).decode("utf-8-sig").split("\n")
        if line.strip() and (row := json.loads(line))["group_id"] in groups
    ]
    if len(targets) != len(groups) or {row["group_id"] for row in targets} != set(groups):
        raise ValueError("target coverage mismatch")
    scores = {name: score_groups(targets, results) for name, results in predictions.items()}
    write("scores.json", scores)
    write(
        "summary.json",
        dict(
            status="completed",
            groups=groups,
            ended_utc=datetime.now(UTC).isoformat(),
            rates={name: score["diagnostic_rates"] for name, score in scores.items()},
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=1280)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--case-count", type=int, default=3)
    parser.add_argument("--text-control", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
