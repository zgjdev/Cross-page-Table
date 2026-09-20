from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TextIO

from pydantic import ValidationError

from cptla.data.models import DocumentRecord
from cptla.data.pubtables_v2 import (
    load_document_bundle,
    normalize_document_with_stats,
)


def _write_json_line(handle: TextIO, value: object) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rejects", type=Path, required=True)
    parser.add_argument(
        "--source-split",
        choices=("train", "validation", "test", "hidden_test"),
        required=True,
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-rejection-rate", type=float, default=0.001)
    args = parser.parse_args()

    table_paths = sorted((args.input / "tables").glob("*_tables.json"))
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        table_paths = table_paths[: args.limit]
    if not table_paths:
        parser.error(f"no table annotations found under {args.input / 'tables'}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.rejects.parent.mkdir(parents=True, exist_ok=True)
    rejected = 0
    clipped_word_boxes = 0
    with (
        args.output.open("w", encoding="utf-8", newline="\n") as output_handle,
        args.rejects.open("w", encoding="utf-8", newline="\n") as rejects_handle,
    ):
        for tables_path in table_paths:
            record_id = tables_path.name.removesuffix("_tables.json")
            try:
                raw = load_document_bundle(
                    args.input, tables_path, source_split=args.source_split
                )
                normalized, stats = normalize_document_with_stats(raw)
                record = DocumentRecord.model_validate(normalized)
                _write_json_line(output_handle, record.model_dump(mode="json"))
                clipped_word_boxes += stats.clipped_word_boxes
            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                json.JSONDecodeError,
                ValidationError,
            ) as exc:
                rejected += 1
                _write_json_line(
                    rejects_handle,
                    {
                        "source_path": str(tables_path),
                        "record_id": record_id,
                        "source_revision": args.source_revision,
                        "validation_error": f"{type(exc).__name__}: {exc}",
                    },
                )

    processed = len(table_paths)
    rejection_rate = rejected / processed
    print(
        json.dumps(
            {
                "processed": processed,
                "accepted": processed - rejected,
                "rejected": rejected,
                "rejection_rate": rejection_rate,
                "clipped_word_boxes": clipped_word_boxes,
                "source_revision": args.source_revision,
            },
            sort_keys=True,
        )
    )
    return int(rejection_rate > args.max_rejection_rate)


if __name__ == "__main__":
    raise SystemExit(main())
