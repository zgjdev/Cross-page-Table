"""Offline GriTS scoring with an exact input-coverage gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import load_truth_directory, score_predictions


def _load_manifest(path: Path) -> list[ImageManifestEntry]:
    return [
        ImageManifestEntry.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_predictions(paths: list[Path]) -> list[PredictionRecord]:
    records: list[PredictionRecord] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(PredictionRecord.model_validate_json(line))
            except ValueError as error:
                raise ValueError(f"invalid prediction at {path}:{line_number}: {error}") from error
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", nargs="+", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--truth-dir", type=Path, required=True)
    parser.add_argument(
        "--collection",
        choices=("cropped_tables", "full_documents"),
        required=True,
    )
    parser.add_argument("--metrics-output", type=Path, required=True)
    parser.add_argument("--failures-output", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()

    metrics, failures = score_predictions(
        _load_manifest(args.manifest),
        _load_predictions(args.predictions),
        load_truth_directory(args.truth_dir, args.collection),
        require_complete=not args.partial,
    )
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.failures_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.failures_output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in failures),
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
