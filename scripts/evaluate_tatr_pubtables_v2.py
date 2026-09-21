"""Evaluate TATR-v1.1-Pub with Direct Text on PubTables-v2 Cropped Tables."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.dotsocr import (
    completed_ids_from_files,
    pending_manifest_entries,
    require_appendable_output,
)
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.tatr import (
    associated_cropped_paths,
    load_pdf_words,
    make_official_postprocessor,
    normalize_words_to_image,
    tatr_objects_to_prediction,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--words", type=Path, required=True)
    parser.add_argument("--truth-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path, nargs="*", default=[])
    parser.add_argument(
        "--official-postprocess",
        type=Path,
        default=Path("third_party/table-transformer-main/src/postprocess.py"),
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    import torch
    import yaml
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForObjectDetection

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    entries = [
        ImageManifestEntry.model_validate_json(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        entries = entries[: args.limit]
    historical_ids = completed_ids_from_files(args.resume_from)
    output_ids = require_appendable_output(args.output)
    if overlap := historical_ids & output_ids:
        raise ValueError(f"prediction ID appears in history and output: {sorted(overlap)[0]}")
    pending = pending_manifest_entries(entries, historical_ids | output_ids)

    spec = importlib.util.spec_from_file_location(
        "cptla_tatr_postprocess", args.official_postprocess
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load official postprocess module: {args.official_postprocess}")
    postprocess_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(postprocess_module)
    postprocessor = make_official_postprocessor(postprocess_module)

    processor = AutoImageProcessor.from_pretrained(
        args.model, local_files_only=True, revision=config["model_revision"]
    )
    model = AutoModelForObjectDetection.from_pretrained(
        args.model,
        local_files_only=True,
        revision=config["model_revision"],
    ).to(args.device).eval()
    torch.manual_seed(config["seed"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8", newline="\n") as stream:
        for entry in pending:
            started = time.time()
            try:
                image_path = args.images / entry.relative_path
                if not image_path.is_file():
                    raise FileNotFoundError(f"missing image: {image_path}")
                words_path, _ = associated_cropped_paths(entry, args.words, args.truth_dir)
                with Image.open(image_path) as source_image:
                    image = source_image.convert("RGB")
                words = normalize_words_to_image(load_pdf_words(words_path), image.size)
                inputs = processor(images=image, return_tensors="pt").to(args.device)
                with torch.inference_mode():
                    outputs = model(**inputs)
                target_sizes = torch.tensor([[image.height, image.width]], device=args.device)
                result = processor.post_process_object_detection(
                    outputs,
                    threshold=0.0,
                    target_sizes=target_sizes,
                )[0]
                record = tatr_objects_to_prediction(
                    image_id=entry.image_id,
                    unit_id=entry.unit_id,
                    boxes=result["boxes"].detach().cpu().tolist(),
                    labels=result["labels"].detach().cpu().tolist(),
                    scores=result["scores"].detach().cpu().tolist(),
                    words=words,
                    thresholds=config["thresholds"],
                    postprocessor=postprocessor,
                    elapsed_sec=round(time.time() - started, 3),
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
            print(
                json.dumps(
                    record.model_dump(exclude={"raw_output", "tables_html"}),
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
