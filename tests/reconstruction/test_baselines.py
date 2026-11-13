from cptla.reconstruction.baselines import concatenate_group
from cptla.reconstruction.grid import html_to_grid


def fragment(i=0, html="<table><tr><th>A</th><td>B</td></tr></table>"):
    return dict(fragment_id=f"f{i}", page_num=i, part_index=i, html=html, status="completed")


def expected(*items):
    return [{k: item[k] for k in ("fragment_id", "page_num", "part_index")} for item in items]


def test_concat_preserves_headers_text_and_order():
    a, b = fragment(), fragment(2)
    out = concatenate_group("g", [b, a], expected(a, b))
    assert out["status"] == "completed"
    assert out["source_pages"] == [0, 2]
    grid = html_to_grid(out["html"])
    assert grid.n_rows == 2 and grid.n_cols == 2
    assert [c.text for c in grid.cells] == ["A", "B", "A", "B"]
    assert sum(c.header for c in grid.cells) == 2


def test_rowspan_preserved_with_offset():
    a = fragment(
        html='<table><tr><td rowspan="2">X</td><td></td></tr><tr><td> Y </td></tr></table>'
    )
    b = fragment(1)
    out = concatenate_group("g", [a, b], expected(a, b))
    cells = html_to_grid(out["html"]).cells
    assert cells[0].row_end == 2
    assert cells[3].row_start == 2
    assert cells[2].text == " Y "


def test_coverage_and_source_failures():
    a, b = fragment(), fragment(1)
    for predictions, reason in [
        ([], "missing_fragments"),
        ([a, a], "duplicate_fragments"),
        ([a, b], "extra_fragments"),
        ([dict(a, page_num=9)], "source_identity_mismatch"),
    ]:
        out = concatenate_group("g", predictions, expected(a))
        assert out["status"] == "failed" and out["html"] is None
        assert reason in out["diagnostics"]["failure_reasons"]
        assert out["diagnostics"]["raw_predictions"] == predictions


def test_invalid_failed_and_inconsistent_width():
    a = fragment()
    for b, reason in [
        (fragment(1, "broken"), "invalid_html"),
        (dict(fragment(1), status="failed"), "fragment_failed"),
        (fragment(1, "<table><tr><td>A</td></tr></table>"), "column_mismatch"),
    ]:
        out = concatenate_group("g", [a, b], expected(a, b))
        assert out["status"] == "failed"
        assert reason in out["diagnostics"]["failure_reasons"]


def test_bad_manifest_rejected():
    import pytest

    a = fragment()
    for items in [[], expected(a, a), [dict(expected(a)[0], page_num=True)]]:
        with pytest.raises(ValueError):
            concatenate_group("g", [a], items)
