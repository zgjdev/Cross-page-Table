"""Build auditable, unmerged document-table outputs from dots.ocr page predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord, RunManifest
from cptla.evaluation.dotsocr_document import adapt_unmerged_dotsocr
from cptla.evaluation.pubtables_v2 import ImageManifestEntry


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, model: type) -> list:
    result = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    result.append(model.model_validate_json(line))
                except ValueError as error:
                    raise ValueError(f"{path}:{number}: {error}") from error
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, nargs="+", required=True)
    parser.add_argument("--run-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    provenance = None
    if args.run_manifest is not None:
        if len(args.predictions) != 1:
            raise ValueError("one run manifest can certify only its single predictions file")
        provenance = RunManifest.model_validate_json(args.run_manifest.read_text(encoding="utf-8"))
        if provenance.model_name != "dots.ocr" or provenance.input_track != "image-only":
            raise ValueError("run manifest must identify dots.ocr image-only inference")
        if (
            provenance.dataset_name != "kensho/PubTables-v2"
            or provenance.dataset_split != "val"
            or provenance.dataset_revision != "aa575e798cb00a296925e2086addb3e3fd9a1903"
        ):
            raise ValueError("run manifest does not describe fixed PubTables-v2 validation")
        if provenance.input_manifest_sha256 != _digest(args.manifest):
            raise ValueError("run manifest input hash differs from input manifest")
        if provenance.predictions_path.resolve() != args.predictions[0].resolve():
            raise ValueError("run manifest predictions path differs from input")
    manifest = _load(args.manifest, ImageManifestEntry)
    predictions = [row for path in args.predictions for row in _load(path, PredictionRecord)]
    pages, tables, evidence, summary = adapt_unmerged_dotsocr(
        manifest, predictions, require_complete=not args.partial
    )
    summary["inputs"] = {
        "manifest": {"path": str(args.manifest), "sha256": _digest(args.manifest)},
        "predictions": [{"path": str(path), "sha256": _digest(path)} for path in args.predictions],
        "run_manifest": (
            {
                "path": str(args.run_manifest),
                "sha256": _digest(args.run_manifest),
                "run_id": provenance.run_id,
                "model_revision": provenance.model_revision,
                "dataset_revision": provenance.dataset_revision,
            }
            if provenance
            else None
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, rows in (
        ("page-results.jsonl", pages),
        ("document-tables.jsonl", tables),
        ("table-evidence.jsonl", evidence),
    ):
        payload = "".join(
            json.dumps(
                row.model_dump(mode="json") if hasattr(row, "model_dump") else row,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in rows
        )
        path = args.output_dir / name
        path.write_text(payload, encoding="utf-8")
        summary.setdefault("outputs", {})[name] = {
            "rows": len(rows),
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
