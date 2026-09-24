import json
import sys
import types
from pathlib import Path

import pytest

try:
    import pylcs  # noqa: F401
except ImportError:
    pylcs_stub = types.ModuleType("pylcs")
    pylcs_stub.lcs_sequence_length = lambda left, right: 0
    sys.modules["pylcs"] = pylcs_stub

from cptla.evaluation.case_analysis import CaseDiagnostic, TableProfile
from cptla.evaluation.case_report import render_comparison_table, write_case_report
from cptla.evaluation.contracts import PredictionRecord


def _profile() -> TableProfile:
    return TableProfile(
        row_count=1,
        column_count=1,
        cell_count=1,
        header_row_count=0,
        header_cell_count=0,
        rowspan_cells=0,
        colspan_cells=0,
        spanning_cells=0,
    )


def _case() -> CaseDiagnostic:
    return CaseDiagnostic(
        image_id="x.jpg",
        unit_id="x",
        relative_path="nested/x.jpg",
        status="ok",
        prediction_table_count=1,
        grits_top=0.75,
        grits_con=0.5,
        acc_top=False,
        acc_con=False,
        score_stratum="medium",
        truth_profile=_profile(),
        prediction_profile=_profile(),
        error_tags=["text_mismatch"],
        complexity_tags=["long"],
    )


def _write_report(output: Path, *, cell_text: str = "A") -> Path:
    images = output.parent / "images"
    (images / "nested").mkdir(parents=True, exist_ok=True)
    (images / "nested" / "x.jpg").write_bytes(b"fake-jpeg")
    truth = f"<table><tr><td>{cell_text}</td></tr></table>"
    prediction = PredictionRecord(
        image_id="x.jpg",
        unit_id="x",
        status="ok",
        tables_html=["<table><tr><td>B</td></tr></table>"],
        elapsed_sec=1,
    )
    case = _case()
    return write_case_report(
        output,
        all_cases=[case],
        selected_cases=[case],
        records_by_id={"x": prediction},
        truth_by_id={"x": truth},
        images_dir=images,
        metadata={"run_id": "test-run", "row_p90": 10, "column_p90": 8},
    )


def test_rendered_report_escapes_scripts_and_contains_three_views(tmp_path: Path) -> None:
    malicious = "&lt;script&gt;alert(1)&lt;/script&gt;"
    index = _write_report(tmp_path / "report", cell_text=malicious)
    html = index.read_text(encoding="utf-8")

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'data-view="source-image"' in html
    assert 'data-view="ground-truth"' in html
    assert 'data-view="prediction"' in html


def test_comparison_table_marks_text_and_structure_differences() -> None:
    truth = "<table><tr><td colspan='2'>A</td></tr></table>"
    text_difference = "<table><tr><td colspan='2'>B</td></tr></table>"
    structure_difference = "<table><tr><td>A</td><td></td></tr></table>"

    assert "cell-text-diff" in render_comparison_table(truth, text_difference, side="truth")
    assert "cell-structure-diff" in render_comparison_table(
        truth, structure_difference, side="truth"
    )


def test_report_is_portable_and_refuses_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "report"
    index = _write_report(output)

    payload = json.loads((output / "cases.json").read_text(encoding="utf-8"))
    assert payload["selected_ids"] == ["x"]
    assert len(payload["cases"]) == 1
    assert (output / "assets" / "images" / "x.jpg").read_bytes() == b"fake-jpeg"
    assert "assets/images/x.jpg" in index.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_report(output)


def test_report_contains_filter_metadata_and_scientific_caveat(tmp_path: Path) -> None:
    html = _write_report(tmp_path / "report").read_text(encoding="utf-8")

    assert 'data-score-stratum="medium"' in html
    assert 'data-error-tags="text_mismatch"' in html
    assert 'data-complexity-tags="long"' in html
    assert "诊断线索" in html
    assert "不能替代人工核验" in html
