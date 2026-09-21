"""Run resumable dots.ocr inference from a frozen PubTables-v2 image manifest."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.dotsocr import (
    completed_ids_from_files,
    extract_table_html,
    pending_manifest_entries,
    require_appendable_output,
)
from cptla.evaluation.pubtables_v2 import ImageManifestEntry

PROMPT = """Please output the layout information from the PDF image, including each layout
element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]
2. Layout Categories: ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer',
   'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].
3. Text rules: Picture omits text; Formula uses LaTeX; Table uses HTML; all others use
   Markdown.
4. Preserve original text without translation and sort in human reading order.
5. Return one JSON object.
"""


def load_manifest(path: Path) -> list[ImageManifestEntry]:
    entries = [
        ImageManifestEntry.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    image_ids = [entry.image_id for entry in entries]
    if len(image_ids) != len(set(image_ids)):
        raise ValueError("input manifest contains duplicate image_id values")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path, nargs="*", default=[])
    parser.add_argument("--max-new-tokens", type=int, default=24000)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    entries = load_manifest(args.manifest)
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        entries = entries[: args.limit]
    historical_ids = completed_ids_from_files(args.resume_from)
    output_ids = require_appendable_output(args.output)
    overlap = historical_ids & output_ids
    if overlap:
        duplicate = sorted(overlap)[0]
        raise ValueError(f"prediction ID appears in history and output: {duplicate}")
    pending = pending_manifest_entries(entries, historical_ids | output_ids)
    missing = [
        entry.relative_path
        for entry in pending
        if not (args.images / entry.relative_path).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"missing {len(missing)} manifest images; first={missing[0]}")

    import torch
    from qwen_vl_utils import process_vision_info
    from transformers import AutoModelForCausalLM, AutoProcessor

    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=True, use_fast=False)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="cuda",
    ).eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8", newline="\n") as stream:
        for index, entry in enumerate(pending, start=1):
            image_path = args.images / entry.relative_path
            started = time.time()
            try:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": str(image_path)},
                            {"type": "text", "text": PROMPT},
                        ],
                    }
                ]
                prompt = processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                image_inputs, video_inputs = process_vision_info(messages)
                inputs = processor(
                    text=[prompt],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                ).to("cuda")
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=args.max_new_tokens,
                        do_sample=False,
                    )
                output = processor.batch_decode(
                    [
                        ids[len(input_ids) :]
                        for ids, input_ids in zip(generated, inputs.input_ids, strict=True)
                    ],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )[0]
                tables, warnings = extract_table_html(output)
                record = PredictionRecord(
                    image_id=entry.image_id,
                    unit_id=entry.unit_id,
                    status="ok",
                    tables_html=tables,
                    elapsed_sec=round(time.time() - started, 3),
                    raw_output=output,
                    warnings=warnings,
                )
            except Exception as error:
                record = PredictionRecord(
                    image_id=entry.image_id,
                    unit_id=entry.unit_id,
                    status="error",
                    tables_html=[],
                    elapsed_sec=round(time.time() - started, 3),
                    error=f"{type(error).__name__}: {error}",
                )
            stream.write(record.model_dump_json() + "\n")
            stream.flush()
            summary = record.model_dump(exclude={"raw_output", "tables_html"})
            summary["index"] = index
            print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
