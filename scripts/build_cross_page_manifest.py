"""Audit PubTables-v2 validation cross-page tables without changing source data."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cptla.evaluation.pubtables_v2 import (
    ImageManifestEntry,
    build_image_manifest,
    parse_full_document_image_id,
)


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    lines = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    return "".join(lines).encode("utf-8")


def _document_paths(directory: Path, suffix: str) -> dict[str, Path]:
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    paths: dict[str, Path] = {}
    for path in directory.glob(f"*{suffix}"):
        document_id = path.name.removesuffix(suffix)
        if not document_id or document_id in paths:
            raise ValueError(f"invalid or duplicate document filename: {path}")
        paths[document_id] = path
    return paths


def _manifest_pages(manifest_path: Path, images_dir: Path) -> dict[str, set[int]]:
    entries = [
        ImageManifestEntry.model_validate_json(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if entries != build_image_manifest(images_dir, "full_documents"):
        raise ValueError("manifest differs from the actual full-document image directory")
    pages: dict[str, set[int]] = defaultdict(set)
    for entry in entries:
        if entry.page_number is None:
            raise ValueError(f"missing page number: {entry.image_id}")
        pages[entry.document_id].add(entry.page_number)
    return dict(pages)


def audit_validation(
    *,
    manifest_path: Path,
    images_dir: Path,
    tables_dir: Path,
    pairs_dir: Path,
    train_tables_dir: Path,
    test_tables_dir: Path,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    pages = _manifest_pages(manifest_path, images_dir)
    tables_paths = _document_paths(tables_dir, "_tables.json")
    pairs_paths = _document_paths(pairs_dir, ".json")
    if set(tables_paths) != set(pages) or set(pairs_paths) != set(pages):
        raise ValueError(
            "document ID mismatch: "
            f"missing_tables={sorted(set(pages) - set(tables_paths))[:3]}, "
            f"extra_tables={sorted(set(tables_paths) - set(pages))[:3]}, "
            f"missing_pairs={sorted(set(pages) - set(pairs_paths))[:3]}, "
            f"extra_pairs={sorted(set(pairs_paths) - set(pages))[:3]}"
        )
    train_ids = set(_document_paths(train_tables_dir, "_tables.json"))
    test_ids = set(_document_paths(test_tables_dir, "_tables.json"))
    if (train_ids & set(pages)) or (test_ids & set(pages)) or (train_ids & test_ids):
        raise ValueError("document IDs overlap across train, validation, or test")

    gold: list[dict[str, Any]] = []
    official_pairs: list[dict[str, Any]] = []
    negative_pairs: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    nonadjacent_gaps: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    span_histogram: Counter[int] = Counter()

    for document_id in sorted(pages):
        document_pages = pages[document_id]
        if document_pages != set(range(max(document_pages) + 1)):
            raise ValueError(f"non-contiguous page images for {document_id}")
        tables = json.loads(tables_paths[document_id].read_text(encoding="utf-8"))
        pairs = json.loads(pairs_paths[document_id].read_text(encoding="utf-8"))
        if not isinstance(tables, list) or not isinstance(pairs, list):
            raise ValueError(f"tables and pairs must be lists: {document_id}")

        adjacency: dict[tuple[int, int], list[str]] = defaultdict(list)
        for index, table in enumerate(tables):
            if not isinstance(table, dict) or not isinstance(table.get("html"), str):
                raise ValueError(f"invalid table/HTML: {document_id} table {index}")
            parts = table.get("parts")
            if not isinstance(parts, list) or not parts:
                raise ValueError(f"missing parts: {document_id} table {index}")
            table_id = f"{document_id}-table-{index}"
            part_rows = []
            for part_index, part in enumerate(parts):
                if not isinstance(part, dict) or type(part.get("page_num")) is not int:
                    raise ValueError(f"invalid page_num: {table_id} part {part_index}")
                page_number = part["page_num"]
                if page_number not in document_pages:
                    raise ValueError(f"part page without image: {table_id} page {page_number}")
                if not isinstance(part.get("bbox"), list) or len(part["bbox"]) != 4:
                    raise ValueError(f"invalid bbox: {table_id} part {part_index}")
                part_rows.append(
                    {
                        "fragment_id": f"{table_id}-part-{part_index}",
                        "page_num": page_number,
                        "page_object_num": part.get("page_object_num"),
                        "bbox": part["bbox"],
                        "pdf_bbox": part.get("pdf_bbox"),
                    }
                )
            counts["all_logical_tables"] += 1
            distinct_pages = sorted({part["page_num"] for part in part_rows})
            if len(part_rows) > 1 and len(distinct_pages) == 1:
                counts["multi_part_single_page_tables"] += 1
            if len(distinct_pages) < 2:
                continue
            span_histogram[len(distinct_pages)] += 1
            gold.append(
                {
                    "document_id": document_id,
                    "table_id": table_id,
                    "table_index": index,
                    "source_split": "val",
                    "source_tables_file": tables_paths[document_id].name,
                    "page_numbers": distinct_pages,
                    "parts": part_rows,
                    "html": table["html"],
                    "label_origin": "derived_from_logical_table_parts",
                }
            )
            for first, second in zip(distinct_pages, distinct_pages[1:], strict=False):
                if second == first + 1:
                    adjacency[(first, second)].append(table_id)
                else:
                    nonadjacent_gaps.append(
                        {
                            "document_id": document_id,
                            "table_id": table_id,
                            "page_before": first,
                            "page_after": second,
                            "intervening_pages": list(range(first + 1, second)),
                            "source": "derived_from_logical_table_parts",
                        }
                    )

        seen_pairs: set[tuple[int, int]] = set()
        for pair in pairs:
            if not isinstance(pair, dict) or type(pair.get("label")) is not int:
                raise ValueError(f"invalid page-pair label: {document_id}")
            label = pair["label"]
            if label not in (0, 1):
                raise ValueError(f"non-binary page-pair label: {document_id}: {label}")
            page_a, page_b = pair.get("page_A"), pair.get("page_B")
            if not isinstance(page_a, str) or not isinstance(page_b, str):
                raise ValueError(f"missing page-pair ID: {document_id}")
            doc_a, first = parse_full_document_image_id(f"{page_a}.jpg")
            doc_b, second = parse_full_document_image_id(f"{page_b}.jpg")
            if doc_a != document_id or doc_b != document_id:
                raise ValueError(f"cross-document pair: {document_id}: {page_a}, {page_b}")
            if first not in document_pages or second not in document_pages:
                raise ValueError(f"pair page without image: {document_id}: {page_a}, {page_b}")
            key = (first, second)
            if key in seen_pairs:
                raise ValueError(f"duplicate pair: {document_id}: {key}")
            seen_pairs.add(key)
            counts[f"official_label_{label}"] += 1
            candidates = sorted(adjacency.get(key, []))
            row = {
                "document_id": document_id,
                "page_A": page_a,
                "page_B": page_b,
                "label": label,
                "source": "official_cross_page_table_pairs",
                "derived_candidate_table_ids": candidates,
            }
            official_pairs.append(row)
            if label == 0:
                negative_pairs.append(row)
            if second != first + 1:
                discrepancies.append({**row, "reason": "nonadjacent_official_pair"})
            if label == 1 and not candidates:
                discrepancies.append({**row, "reason": "positive_without_derived_table"})
            if label == 0 and candidates:
                discrepancies.append({**row, "reason": "negative_with_derived_table"})
        for (first, second), candidate_ids in adjacency.items():
            if (first, second) not in seen_pairs:
                discrepancies.append(
                    {
                        "document_id": document_id,
                        "page_A": f"{document_id}_page_{first}",
                        "page_B": f"{document_id}_page_{second}",
                        "reason": "derived_adjacency_without_official_pair",
                        "derived_candidate_table_ids": sorted(candidate_ids),
                    }
                )

    summary = {
        "dataset": "PubTables-v2 Full Documents",
        "dataset_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
        "split": "val",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "image_pages": sum(map(len, pages.values())),
        "validation_documents": len(pages),
        "train_document_ids_checked": len(train_ids),
        "test_document_ids_checked_by_filename_only": len(test_ids),
        "logical_tables": counts["all_logical_tables"],
        "cross_page_tables": len(gold),
        "multi_part_single_page_tables": counts["multi_part_single_page_tables"],
        "cross_page_pages_per_table": dict(sorted(span_histogram.items())),
        "nonadjacent_part_page_gaps": len(nonadjacent_gaps),
        "official_positive_pairs": counts["official_label_1"],
        "official_negative_pairs": counts["official_label_0"],
        "pair_discrepancies": len(discrepancies),
        "discrepancy_reasons": dict(
            sorted(Counter(row["reason"] for row in discrepancies).items())
        ),
        "cross_page_label_origin": "derived_from_logical_table_parts",
        "page_pair_label_origin": "official_cross_page_table_pairs",
    }
    return summary, {
        "gold-cross-page.jsonl": gold,
        "official-page-pairs.jsonl": official_pairs,
        "negative-page-pairs.jsonl": negative_pairs,
        "discrepancies.jsonl": discrepancies,
        "nonadjacent-part-gaps.jsonl": nonadjacent_gaps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--tables", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--train-tables", required=True, type=Path)
    parser.add_argument("--test-tables", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error(f"output directory already exists: {args.output_dir}")
    summary, rows = audit_validation(
        manifest_path=args.manifest,
        images_dir=args.images,
        tables_dir=args.tables,
        pairs_dir=args.pairs,
        train_tables_dir=args.train_tables,
        test_tables_dir=args.test_tables,
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for filename, records in rows.items():
        payload = _jsonl_bytes(records)
        (args.output_dir / filename).write_bytes(payload)
        hashes[filename] = hashlib.sha256(payload).hexdigest()
    summary["output_sha256"] = hashes
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
