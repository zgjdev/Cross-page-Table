import json
import sys
import types
from pathlib import Path

import pytest

# pylcs has no Windows wheel. This test-only module exercises the pinned GriTS code with
# the same LCS contract; formal Linux evaluation installs the official pylcs dependency.
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

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import (
    IncompleteCoverageError,
    load_truth_directory,
    score_predictions,
)

HTML_A = "<table><tr><td>A</td><td>B</td></tr></table>"
HTML_B = "<table><tr><td>C</td></tr></table>"


def _entry(image_id: str, unit_id: str) -> ImageManifestEntry:
    return ImageManifestEntry(
        image_id=image_id,
        relative_path=image_id,
        unit_id=unit_id,
        document_id=unit_id,
        page_number=0,
    )


def _prediction(image_id: str, unit_id: str, tables: list[str]) -> PredictionRecord:
    return PredictionRecord(
        image_id=image_id,
        unit_id=unit_id,
        status="ok",
        tables_html=tables,
        elapsed_sec=1,
    )


def test_perfect_prediction_has_perfect_metrics() -> None:
    metrics, failures = score_predictions(
        [_entry("PMC1_page_0.jpg", "PMC1")],
        [_prediction("PMC1_page_0.jpg", "PMC1", [HTML_A])],
        {"PMC1": [HTML_A]},
        require_complete=True,
    )

    assert metrics["coverage"]["is_complete"] is True
    assert metrics["GriTS-Top"] == pytest.approx(1)
    assert metrics["GriTS-Con"] == pytest.approx(1)
    assert metrics["Acc-Top"] == pytest.approx(1)
    assert metrics["Acc-Con"] == pytest.approx(1)
    assert failures == []


def test_empty_prediction_counts_as_false_negative() -> None:
    metrics, _ = score_predictions(
        [_entry("PMC1_page_0.jpg", "PMC1")],
        [_prediction("PMC1_page_0.jpg", "PMC1", [])],
        {"PMC1": [HTML_A]},
        require_complete=True,
    )

    assert metrics["GriTS-Top"] == 0
    assert metrics["GriTS-Con"] == 0


def test_table_on_empty_truth_unit_counts_as_false_positive() -> None:
    metrics, _ = score_predictions(
        [_entry("PMC2_page_0.jpg", "PMC2")],
        [_prediction("PMC2_page_0.jpg", "PMC2", [HTML_A])],
        {"PMC2": []},
        require_complete=True,
    )

    assert metrics["GriTS-Top"] == 0
    assert metrics["GriTS-Con"] == 0


def test_multiple_tables_use_order_independent_matching() -> None:
    metrics, _ = score_predictions(
        [_entry("PMC1_page_0.jpg", "PMC1")],
        [_prediction("PMC1_page_0.jpg", "PMC1", [HTML_B, HTML_A])],
        {"PMC1": [HTML_A, HTML_B]},
        require_complete=True,
    )

    assert metrics["GriTS-Top"] == pytest.approx(1)
    assert metrics["GriTS-Con"] == pytest.approx(1)


def test_truth_outside_manifest_is_not_part_of_smoke_scope() -> None:
    metrics, _ = score_predictions(
        [_entry("a.jpg", "a")],
        [_prediction("a.jpg", "a", [HTML_A])],
        {"a": [HTML_A], "b": [HTML_B]},
        require_complete=True,
    )

    assert metrics["units_scored"] == 1
    assert metrics["GriTS-Top"] == pytest.approx(1)


def test_manifest_unit_requires_truth_entry() -> None:
    with pytest.raises(ValueError, match="missing truth"):
        score_predictions(
            [_entry("a.jpg", "a")],
            [_prediction("a.jpg", "a", [])],
            {"b": [HTML_B]},
            require_complete=True,
        )


@pytest.mark.parametrize(
    "manifest,predictions",
    [
        ([_entry("a.jpg", "a"), _entry("b.jpg", "b")], [_prediction("a.jpg", "a", [])]),
        ([_entry("a.jpg", "a")], [_prediction("a.jpg", "a", []), _prediction("x.jpg", "x", [])]),
        ([_entry("a.jpg", "a")], [_prediction("a.jpg", "a", []), _prediction("a.jpg", "a", [])]),
    ],
    ids=["missing", "extra", "duplicate"],
)
def test_complete_scope_rejects_coverage_errors(
    manifest: list[ImageManifestEntry], predictions: list[PredictionRecord]
) -> None:
    with pytest.raises(IncompleteCoverageError):
        score_predictions(manifest, predictions, {}, require_complete=True)


def test_partial_scope_scores_missing_input_as_empty_prediction() -> None:
    metrics, _ = score_predictions(
        [_entry("a.jpg", "a")],
        [],
        {"a": [HTML_A]},
        require_complete=False,
    )

    assert metrics["scope"] == "partial"
    assert metrics["coverage"]["missing"] == ["a.jpg"]
    assert metrics["GriTS-Con"] == 0


def test_invalid_prediction_html_is_indexed_and_scored_as_missing() -> None:
    metrics, failures = score_predictions(
        [_entry("a.jpg", "a")],
        [_prediction("a.jpg", "a", ["<table><tr><td>broken"])],
        {"a": [HTML_A]},
        require_complete=True,
    )

    assert metrics["invalid_table_html"] == 1
    assert metrics["GriTS-Con"] == 0
    assert failures[0]["reason"] == "invalid_table_html"


def test_fixture_result_is_byte_deterministic() -> None:
    truth = json.loads(
        Path("tests/fixtures/evaluation/truth.json").read_text(encoding="utf-8")
    )
    args = (
        [_entry("PMC1_page_0.jpg", "PMC1"), _entry("PMC2_page_0.jpg", "PMC2")],
        [
            _prediction("PMC1_page_0.jpg", "PMC1", [HTML_A]),
            _prediction("PMC2_page_0.jpg", "PMC2", []),
        ],
        truth,
    )

    first = score_predictions(*args, require_complete=True)
    second = score_predictions(*args, require_complete=True)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_load_full_document_truth_groups_tables_by_document(tmp_path: Path) -> None:
    (tmp_path / "PMC1_tables.json").write_text(
        json.dumps([{"html": HTML_A}, {"html": HTML_B}]), encoding="utf-8"
    )

    assert load_truth_directory(tmp_path, "full_documents") == {"PMC1": [HTML_A, HTML_B]}


def test_load_cropped_truth_supports_one_table_file_and_explicit_ids(tmp_path: Path) -> None:
    (tmp_path / "PMC1_table_0.json").write_text(json.dumps({"html": HTML_A}), encoding="utf-8")
    (tmp_path / "tables.json").write_text(
        json.dumps([{"id": "PMC2_table_0", "html": HTML_B}]), encoding="utf-8"
    )

    assert load_truth_directory(tmp_path, "cropped_tables") == {
        "PMC1_table_0": [HTML_A],
        "PMC2_table_0": [HTML_B],
    }
