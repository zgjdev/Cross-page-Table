"""Document-level matching followed by derived cross-page subset scoring."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from grits import (
    GritsEvaluator,
    cell_list_to_grid_con,
    html_to_cell_list,
    hungarian_grits_con_matching,
)
from pydantic import BaseModel, ConfigDict, Field

from cptla.evaluation.contracts import CoverageReport, PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import IncompleteCoverageError


class DocumentTablePrediction(BaseModel):
    """A final (possibly merged) table with auditable input-page provenance."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    html: str
    source_pages: list[int] = Field(min_length=1)


def score_cross_page(
    manifest: list[ImageManifestEntry],
    page_results: list[PredictionRecord],
    predicted_tables: list[DocumentTablePrediction],
    truth_by_document: dict[str, list[dict[str, Any]]],
    cross_page_gold: list[dict[str, Any]],
    *,
    require_complete: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Match against ALL truth tables with official GriTS-Con Hungarian assignment.

    Cross-page GriTS is a GT-subset diagnostic, not detection precision: unmatched
    predictions are counted separately and excluded from its cell denominator.
    """
    coverage = CoverageReport.from_ids(
        [entry.image_id for entry in manifest], [record.image_id for record in page_results]
    )
    if require_complete and not coverage.is_complete:
        raise IncompleteCoverageError(f"incomplete page coverage: {coverage.model_dump()}")
    images = {entry.image_id: entry for entry in manifest}
    if len(images) != len(manifest) or any(entry.page_number is None for entry in manifest):
        raise ValueError("expected unique full-document page manifest")
    pages: dict[str, set[int]] = defaultdict(set)
    for entry in manifest:
        if entry.document_id != entry.unit_id:
            raise ValueError(f"manifest unit/document mismatch: {entry.image_id}")
        pages[entry.document_id].add(entry.page_number)
    for record in page_results:
        entry = images.get(record.image_id)
        if entry is None:
            if require_complete:
                raise ValueError(f"unknown image: {record.image_id}")
            continue
        if record.unit_id != entry.unit_id:
            raise ValueError(f"page unit mismatch: {record.image_id}")
        if record.tables_html:
            raise ValueError("page_results are coverage only; put tables in document predictions")
    if set(truth_by_document) != set(pages):
        raise ValueError("truth document IDs must equal manifest document IDs")

    cross_ids: set[tuple[str, int]] = set()
    for row in cross_page_gold:
        doc, index = row["document_id"], row["table_index"]
        if (
            doc not in pages
            or type(index) is not int
            or not 0 <= index < len(truth_by_document[doc])
        ):
            raise ValueError(f"cross-page truth outside scope: {doc} {index}")
        table = truth_by_document[doc][index]
        distinct = sorted({part["page_num"] for part in table["parts"]})
        key = (doc, index)
        if key in cross_ids or len(distinct) < 2 or distinct != row["page_numbers"]:
            raise ValueError(f"cross-page membership mismatch/duplicate: {key}")
        if table["html"] != row["html"] or row["table_id"] != f"{doc}-table-{index}":
            raise ValueError(f"cross-page truth HTML/ID mismatch: {key}")
        cross_ids.add(key)
    derived_ids = {
        (doc, index)
        for doc, tables in truth_by_document.items()
        for index, table in enumerate(tables)
        if len({part["page_num"] for part in table["parts"]}) > 1
    }
    if derived_ids != cross_ids:
        raise ValueError("cross-page gold does not equal all derived cross-page truth tables")

    predicted: dict[str, list[DocumentTablePrediction]] = defaultdict(list)
    seen_ids: set[tuple[str, str]] = set()
    failures: list[dict[str, Any]] = []
    for row in predicted_tables:
        key = (row.document_id, row.table_id)
        if key in seen_ids or row.document_id not in pages:
            raise ValueError(f"duplicate/out-of-scope prediction: {key}")
        seen_ids.add(key)
        if len(row.source_pages) != len(set(row.source_pages)) or any(
            type(page) is not int or page not in pages[row.document_id] for page in row.source_pages
        ):
            raise ValueError(f"invalid source pages: {key}")
        try:
            if not html_to_cell_list(row.html):
                raise ValueError("empty/unparseable table")
        except (TypeError, ValueError) as error:
            failures.append(
                {
                    "document_id": row.document_id,
                    "table_id": row.table_id,
                    "reason": "invalid_table_html",
                    "error": str(error),
                }
            )
            continue
        predicted[row.document_id].append(row)

    cross_evaluator = GritsEvaluator(metrics=["top", "con"])
    full_evaluator = GritsEvaluator(metrics=["top", "con"])
    matches: list[dict[str, Any]] = []
    diagnostics: Counter[str] = Counter()
    for doc in sorted(pages):
        truth = truth_by_document[doc]
        preds = sorted(predicted[doc], key=lambda item: item.table_id)
        truth_htmls: list[str] = []
        for index, table in enumerate(truth):
            if not isinstance(table, dict) or not isinstance(table.get("html"), str):
                raise ValueError(f"invalid truth table: {doc} {index}")
            if not html_to_cell_list(table["html"]):
                raise ValueError(f"invalid truth HTML: {doc} {index}")
            truth_htmls.append(table["html"])
        full_evaluator.eval_htmls(truth_htmls, [item.html for item in preds])
        true_grids = [cell_list_to_grid_con(html_to_cell_list(html)) for html in truth_htmls]
        pred_grids = [cell_list_to_grid_con(html_to_cell_list(row.html)) for row in preds]
        assignment = hungarian_grits_con_matching(true_grids, pred_grids)
        assigned = {
            i: j
            for position, (i, j) in enumerate(
                zip(assignment.matched_true_indices, assignment.matched_pred_indices, strict=True)
            )
            # A zero-overlap assignment must not claim a detected table.
            if float(assignment.true_grid_scores[position].sum()) > 0
        }
        consumed = set(assigned.values())
        for index, html in enumerate(truth_htmls):
            if (doc, index) not in cross_ids:
                continue
            pred = preds[assigned[index]] if index in assigned else None
            cross_evaluator.eval_htmls([html], [pred.html] if pred else [])
            source = sorted(pred.source_pages) if pred else []
            expected = sorted({part["page_num"] for part in truth[index]["parts"]})
            if pred:
                if set(source) - set(expected):
                    diagnostics["matched_cross_page_extra_source_pages"] += 1
                if set(expected) - set(source):
                    diagnostics["matched_cross_page_missing_source_pages"] += 1
            matches.append(
                {
                    "document_id": doc,
                    "truth_table_id": f"{doc}-table-{index}",
                    "predicted_table_id": pred.table_id if pred else None,
                    "truth_pages": expected,
                    "source_pages": source,
                }
            )
        for j, row in enumerate(preds):
            if j not in consumed:
                diagnostics["unmatched_predicted_tables"] += 1
                if len(row.source_pages) > 1:
                    diagnostics["unmatched_multisource_tables"] += 1
    diagnostics["invalid_table_html"] = len(failures)
    diagnostics["inference_error_pages"] = sum(row.status == "error" for row in page_results)
    cross_metrics = cross_evaluator.compute_grits() if matches else {}
    metrics = {
        "scope": "full_validation" if require_complete else "partial",
        "coverage": {**coverage.model_dump(), "is_complete": coverage.is_complete},
        "cross_page_truth_tables": len(matches),
        "cross_page_matched_tables": sum(row["predicted_table_id"] is not None for row in matches),
        "cross_page": cross_metrics,
        "full_document": full_evaluator.compute_grits(),
        "diagnostics": dict(sorted(diagnostics.items())),
        "protocol": (
            "document GriTS-Con Hungarian matching over all truth; positive-overlap pairs "
            "only; cross-page GT-subset micro GriTS (not precision)"
        ),
    }
    return metrics, matches, failures
