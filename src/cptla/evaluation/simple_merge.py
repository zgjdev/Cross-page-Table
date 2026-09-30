"""Conservative, provenance-preserving repeated-header cross-page baseline."""

from __future__ import annotations

import copy
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any

from grits import html_to_cell_list

from cptla.evaluation.contracts import CoverageReport, PredictionRecord
from cptla.evaluation.cross_page import DocumentTablePrediction
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import IncompleteCoverageError


def _table_tree(html: str) -> tuple[ET.Element, ET.Element, list[ET.Element], int] | None:
    try:
        root = ET.fromstring(html)
        table = root if root.tag == "table" else root.find(".//table")
        cells = html_to_cell_list(html)
        if table is None or not cells:
            return None
        rows = list(table.iter("tr"))
        width = max(max(cell.column_nums) for cell in cells) + 1
        if not rows or width < 1 or any(max(cell.row_nums) >= len(rows) for cell in cells):
            return None
        return root, table, rows, width
    except (ET.ParseError, TypeError, ValueError, OverflowError):
        return None


def _first_header(rows: list[ET.Element], table: ET.Element) -> tuple[str, ...] | None:
    header = table.find("thead")
    first = rows[0]
    if header is None or first not in list(header.iter("tr")):
        if not list(first) or not all(cell.tag == "th" for cell in first):
            return None
    texts = tuple(" ".join("".join(cell.itertext()).split()).casefold() for cell in first)
    return texts if texts and all(texts) else None


def _bbox(value: object, width: int, height: int) -> tuple[float, float, float, float] | None:
    if not isinstance(value, list) or len(value) != 4 or width <= 0 or height <= 0:
        return None
    if not all(type(number) in (float, int) and math.isfinite(number) for number in value):
        return None
    x0, y0, x1, y1 = (float(number) for number in value)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        return None
    return x0, y0, x1, y1


def _append_without_header(left: str, right: str) -> str | None:
    first = _table_tree(left)
    second = _table_tree(right)
    if first is None or second is None:
        return None
    root, table, rows, cols = first
    _, next_table, next_rows, next_cols = second
    if cols != next_cols or _first_header(rows, table) != _first_header(next_rows, next_table):
        return None
    if _first_header(rows, table) is None or len(next_rows) < 2:
        return None
    body = table.find("tbody")
    if body is None:
        body = ET.SubElement(table, "tbody")
    for row in next_rows[1:]:
        body.append(copy.deepcopy(row))
    result = ET.tostring(root, encoding="unicode")
    return result if _table_tree(result) is not None else None


def merge_repeated_header_pages(
    manifest: list[ImageManifestEntry],
    page_results: list[PredictionRecord],
    tables: list[DocumentTablePrediction],
    evidence: list[dict[str, Any]],
    image_sizes: dict[str, tuple[int, int]],
) -> tuple[list[DocumentTablePrediction], list[dict[str, Any]], dict[str, Any]]:
    """Merge only adjacent boundary tables with equal columns and exact repeated headers.

    Fixed geometry gates: the last table must reach the final 20% of its page,
    and the first table must start within the first 25% of the next page.
    These are preset baseline constants, not validation-tuned thresholds.
    """
    coverage = CoverageReport.from_ids(
        [item.image_id for item in manifest], [row.image_id for row in page_results]
    )
    if not coverage.is_complete or any(row.tables_html for row in page_results):
        raise IncompleteCoverageError("merge requires complete status-only page results")
    by_page: dict[tuple[str, int], list[DocumentTablePrediction]] = defaultdict(list)
    indexed_images = {(entry.document_id, entry.page_number): entry for entry in manifest}
    if len(indexed_images) != len(manifest) or any(key[1] is None for key in indexed_images):
        raise ValueError("duplicate/missing document page in manifest")
    if {entry.image_id for entry in manifest} != set(image_sizes):
        raise ValueError("image sizes must cover the exact manifest")
    status = {row.image_id: row for row in page_results}
    if any(
        row.unit_id != entry.document_id for entry in manifest for row in (status[entry.image_id],)
    ):
        raise ValueError("page status document mismatch")
    table_ids = {(row.document_id, row.table_id) for row in tables}
    if len(table_ids) != len(tables):
        raise ValueError("duplicate table ID")
    geometry = {(row["document_id"], row["table_id"]): row for row in evidence}
    if len(geometry) != len(evidence) or table_ids != set(geometry):
        raise ValueError("table evidence must cover each table exactly once")
    for row in tables:
        if (
            len(row.source_pages) != 1
            or (row.document_id, row.source_pages[0]) not in indexed_images
        ):
            raise ValueError("simple merge requires unmerged single-page source tables")
        source = indexed_images[row.document_id, row.source_pages[0]]
        proof = geometry[row.document_id, row.table_id]
        if proof["image_id"] != source.image_id or proof["page_number"] != row.source_pages[0]:
            raise ValueError("table evidence page mismatch")
        by_page[row.document_id, row.source_pages[0]].append(row)

    decisions: list[dict[str, Any]] = []
    successor: dict[tuple[str, str], tuple[str, str]] = {}
    predecessor: set[tuple[str, str]] = set()
    for document_id, page in sorted(indexed_images):
        next_key = document_id, page + 1
        if (
            next_key not in indexed_images
            or not by_page[document_id, page]
            or not by_page[next_key]
        ):
            continue
        left_page = indexed_images[document_id, page]
        right_page = indexed_images[next_key]
        left_rows = by_page[document_id, page]
        right_rows = by_page[next_key]
        # If geometry is missing or tied, do not guess which is the boundary table.
        left_bbox = {
            row.table_id: _bbox(
                geometry[document_id, row.table_id].get("bbox_as_provided"),
                *image_sizes[left_page.image_id],
            )
            for row in left_rows
        }
        right_bbox = {
            row.table_id: _bbox(
                geometry[document_id, row.table_id].get("bbox_as_provided"),
                *image_sizes[right_page.image_id],
            )
            for row in right_rows
        }
        if any(box is None for box in (*left_bbox.values(), *right_bbox.values())):
            decisions.append(
                {
                    "document_id": document_id,
                    "page_before": page,
                    "page_after": page + 1,
                    "left_table_id": None,
                    "right_table_id": None,
                    "reason": "missing_or_invalid_bbox",
                }
            )
            continue
        left = max(left_rows, key=lambda row: left_bbox[row.table_id][3])
        right = min(right_rows, key=lambda row: right_bbox[row.table_id][1])
        reason = "accepted"
        if status[left_page.image_id].status != "ok" or status[right_page.image_id].status != "ok":
            reason = "inference_error"
        elif (
            sum(left_bbox[row.table_id][3] == left_bbox[left.table_id][3] for row in left_rows) != 1
        ):
            reason = "ambiguous_last_table"
        elif (
            sum(right_bbox[row.table_id][1] == right_bbox[right.table_id][1] for row in right_rows)
            != 1
        ):
            reason = "ambiguous_first_table"
        elif left_bbox[left.table_id][3] < 0.8 * image_sizes[left_page.image_id][1]:
            reason = "not_at_page_bottom"
        elif right_bbox[right.table_id][1] > 0.25 * image_sizes[right_page.image_id][1]:
            reason = "not_at_page_top"
        elif _append_without_header(left.html, right.html) is None:
            reason = "column_header_or_html_mismatch"
        decisions.append(
            {
                "document_id": document_id,
                "page_before": page,
                "page_after": page + 1,
                "left_table_id": left.table_id,
                "right_table_id": right.table_id,
                "reason": reason,
            }
        )
        if reason == "accepted":
            successor[document_id, left.table_id] = document_id, right.table_id
            predecessor.add((document_id, right.table_id))

    table_by_key = {(row.document_id, row.table_id): row for row in tables}
    merged: list[DocumentTablePrediction] = []
    for key in sorted(table_by_key):
        if key in predecessor:
            continue
        chain = [key]
        while chain[-1] in successor:
            chain.append(successor[chain[-1]])
        html = table_by_key[chain[0]].html
        pages = []
        for item in chain:
            pages.extend(table_by_key[item].source_pages)
        for item in chain[1:]:
            updated = _append_without_header(html, table_by_key[item].html)
            if updated is None:
                raise ValueError(f"cannot serialize accepted merge chain: {chain}")
            html = updated
        merged.append(
            DocumentTablePrediction(
                document_id=key[0], table_id=key[1], html=html, source_pages=pages
            )
        )
    return (
        merged,
        decisions,
        {
            "mode": "simple_merge_repeated_header",
            "input_tables": len(tables),
            "output_tables": len(merged),
            "accepted_boundaries": len(successor),
            "candidate_boundaries": len(decisions),
            "geometry_gate": {"last_y2_fraction_min": 0.8, "first_y1_fraction_max": 0.25},
        },
    )
