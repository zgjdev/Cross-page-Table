"""Run resumable dots.ocr inference on PubTables-v2 validation pages."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoProcessor
from qwen_vl_utils import process_vision_info

PROMPT = """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]
2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].
3. Text Extraction & Formatting Rules:
- Picture: omit the text field.
- Formula: format text as LaTeX.
- Table: format text as HTML.
- All others: format text as Markdown.
4. The output text must be original, without translation, and sorted in human reading order.
5. The entire output must be a single JSON object."""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=24000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = set()
    if args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            try:
                completed.add(json.loads(line)["image"])
            except (json.JSONDecodeError, KeyError):
                pass

    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=True, use_fast=False)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda"
    ).eval()
    if args.manifest:
        images = [args.images / name for name in args.manifest.read_text().splitlines() if name]
        missing = [str(path) for path in images if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing {len(missing)} manifest images; first={missing[0]}")
    else:
        images = sorted(args.images.glob("*.jpg"))
    if args.limit is not None:
        images = images[: args.limit]

    with args.output.open("a", encoding="utf-8") as stream:
        for index, image_path in enumerate(images, 1):
            image = str(image_path)
            if image in completed:
                continue
            started = time.time()
            record = {"image": image, "index": index}
            try:
                messages = [{"role": "user", "content": [
                    {"type": "image", "image": image}, {"type": "text", "text": PROMPT}
                ]}]
                text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                image_inputs, video_inputs = process_vision_info(messages)
                inputs = processor(
                    text=[text], images=image_inputs, videos=video_inputs,
                    padding=True, return_tensors="pt"
                ).to("cuda")
                with torch.inference_mode():
                    generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False)
                output = processor.batch_decode(
                    [ids[len(input_ids):] for ids, input_ids in zip(generated, inputs.input_ids)],
                    skip_special_tokens=True, clean_up_tokenization_spaces=False,
                )[0]
                record.update(status="ok", output=output, output_chars=len(output))
            except Exception as error:
                record.update(status="error", error=f"{type(error).__name__}: {error}")
            record["elapsed_sec"] = round(time.time() - started, 3)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            print(json.dumps({k: record[k] for k in record if k != "output"}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
