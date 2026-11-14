from cptla.reconstruction.alignment_baseline import align_group
from cptla.reconstruction.grid import html_to_grid


def run(a, b):
    ps = [
        dict(fragment_id=str(i), page_num=i, part_index=0, status="completed", html=h)
        for i, h in enumerate((a, b))
    ]
    return align_group("g", ps, ps)


def test_missing_middle_column_explicit_empty():
    a = (
        "<table><tr><th>A</th><th>B</th><th>C</th></tr>"
        "<tr><td>1</td><td>2</td><td>3</td></tr></table>"
    )
    b = "<table><tr><th>A</th><th>C</th></tr><tr><td>x</td><td>z</td></tr></table>"
    out = run(a, b)
    assert out["status"] == "completed"
    grid = html_to_grid(out["html"])
    assert grid.n_cols == 3
    assert any(c.text == "" and c.col_start == 1 and c.row_start == 3 for c in grid.cells)
    assert out["diagnostics"]["column_maps"]["1"] == [0, 2]


def test_ambiguous_headers_fail():
    a = "<table><tr><th>A</th><th>A</th></tr></table>"
    b = "<table><tr><th>A</th></tr></table>"
    assert run(a, b)["status"] == "failed"


def test_prefix_is_separate_logged_heuristic():
    a = "<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>"
    b = a.replace(">1<", ">3<")
    out = run(a, b)
    assert html_to_grid(out["html"]).n_rows == 3
    assert out["diagnostics"]["removed_prefix_rows"]["1"] == 1


def test_rowspan_prefix_never_cut():
    a = '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'
    b = a.replace(">C<", ">D<")
    assert html_to_grid(run(a, b)["html"]).n_rows == 4


def test_failed_later_fragment_cannot_be_hidden_by_mismatch():
    ps = [
        dict(fragment_id=str(i), page_num=i, part_index=0, status="completed", html=h)
        for i, h in enumerate(
            (
                "<table><tr><td>A</td></tr></table>",
                "<table><tr><td>A</td><td>B</td></tr></table>",
                "bad",
            )
        )
    ]
    out = align_group("g", ps, ps)
    assert out["status"] == "failed"
    assert out["html"] is None
    assert len(out["diagnostics"]["raw_predictions"]) == 3


def test_colspan_cannot_invent_inserted_span():
    a = (
        "<table><tr><th>A</th><th>B</th><th>C</th></tr></table>"
    )
    b = '<table><tr><th>A</th><th>C</th></tr><tr><td colspan="2">x</td></tr></table>'
    assert run(a, b)["diagnostics"]["failure_reasons"] == ["colspan_crosses_inserted_column"]


def test_all_td_first_row_exact_label_heuristic():
    a = (
        "<table><tr><td>A</td><td>B</td><td>C</td></tr>"
        "<tr><td>1</td><td>2</td><td>3</td></tr></table>"
    )
    b = "<table><tr><td>A</td><td>C</td></tr><tr><td>x</td><td>z</td></tr></table>"
    out = run(a, b)
    assert out["status"] == "completed"
    assert out["diagnostics"]["column_maps"]["1"] == [0, 2]
    assert out["diagnostics"]["alignment_heuristic"] == "first_row_exact_label_heuristic"
    assert out["diagnostics"]["audit_status"] == "unreviewed_candidate_not_official_labels"


def test_repeated_body_false_removal_is_retained_in_provenance():
    # 首行其实是重复观测正文：启发式无法知道，会删除，必须可审计。
    a = "<table><tr><td>100</td><td>200</td></tr><tr><td>101</td><td>201</td></tr></table>"
    b = a.replace(">101<", ">102<")
    out = run(a, b)
    assert out["diagnostics"]["removed_prefix_rows"]["1"] == 1
    assert out["diagnostics"]["raw_predictions"][1]["html"] == b
    assert out["diagnostics"]["prefix_risk"] == "may_remove_repeated_body_rows"
