from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from typing import Literal

from grits import GritsEvaluator, html_to_cell_list
from pydantic import BaseModel, ConfigDict, Field

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry

ScoreStratum = Literal["exact", "high_non_exact", "medium", "low", "zero_or_empty"]


class TableProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)
    header_row_count: int = Field(ge=0)
    header_cell_count: int = Field(ge=0)
    rowspan_cells: int = Field(ge=0)
    colspan_cells: int = Field(ge=0)
    spanning_cells: int = Field(ge=0)


class ComplexityThresholds(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_p90: int = Field(ge=0)
    column_p90: int = Field(ge=0)


class CaseDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    image_id: str
    unit_id: str
    relative_path: str
    status: Literal["ok", "error"]
    prediction_table_count: int = Field(ge=0)
    grits_top: float = Field(ge=0, le=1)
    grits_con: float = Field(ge=0, le=1)
    acc_top: bool
    acc_con: bool
    score_stratum: ScoreStratum
    truth_profile: TableProfile
    prediction_profile: TableProfile | None
    error_tags: list[str] = Field(default_factory=list)
    complexity_tags: list[str] = Field(default_factory=list)


def _cells(html: str):
    cells = html_to_cell_list(html)
    if cells is None:
        raise ValueError("table HTML could not be parsed")
    return cells


def profile_html(html: str) -> TableProfile:
    cells = _cells(html)
    if not cells:
        return TableProfile(
            row_count=0,
            column_count=0,
            cell_count=0,
            header_row_count=0,
            header_cell_count=0,
            rowspan_cells=0,
            colspan_cells=0,
            spanning_cells=0,
        )
    header_rows = {row for cell in cells if cell.is_column_header for row in cell.row_nums}
    return TableProfile(
        row_count=max(max(cell.row_nums) for cell in cells) + 1,
        column_count=max(max(cell.column_nums) for cell in cells) + 1,
        cell_count=len(cells),
        header_row_count=len(header_rows),
        header_cell_count=sum(cell.is_column_header for cell in cells),
        rowspan_cells=sum(len(cell.row_nums) > 1 for cell in cells),
        colspan_cells=sum(len(cell.column_nums) > 1 for cell in cells),
        spanning_cells=sum(
            len(cell.row_nums) > 1 or len(cell.column_nums) > 1 for cell in cells
        ),
    )


CellSignature = tuple[tuple[int, ...], tuple[int, ...], str, bool]


def _cell_map(html: str) -> dict[tuple[int, int], CellSignature]:
    return {
        (min(cell.row_nums), min(cell.column_nums)): (
            tuple(cell.row_nums),
            tuple(cell.column_nums),
            " ".join(cell.cell_text.split()),
            cell.is_column_header,
        )
        for cell in _cells(html)
    }


def _score_stratum(grits_top: float, acc_top: bool, acc_con: bool) -> ScoreStratum:
    if acc_top and acc_con:
        return "exact"
    if grits_top >= 0.9:
        return "high_non_exact"
    if grits_top >= 0.6:
        return "medium"
    if grits_top > 0:
        return "low"
    return "zero_or_empty"


def _single_case_metrics(truth_html: str, predicted_htmls: list[str]) -> dict[str, float]:
    evaluator = GritsEvaluator(metrics=["top", "con"])
    evaluator.eval_htmls([truth_html], predicted_htmls)
    return evaluator.compute_grits()


def analyze_cropped_case(
    entry: ImageManifestEntry,
    prediction: PredictionRecord,
    truth_html: str,
) -> CaseDiagnostic:
    if entry.image_id != prediction.image_id or entry.unit_id != prediction.unit_id:
        raise ValueError(f"prediction identity mismatch for {entry.image_id}")

    predicted_htmls = prediction.tables_html if prediction.status == "ok" else []
    metrics = _single_case_metrics(truth_html, predicted_htmls)
    grits_top = float(metrics.get("grits_top", 0.0))
    grits_con = float(metrics.get("grits_con", 0.0))
    acc_top = metrics.get("grits_top_grid_exact_match_accuracy", 0.0) == 1.0
    acc_con = metrics.get("grits_con_grid_exact_match_accuracy", 0.0) == 1.0
    truth_profile = profile_html(truth_html)
    prediction_profile = profile_html(predicted_htmls[0]) if len(predicted_htmls) == 1 else None

    error_tags: list[str] = []
    if prediction.status == "error":
        error_tags.append("inference_error")
    if not predicted_htmls:
        error_tags.append("empty_prediction")
    elif len(predicted_htmls) != 1:
        error_tags.append("table_count_mismatch")
    else:
        assert prediction_profile is not None
        if truth_profile.row_count != prediction_profile.row_count:
            error_tags.append("row_count_mismatch")
        if truth_profile.column_count != prediction_profile.column_count:
            error_tags.append("column_count_mismatch")
        if (
            truth_profile.header_row_count != prediction_profile.header_row_count
            or truth_profile.header_cell_count != prediction_profile.header_cell_count
        ):
            error_tags.append("header_mismatch")

        truth_map = _cell_map(truth_html)
        prediction_map = _cell_map(predicted_htmls[0])
        coordinates = truth_map.keys() | prediction_map.keys()
        if any(
            coordinate not in truth_map
            or coordinate not in prediction_map
            or truth_map[coordinate][:2] != prediction_map[coordinate][:2]
            for coordinate in coordinates
        ):
            error_tags.append("span_mismatch")
        if any(
            coordinate in truth_map
            and coordinate in prediction_map
            and truth_map[coordinate][2] != prediction_map[coordinate][2]
            for coordinate in coordinates
        ):
            error_tags.append("text_mismatch")
        diagnostic_tags = {
            "row_count_mismatch",
            "column_count_mismatch",
            "header_mismatch",
            "span_mismatch",
            "text_mismatch",
        }
        if len(diagnostic_tags.intersection(error_tags)) > 1:
            error_tags.append("mixed")

    return CaseDiagnostic(
        image_id=entry.image_id,
        unit_id=entry.unit_id,
        relative_path=entry.relative_path,
        status=prediction.status,
        prediction_table_count=len(predicted_htmls),
        grits_top=grits_top,
        grits_con=grits_con,
        acc_top=acc_top,
        acc_con=acc_con,
        score_stratum=_score_stratum(grits_top, acc_top, acc_con),
        truth_profile=truth_profile,
        prediction_profile=prediction_profile,
        error_tags=error_tags,
    )


def _nearest_rank_p90(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)]


def add_complexity_tags(
    cases: list[CaseDiagnostic],
) -> tuple[list[CaseDiagnostic], ComplexityThresholds]:
    thresholds = ComplexityThresholds(
        row_p90=_nearest_rank_p90([case.truth_profile.row_count for case in cases]),
        column_p90=_nearest_rank_p90([case.truth_profile.column_count for case in cases]),
    )
    tagged: list[CaseDiagnostic] = []
    for case in cases:
        tags: list[str] = []
        if thresholds.row_p90 and case.truth_profile.row_count >= thresholds.row_p90:
            tags.append("long")
        if thresholds.column_p90 and case.truth_profile.column_count >= thresholds.column_p90:
            tags.append("wide")
        if case.truth_profile.header_row_count > 1:
            tags.append("multi_level_header")
        if case.truth_profile.spanning_cells:
            tags.append("spanning")
        tagged.append(case.model_copy(update={"complexity_tags": tags}))
    return tagged, thresholds


def _stable_order(case: CaseDiagnostic, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{case.unit_id}".encode()).hexdigest()


def _balanced_stratum(cases: list[CaseDiagnostic], seed: int) -> list[CaseDiagnostic]:
    ordered = sorted(cases, key=lambda case: _stable_order(case, seed))
    buckets: dict[str, list[CaseDiagnostic]] = defaultdict(list)
    for case in ordered:
        signature = "|".join(case.complexity_tags + case.error_tags) or "ordinary"
        buckets[signature].append(case)
    result: list[CaseDiagnostic] = []
    keys = sorted(buckets)
    while keys:
        next_keys: list[str] = []
        for key in keys:
            result.append(buckets[key].pop(0))
            if buckets[key]:
                next_keys.append(key)
        keys = next_keys
    return result


def stratified_sample(
    cases: list[CaseDiagnostic],
    *,
    sample_size: int,
    seed: int,
    include_ids: list[str] | None = None,
) -> list[CaseDiagnostic]:
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    by_id = {case.unit_id: case for case in cases}
    include_ids = list(dict.fromkeys(include_ids or []))
    unknown = sorted(set(include_ids) - by_id.keys())
    if unknown:
        raise ValueError(f"unknown include_ids: {unknown}")
    if len(include_ids) > sample_size:
        raise ValueError("include_ids exceed sample_size")

    selected = [by_id[identifier] for identifier in include_ids]
    selected_ids = set(include_ids)
    strata: dict[str, list[CaseDiagnostic]] = defaultdict(list)
    for case in cases:
        if case.unit_id not in selected_ids:
            strata[case.score_stratum].append(case)
    strata = {key: _balanced_stratum(value, seed) for key, value in strata.items()}
    stratum_order = ["exact", "high_non_exact", "medium", "low", "zero_or_empty"]
    while len(selected) < min(sample_size, len(cases)):
        made_progress = False
        for stratum in stratum_order:
            if strata.get(stratum):
                selected.append(strata[stratum].pop(0))
                made_progress = True
                if len(selected) == min(sample_size, len(cases)):
                    break
        if not made_progress:
            break
    return selected
