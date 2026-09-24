import sys
import types

import pytest

try:
    import pylcs  # noqa: F401
except ImportError:
    pylcs_stub = types.ModuleType("pylcs")

    def lcs_sequence_length(left: str, right: str) -> int:
        previous = [0] * (len(right) + 1)
        for left_character in left:
            current = [0]
            for index, right_character in enumerate(right, start=1):
                if left_character == right_character:
                    current.append(previous[index - 1] + 1)
                else:
                    current.append(max(previous[index], current[-1]))
            previous = current
        return previous[-1]

    pylcs_stub.lcs_sequence_length = lcs_sequence_length
    sys.modules["pylcs"] = pylcs_stub

from cptla.evaluation.case_analysis import (
    CaseDiagnostic,
    TableProfile,
    add_complexity_tags,
    analyze_cropped_case,
    stratified_sample,
)
from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry


def _entry(identifier: str) -> ImageManifestEntry:
    return ImageManifestEntry(
        image_id=f"{identifier}.jpg",
        relative_path=f"{identifier}.jpg",
        unit_id=identifier,
        document_id="PMC1",
    )


def _prediction(identifier: str, html: str | None, *, error: bool = False) -> PredictionRecord:
    return PredictionRecord(
        image_id=f"{identifier}.jpg",
        unit_id=identifier,
        status="error" if error else "ok",
        tables_html=[] if html is None else [html],
        elapsed_sec=1,
        error="failure" if error else None,
    )


def test_analyze_case_separates_span_header_and_text_mismatch() -> None:
    truth = (
        "<table><thead><tr><th colspan='2'>H</th></tr></thead>"
        "<tbody><tr><td>A</td><td>B</td></tr></tbody></table>"
    )
    pred = (
        "<table><thead><tr><th>H</th><th></th></tr></thead>"
        "<tbody><tr><td>A</td><td>X</td></tr></tbody></table>"
    )

    case = analyze_cropped_case(_entry("x"), _prediction("x", pred), truth)

    assert case.truth_profile.column_count == 2
    assert case.truth_profile.header_row_count == 1
    assert {"span_mismatch", "text_mismatch"} <= set(case.error_tags)
    assert case.grits_top < 1
    assert case.grits_con < 1


def test_error_prediction_is_preserved_as_zero_score() -> None:
    truth = "<table><tr><td>A</td></tr></table>"

    case = analyze_cropped_case(_entry("x"), _prediction("x", None, error=True), truth)

    assert case.grits_top == 0
    assert case.grits_con == 0
    assert case.score_stratum == "zero_or_empty"
    assert case.error_tags == ["inference_error", "empty_prediction"]


def _profile(rows: int, columns: int, *, header_rows: int = 1, spans: int = 0) -> TableProfile:
    return TableProfile(
        row_count=rows,
        column_count=columns,
        cell_count=rows * columns,
        header_row_count=header_rows,
        header_cell_count=columns * header_rows,
        rowspan_cells=spans,
        colspan_cells=spans,
        spanning_cells=spans,
    )


def _case(index: int) -> CaseDiagnostic:
    score = [1.0, 0.95, 0.75, 0.3, 0.0][index % 5]
    return CaseDiagnostic(
        image_id=f"case-{index}.jpg",
        unit_id=f"case-{index}",
        relative_path=f"case-{index}.jpg",
        status="ok",
        prediction_table_count=0 if score == 0 else 1,
        grits_top=score,
        grits_con=score,
        acc_top=score == 1,
        acc_con=score == 1,
        score_stratum=(
            "exact"
            if score == 1
            else "high_non_exact"
            if score >= 0.9
            else "medium"
            if score >= 0.6
            else "low"
            if score > 0
            else "zero_or_empty"
        ),
        truth_profile=_profile(index + 1, (index % 11) + 1, spans=index % 3),
        prediction_profile=None if score == 0 else _profile(index + 1, (index % 11) + 1),
        error_tags=["empty_prediction"] if score == 0 else ["text_mismatch"],
    )


def test_complexity_tags_use_population_quantiles_and_structure() -> None:
    cases = [_case(index) for index in range(20)]

    tagged, thresholds = add_complexity_tags(cases)

    assert thresholds.row_p90 == 18
    assert thresholds.column_p90 == 9
    assert "long" in tagged[-1].complexity_tags
    assert "spanning" in tagged[2].complexity_tags


def test_stratified_sample_is_deterministic_and_honors_includes() -> None:
    cases, _ = add_complexity_tags([_case(index) for index in range(100)])

    first = stratified_sample(cases, sample_size=20, seed=17, include_ids=["case-99"])
    second = stratified_sample(
        list(reversed(cases)), sample_size=20, seed=17, include_ids=["case-99"]
    )

    assert [item.unit_id for item in first] == [item.unit_id for item in second]
    assert len(first) == 20
    assert "case-99" in {item.unit_id for item in first}
    assert len({item.unit_id for item in first}) == 20
    assert {item.score_stratum for item in first} == {
        "exact",
        "high_non_exact",
        "medium",
        "low",
        "zero_or_empty",
    }


def test_sampling_rejects_unknown_forced_id() -> None:
    with pytest.raises(ValueError, match="unknown include_ids"):
        stratified_sample([_case(0)], sample_size=1, seed=1, include_ids=["missing"])
