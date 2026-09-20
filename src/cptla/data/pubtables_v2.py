from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_WORD_FILE_RE = re.compile(r"^(?P<document>.+)_page_(?P<page>\d+)_words\.json$")
_WORD_BBOX_CLIP_TOLERANCE = 0.05


@dataclass(frozen=True)
class NormalizationStats:
    clipped_word_boxes: int = 0


def _page_dimensions(xml_path: Path) -> tuple[int, int]:
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"{xml_path}: missing XML size element")
    width_text = size.findtext("width")
    height_text = size.findtext("height")
    if width_text is None or height_text is None:
        raise ValueError(f"{xml_path}: missing XML page dimensions")
    return int(width_text), int(height_text)


def load_document_bundle(
    input_root: Path, tables_path: Path, *, source_split: str
) -> dict[str, Any]:
    suffix = "_tables.json"
    if not tables_path.name.endswith(suffix):
        raise ValueError(f"unexpected tables filename: {tables_path.name}")
    document_id = tables_path.name[: -len(suffix)]

    pages = []
    word_paths = sorted((input_root / "words").glob(f"{document_id}_page_*_words.json"))
    if not word_paths:
        raise ValueError(f"{document_id}: no word files found")
    for word_path in word_paths:
        match = _WORD_FILE_RE.match(word_path.name)
        if match is None or match.group("document") != document_id:
            raise ValueError(f"unexpected words filename: {word_path.name}")
        page_num = int(match.group("page"))
        xml_path = input_root / "xml_annotations" / f"{document_id}_page_{page_num}.xml"
        if not xml_path.is_file():
            raise ValueError(f"{document_id}: missing XML annotation for page {page_num}")
        width, height = _page_dimensions(xml_path)
        pages.append(
            {
                "page_num": page_num,
                "width": width,
                "height": height,
                "words": json.loads(word_path.read_text(encoding="utf-8")),
            }
        )

    pages.sort(key=lambda page: page["page_num"])
    return {
        "document_id": document_id,
        "source_split": source_split,
        "pages": pages,
        "tables": json.loads(tables_path.read_text(encoding="utf-8")),
    }


def _normalized_bbox(
    bbox: Sequence[float],
    *,
    width: float,
    height: float,
    context: str,
    clip_tolerance: float = 0.0,
) -> tuple[dict[str, float], bool]:
    if len(bbox) != 4:
        raise ValueError(f"{context}: expected four bbox coordinates")
    if width <= 0 or height <= 0:
        raise ValueError(f"{context}: page dimensions must be positive")

    x0, y0, x1, y1 = (float(value) for value in bbox)
    if not (
        -width * clip_tolerance <= x0 < x1 <= width * (1 + clip_tolerance)
    ):
        raise ValueError(f"{context}: horizontal bbox coordinates are outside the page")
    if not (
        -height * clip_tolerance <= y0 < y1 <= height * (1 + clip_tolerance)
    ):
        raise ValueError(f"{context}: vertical bbox coordinates are outside the page")

    clipped = (max(0.0, x0), max(0.0, y0), min(width, x1), min(height, y1))
    was_clipped = clipped != (x0, y0, x1, y1)
    x0, y0, x1, y1 = clipped
    normalized = {
        "x0": x0 / width,
        "y0": y0 / height,
        "x1": x1 / width,
        "y1": y1 / height,
    }
    if not (0 <= normalized["x0"] < normalized["x1"] <= 1):
        raise ValueError(f"{context}: horizontal bbox coordinates are outside the page")
    if not (0 <= normalized["y0"] < normalized["y1"] <= 1):
        raise ValueError(f"{context}: vertical bbox coordinates are outside the page")
    return normalized, was_clipped


def _required_indices(cell: Mapping[str, Any], key: str, context: str) -> list[int]:
    values = cell.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{context}: {key} must be a non-empty list")
    indices = [int(value) for value in values]
    if min(indices) < 0:
        raise ValueError(f"{context}: {key} cannot contain negative indices")
    return indices


def normalize_document_with_stats(
    raw: Mapping[str, Any],
) -> tuple[dict[str, Any], NormalizationStats]:
    document_id = str(raw.get("document_id", "")).strip()
    if not document_id:
        raise ValueError("document_id is required")

    raw_pages = raw.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ValueError("pages must be a non-empty list")

    pages: dict[int, Mapping[str, Any]] = {}
    words: list[dict[str, Any]] = []
    clipped_word_boxes = 0
    for raw_page in raw_pages:
        page_num = int(raw_page["page_num"])
        if page_num in pages:
            raise ValueError(f"duplicate page metadata for page {page_num}")
        pages[page_num] = raw_page
        width = float(raw_page["width"])
        height = float(raw_page["height"])
        for word_index, raw_word in enumerate(raw_page.get("words", [])):
            text = str(raw_word.get("text", ""))
            if not text:
                continue
            bbox, was_clipped = _normalized_bbox(
                raw_word["bbox"],
                width=width,
                height=height,
                context=f"page {page_num} word {word_index}",
                clip_tolerance=_WORD_BBOX_CLIP_TOLERANCE,
            )
            clipped_word_boxes += int(was_clipped)
            words.append({"page": page_num, "text": text, "bbox": bbox})

    tables: list[dict[str, Any]] = []
    raw_tables = raw.get("tables")
    if not isinstance(raw_tables, list):
        raise ValueError("tables must be a list")
    for table_index, raw_table in enumerate(raw_tables):
        table_id = f"{document_id}-table-{table_index}"
        cells = []
        for cell_index, raw_cell in enumerate(raw_table.get("cells", [])):
            context = f"table {table_index} cell {cell_index}"
            rows = _required_indices(raw_cell, "row_nums", context)
            columns = _required_indices(raw_cell, "column_nums", context)
            cells.append(
                {
                    "cell_id": f"{table_id}-cell-{cell_index}",
                    "row": min(rows),
                    "column": min(columns),
                    "row_span": max(rows) - min(rows) + 1,
                    "column_span": max(columns) - min(columns) + 1,
                    "text": str(raw_cell.get("xml_text_content", "")),
                    "is_header": bool(raw_cell.get("is_column_header", False)),
                    "word_indices": (),
                }
            )

        fragments = []
        for part_index, raw_part in enumerate(raw_table.get("parts", [])):
            page_num = int(raw_part["page_num"])
            page = pages.get(page_num)
            if page is None:
                raise ValueError(f"missing page metadata for page {page_num}")
            bbox, _ = _normalized_bbox(
                raw_part["bbox"],
                width=float(page["width"]),
                height=float(page["height"]),
                context=f"table {table_index} part {part_index}",
            )
            fragments.append(
                {
                    "fragment_id": f"{table_id}-part-{part_index}",
                    "table_id": table_id,
                    "page": page_num,
                    "bbox": bbox,
                }
            )

        tables.append({"table_id": table_id, "cells": cells, "fragments": fragments})

    return (
        {
            "document_id": document_id,
            "source_split": raw.get("source_split"),
            "journal_id": raw.get("journal_id"),
            "page_count": max(pages) + 1,
            "words": words,
            "tables": tables,
        },
        NormalizationStats(clipped_word_boxes=clipped_word_boxes),
    )


def normalize_document(raw: Mapping[str, Any]) -> dict[str, Any]:
    normalized, _ = normalize_document_with_stats(raw)
    return normalized
