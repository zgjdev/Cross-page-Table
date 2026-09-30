"""CPU-only, no-GT baseline for adjacent dots.ocr page tables with repeated headers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.cross_page import DocumentTablePrediction
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.simple_merge import merge_repeated_header_pages


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, model: type) -> list:
    with path.open(encoding="utf-8") as handle:
        return [model.model_validate_json(line) for line in handle if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = _load(args.manifest, ImageManifestEntry)
    summary = json.loads((args.adapter_dir / "summary.json").read_text(encoding="utf-8"))
    if summary["mode"] != "no_merge" or summary["inputs"]["manifest"]["sha256"] != _digest(
        args.manifest
    ):
        raise ValueError("adapter source is not this no_merge input manifest")
    names = ("page-results.jsonl", "document-tables.jsonl", "table-evidence.jsonl")
    for name in names:
        if summary["outputs"][name]["sha256"] != _digest(args.adapter_dir / name):
            raise ValueError(f"adapter output changed since audit: {name}")

    page_results = _load(args.adapter_dir / names[0], PredictionRecord)
    tables = _load(args.adapter_dir / names[1], DocumentTablePrediction)
    with (args.adapter_dir / names[2]).open(encoding="utf-8") as handle:
        evidence = [json.loads(line) for line in handle if line.strip()]
    sizes = {}
    for entry in manifest:
        path = args.images / entry.relative_path
        with Image.open(path) as image:
            sizes[entry.image_id] = image.size
    merged, decisions, report = merge_repeated_header_pages(
        manifest, page_results, tables, evidence, sizes
    )
    report["inputs"] = {
        "manifest_sha256": _digest(args.manifest),
        "adapter_summary_sha256": _digest(args.adapter_dir / "summary.json"),
        "adapter_dir": str(args.adapter_dir),
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, rows in (("document-tables.jsonl", merged), ("decisions.jsonl", decisions)):
        payload = "".join(
            json.dumps(
                row.model_dump(mode="json") if hasattr(row, "model_dump") else row,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in rows
        )
        (args.output_dir / name).write_text(payload, encoding="utf-8")
        report[name] = {"rows": len(rows), "sha256": hashlib.sha256(payload.encode()).hexdigest()}
    (args.output_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
