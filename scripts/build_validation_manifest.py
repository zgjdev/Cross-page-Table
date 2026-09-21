"""Build a deterministic PubTables-v2 image manifest without consulting truth labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cptla.evaluation.pubtables_v2 import build_image_manifest, write_image_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument(
        "--collection",
        choices=("cropped_tables", "full_documents"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()

    records = build_image_manifest(args.images, args.collection)
    if args.expected_count is not None and len(records) != args.expected_count:
        parser.error(f"expected {args.expected_count} images, found {len(records)}")
    digest = write_image_manifest(records, args.output)
    print(
        json.dumps(
            {
                "collection": args.collection,
                "count": len(records),
                "manifest": str(args.output),
                "sha256": digest,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
