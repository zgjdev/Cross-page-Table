from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry

Postprocessor = Callable[
    [list[list[float]], list[int], list[float], list[dict[str, object]], dict[str, float]],
    list[dict[str, object]],
]

STRUCTURE_CLASS_NAMES = [
    "table",
    "table column",
    "table row",
    "table column header",
    "table projected row header",
    "table spanning cell",
    "no object",
]


def normalize_tatr_processor_size(size: dict[str, int]) -> dict[str, int]:
    """Adapt the legacy max-longest-edge config without changing its resize semantics."""
    normalized = dict(size)
    if set(normalized) == {"longest_edge"}:
        longest_edge = normalized["longest_edge"]
        if not isinstance(longest_edge, int) or longest_edge <= 0:
            raise ValueError(f"invalid TATR longest_edge: {longest_edge}")
        normalized["shortest_edge"] = longest_edge
    return normalized


def load_pdf_words(path: Path) -> list[dict[str, object]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("words")
    if not isinstance(value, list) or not all(isinstance(word, dict) for word in value):
        raise ValueError(f"expected a word list in {path}")
    return value


def normalize_words_to_image(
    words: list[dict[str, object]], image_size: tuple[int, int], *, overflow_tolerance: float = 1
) -> list[dict[str, object]]:
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid image size: {image_size}")

    normalized: list[dict[str, object]] = []
    for index, word in enumerate(words):
        bbox = word.get("bbox")
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bbox)
        ):
            raise ValueError(f"invalid word bbox at index {index}: {bbox}")
        x0, y0, x1, y1 = (float(value) for value in bbox)
        if x0 > x1 or y0 > y1:
            raise ValueError(f"inverted word bbox at index {index}: {bbox}")
        if (
            x0 < -overflow_tolerance
            or y0 < -overflow_tolerance
            or x1 > width + overflow_tolerance
            or y1 > height + overflow_tolerance
        ):
            raise ValueError(f"word bbox outside image at index {index}: {bbox}")
        item = dict(word)
        item["bbox"] = [
            min(max(x0, 0.0), float(width)),
            min(max(y0, 0.0), float(height)),
            min(max(x1, 0.0), float(width)),
            min(max(y1, 0.0), float(height)),
        ]
        item.setdefault("block_num", 0)
        item.setdefault("line_num", 0)
        item.setdefault("span_num", index)
        normalized.append(item)
    return normalized


def associated_cropped_paths(
    entry: ImageManifestEntry, words_dir: Path, truth_dir: Path
) -> tuple[Path, Path]:
    words_path = words_dir / f"{entry.unit_id}_words.json"
    truth_path = truth_dir / f"{entry.unit_id}.json"
    if not words_path.is_file():
        raise FileNotFoundError(f"missing words for {entry.unit_id}: {words_path}")
    if not truth_path.is_file():
        raise FileNotFoundError(f"missing truth for {entry.unit_id}: {truth_path}")
    return words_path, truth_path


def make_official_postprocessor(module: Any) -> Postprocessor:
    def postprocess(
        boxes: list[list[float]],
        labels: list[int],
        scores: list[float],
        words: list[dict[str, object]],
        thresholds: dict[str, float],
    ) -> list[dict[str, object]]:
        filtered_boxes, filtered_scores, filtered_labels = module.apply_class_thresholds(
            boxes,
            labels,
            scores,
            STRUCTURE_CLASS_NAMES,
            thresholds,
        )
        objects = [
            {"bbox": bbox, "score": score, "label": label}
            for bbox, score, label in zip(
                filtered_boxes, filtered_scores, filtered_labels, strict=True
            )
        ]
        table_objects = [item for item in objects if item["label"] == 0]
        if table_objects:
            table_bbox = max(table_objects, key=lambda item: item["score"])["bbox"]
        else:
            table_bbox = [0, 0, 1000, 1000]
        words_in_table = [word for word in words if module.iob(word["bbox"], table_bbox) >= 0.5]
        table = {"objects": objects, "page_num": 0, "bbox": table_bbox}
        _, cells, _ = module.objects_to_cells(
            table,
            objects,
            words_in_table,
            STRUCTURE_CLASS_NAMES,
            thresholds,
        )
        return cells

    return postprocess


def cells_to_html(cells: list[dict[str, object]]) -> str:
    ordered = sorted(cells, key=lambda cell: min(cell["column_nums"]))  # type: ignore[arg-type]
    ordered = sorted(ordered, key=lambda cell: min(cell["row_nums"]))  # type: ignore[arg-type]
    table = ET.Element("table")
    rows: dict[int, list[dict[str, object]]] = {}
    for cell in ordered:
        row_nums = cell["row_nums"]
        column_nums = cell["column_nums"]
        if not isinstance(row_nums, list) or not isinstance(column_nums, list):
            raise ValueError("cell row_nums and column_nums must be lists")
        rows.setdefault(min(row_nums), []).append(cell)

    sections: dict[bool, ET.Element] = {}
    for row_cells in rows.values():
        is_header = bool(
            row_cells[0].get("header", row_cells[0].get("column header", False))
        )
        if is_header not in sections:
            sections[is_header] = ET.SubElement(table, "thead" if is_header else "tbody")
        row = ET.SubElement(sections[is_header], "tr")
        for cell in row_cells:
            row_nums = cell["row_nums"]
            column_nums = cell["column_nums"]
            if not isinstance(row_nums, list) or not isinstance(column_nums, list):
                raise ValueError("cell row_nums and column_nums must be lists")
            attributes: dict[str, str] = {}
            if len(column_nums) > 1:
                attributes["colspan"] = str(len(column_nums))
            if len(row_nums) > 1:
                attributes["rowspan"] = str(len(row_nums))
            table_cell = ET.SubElement(row, "th" if is_header else "td", attrib=attributes)
            table_cell.text = str(cell.get("cell_text", cell.get("cell text", "")))
    return ET.tostring(table, encoding="unicode", short_empty_elements=False)


def tatr_objects_to_prediction(
    *,
    image_id: str,
    unit_id: str,
    boxes: list[list[float]],
    labels: list[int],
    scores: list[float],
    words: list[dict[str, object]],
    thresholds: dict[str, float],
    postprocessor: Postprocessor,
    elapsed_sec: float,
) -> PredictionRecord:
    if not (len(boxes) == len(labels) == len(scores)):
        raise ValueError("TATR boxes, labels, and scores must have equal lengths")
    cells = postprocessor(boxes, labels, scores, words, thresholds)
    html = cells_to_html(cells)
    return PredictionRecord(
        image_id=image_id,
        unit_id=unit_id,
        status="ok",
        tables_html=[html] if cells else [],
        elapsed_sec=elapsed_sec,
        raw_output=json.dumps(
            {"boxes": boxes, "labels": labels, "scores": scores, "cells": cells},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        warnings=[] if cells else ["no_valid_cells"],
    )
