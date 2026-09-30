"""Score complete document-level table outputs against PubTables-v2 validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.cross_page import DocumentTablePrediction, score_cross_page
from cptla.evaluation.pubtables_v2 import ImageManifestEntry


def load_jsonl(path: Path, model: type) -> list:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(model.model_validate_json(line))
                except ValueError as error:
                    raise ValueError(f"{path}:{number}: {error}") from error
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--page-results", required=True, type=Path)
    parser.add_argument("--document-tables", required=True, type=Path)
    parser.add_argument("--truth-dir", required=True, type=Path)
    parser.add_argument("--cross-page-gold", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    manifest = load_jsonl(args.manifest, ImageManifestEntry)
    docs = {entry.document_id for entry in manifest}
    truth = {}
    for doc in sorted(docs):
        path = args.truth_dir / f"{doc}_tables.json"
        truth[doc] = json.loads(path.read_text(encoding="utf-8"))
    with args.cross_page_gold.open(encoding="utf-8") as handle:
        gold = [json.loads(line) for line in handle if line.strip()]
    if args.partial:
        gold = [row for row in gold if row["document_id"] in docs]
    metrics, matches, failures = score_cross_page(
        manifest,
        load_jsonl(args.page_results, PredictionRecord),
        load_jsonl(args.document_tables, DocumentTablePrediction),
        truth,
        gold,
        require_complete=not args.partial,
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    for name, rows in (("matches.jsonl", matches), ("failures.jsonl", failures)):
        (args.output_dir / name).write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
