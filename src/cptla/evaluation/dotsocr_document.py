"""Convert page-level dots.ocr predictions into an unmerged document-table baseline."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from cptla.evaluation.contracts import CoverageReport, PredictionRecord
from cptla.evaluation.cross_page import DocumentTablePrediction
from cptla.evaluation.dotsocr import extract_table_html, parse_layout
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import IncompleteCoverageError


def adapt_unmerged_dotsocr(
    manifest: list[ImageManifestEntry],
    predictions: list[PredictionRecord],
    *,
    require_complete: bool = True,
) -> tuple[list[PredictionRecord], list[DocumentTablePrediction], list[dict[str, Any]], dict]:
    """Return page statuses, unmerged tables, raw-layout evidence and counters.

    No ground truth, pair label, or inference heuristic is used here.
    """
    entries = {entry.image_id: entry for entry in manifest}
    if len(entries) != len(manifest):
        raise ValueError("duplicate manifest image ID")
    if any(entry.page_number is None or entry.document_id != entry.unit_id for entry in manifest):
        raise ValueError("expected full-document manifest with page numbers")
    if len({(entry.document_id, entry.page_number) for entry in manifest}) != len(manifest):
        raise ValueError("duplicate document/page in manifest")
    coverage = CoverageReport.from_ids(
        [entry.image_id for entry in manifest], [row.image_id for row in predictions]
    )
    if coverage.duplicates:
        raise ValueError(f"duplicate input image ID: {coverage.duplicates[0]}")
    if coverage.extra:
        raise ValueError(f"prediction outside manifest: {coverage.extra[0]}")
    if require_complete and not coverage.is_complete:
        raise IncompleteCoverageError(f"incomplete dots.ocr page coverage: {coverage.model_dump()}")

    status_rows: list[PredictionRecord] = []
    tables: list[DocumentTablePrediction] = []
    evidence: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    rows = {row.image_id: row for row in predictions}
    for entry in sorted(manifest, key=lambda item: (item.document_id, item.page_number)):
        row = rows.get(entry.image_id)
        if row is None:
            continue
        if row.unit_id != entry.unit_id:
            raise ValueError(f"dots.ocr unit mismatch: {row.image_id}")
        if row.status == "error" and row.tables_html:
            raise ValueError(f"failed page contains tables: {row.image_id}")
        page_tables = []
        if row.status == "ok" and row.raw_output is not None:
            page_tables, raw_warnings = extract_table_html(row.raw_output)
            if page_tables != row.tables_html or raw_warnings != row.warnings:
                raise ValueError(f"raw layout differs from saved HTML/warnings: {row.image_id}")
        elif row.status == "ok" and row.tables_html:
            raise ValueError(f"table provenance requires raw_output: {row.image_id}")

        status_rows.append(row.model_copy(update={"tables_html": [], "raw_output": None}))
        counts["page_results"] += 1
        counts["inference_errors"] += row.status == "error"
        counts["runner_warnings"] += len(row.warnings)
        if not page_tables:
            continue
        layout = parse_layout(row.raw_output)
        locations = [
            (index, element)
            for index, element in enumerate(layout)
            if str(element.get("category", "")).casefold() == "table"
            and isinstance(element.get("text"), str)
            and element["text"].strip() in page_tables
        ]
        # Reconcile in source order, not by HTML value: identical tables may coexist.
        if [element["text"].strip() for _, element in locations] != page_tables:
            raise ValueError(f"ambiguous raw layout table order: {row.image_id}")
        for table_index, (html, (layout_index, element)) in enumerate(
            zip(page_tables, locations, strict=True)
        ):
            table_id = f"{entry.document_id}-page-{entry.page_number}-table-{table_index}"
            tables.append(
                DocumentTablePrediction(
                    document_id=entry.document_id,
                    table_id=table_id,
                    html=html,
                    source_pages=[entry.page_number],
                )
            )
            evidence.append(
                {
                    "document_id": entry.document_id,
                    "table_id": table_id,
                    "image_id": entry.image_id,
                    "page_number": entry.page_number,
                    "layout_element_index": layout_index,
                    "bbox_as_provided": element.get("bbox"),
                    "raw_output_sha256": hashlib.sha256(row.raw_output.encode("utf-8")).hexdigest(),
                }
            )
    counts["document_tables"] = len(tables)
    counts["documents_in_manifest"] = len({entry.unit_id for entry in manifest})
    return (
        status_rows,
        tables,
        evidence,
        {
            "coverage": {**coverage.model_dump(), "is_complete": coverage.is_complete},
            "counts": dict(sorted(counts.items())),
            "mode": "no_merge",
        },
    )
