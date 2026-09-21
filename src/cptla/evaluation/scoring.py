from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Literal

from grits import GritsEvaluator, html_to_cell_list

from cptla.evaluation.contracts import CoverageReport, PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry


class IncompleteCoverageError(ValueError):
    """Raised when a run claims complete scope without exact image coverage."""


def load_truth_directory(
    truth_dir: Path, collection: Literal["cropped_tables", "full_documents"]
) -> dict[str, list[str]]:
    if not truth_dir.is_dir():
        raise NotADirectoryError(truth_dir)
    truth: dict[str, list[str]] = {}
    pattern = "*_tables.json" if collection == "full_documents" else "*.json"
    for path in sorted(truth_dir.glob(pattern), key=lambda item: item.name):
        value = json.loads(path.read_text(encoding="utf-8"))
        if collection == "full_documents":
            if not isinstance(value, list):
                raise ValueError(f"expected a table list in {path}")
            unit_id = path.name.removesuffix("_tables.json")
            truth[unit_id] = [_require_html(table, path) for table in value]
            continue

        tables = value if isinstance(value, list) else [value]
        if not all(isinstance(table, dict) for table in tables):
            raise ValueError(f"expected table objects in {path}")
        for table in tables:
            explicit_id = table.get("id") or table.get("table_id")
            if explicit_id is None:
                if len(tables) != 1:
                    raise ValueError(f"multiple cropped tables without explicit IDs in {path}")
                unit_id = path.stem.removesuffix("_tables")
            else:
                unit_id = str(explicit_id)
            if unit_id in truth:
                raise ValueError(f"duplicate truth table ID: {unit_id}")
            truth[unit_id] = [_require_html(table, path)]
    return truth


def _require_html(table: object, path: Path) -> str:
    if not isinstance(table, dict) or not isinstance(table.get("html"), str):
        raise ValueError(f"table without HTML in {path}")
    return table["html"]


def score_predictions(
    manifest: list[ImageManifestEntry],
    predictions: list[PredictionRecord],
    truth_by_unit: dict[str, list[str]],
    *,
    require_complete: bool,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    coverage = CoverageReport.from_ids(
        [entry.image_id for entry in manifest],
        [record.image_id for record in predictions],
    )
    if require_complete and not coverage.is_complete:
        raise IncompleteCoverageError(
            "full validation requires exact image coverage: "
            f"missing={len(coverage.missing)}, extra={len(coverage.extra)}, "
            f"duplicates={len(coverage.duplicates)}"
        )

    manifest_by_image = {entry.image_id: entry for entry in manifest}
    predictions_by_unit: dict[str, list[str]] = defaultdict(list)
    failures: list[dict[str, object]] = []
    invalid_table_html = 0
    inference_errors = 0

    for record in predictions:
        expected_entry = manifest_by_image.get(record.image_id)
        if expected_entry is not None and expected_entry.unit_id != record.unit_id:
            raise ValueError(
                f"unit_id mismatch for {record.image_id}: "
                f"manifest={expected_entry.unit_id}, prediction={record.unit_id}"
            )
        if record.status == "error":
            inference_errors += 1
            failures.append(
                {
                    "image_id": record.image_id,
                    "unit_id": record.unit_id,
                    "reason": "inference_error",
                    "error": record.error,
                }
            )
            continue
        for table_index, html in enumerate(record.tables_html):
            try:
                cells = html_to_cell_list(html)
                if cells is None:
                    raise ValueError("HTML could not be converted to cells")
            except (TypeError, ValueError) as error:
                invalid_table_html += 1
                failures.append(
                    {
                        "image_id": record.image_id,
                        "unit_id": record.unit_id,
                        "table_index": table_index,
                        "reason": "invalid_table_html",
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
                continue
            predictions_by_unit[record.unit_id].append(html)

    for unit_id, htmls in truth_by_unit.items():
        for html in htmls:
            try:
                cells = html_to_cell_list(html)
                if cells is None:
                    raise ValueError("HTML could not be converted to cells")
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid truth HTML for {unit_id}: {error}") from error

    manifest_units = {entry.unit_id for entry in manifest}
    units = sorted(manifest_units | truth_by_unit.keys() | predictions_by_unit.keys())
    evaluator = GritsEvaluator(metrics=["top", "con"])
    for unit_id in units:
        evaluator.eval_htmls(
            truth_by_unit.get(unit_id, []),
            predictions_by_unit.get(unit_id, []),
        )
    if sum(len(htmls) for htmls in truth_by_unit.values()) == 0:
        raw_metrics = {
            f"grits_{metric}{suffix}": 0.0
            for metric in ("top", "con")
            for suffix in (
                "",
                "_precision",
                "_recall",
                "_cell_exact_match_accuracy",
                "_grid_exact_match_accuracy",
            )
        }
    else:
        raw_metrics = evaluator.compute_grits()
    metrics: dict[str, object] = {
        "scope": "full_validation" if require_complete else "partial",
        "units_scored": len(units),
        "coverage": {**coverage.model_dump(), "is_complete": coverage.is_complete},
        "predicted_tables": sum(len(value) for value in predictions_by_unit.values()),
        "invalid_table_html": invalid_table_html,
        "inference_errors": inference_errors,
        "Acc-Top": raw_metrics.get("grits_top_grid_exact_match_accuracy"),
        "Acc-Con": raw_metrics.get("grits_con_grid_exact_match_accuracy"),
        "GriTS-Top": raw_metrics.get("grits_top"),
        "GriTS-Con": raw_metrics.get("grits_con"),
        "grits": raw_metrics,
    }
    return metrics, failures
