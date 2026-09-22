"""Rebuild TATR prediction HTML from saved postprocessed cells."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cptla.evaluation.tatr_rebuild import rebuild_tatr_predictions_jsonl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = rebuild_tatr_predictions_jsonl(args.source, args.output)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
