from cptla.reconstruction.grid import html_to_grid
from cptla.reconstruction.header_baseline import deduplicate_headers_group


def run(a, b):
    ps = [
        dict(fragment_id=str(i), page_num=i, part_index=0, status="completed", html=h)
        for i, h in enumerate((a, b))
    ]
    return deduplicate_headers_group("g", ps, ps)


def test_explicit_header_only_and_keep_first():
    h = "<table><tr><th>A</th></tr><tr><td>B</td></tr></table>"
    out = run(h, h)
    assert html_to_grid(out["html"]).n_rows == 3
    assert out["diagnostics"]["removed_header_rows"] == {"0": 0, "1": 1}
    assert out["source_pages"] == [0, 1]
    assert html_to_grid(run(h.replace("th", "td"), h.replace("th", "td"))["html"]).n_rows == 4


def test_all_header_fragment_is_retained():
    h = "<table><tr><th>A</th></tr></table>"
    assert html_to_grid(run(h, h)["html"]).n_rows == 2


def test_rowspan_boundary_not_truncated_and_text_exact():
    h = '<table><tr><th rowspan="2">A</th><th>B</th></tr><tr><td>C</td></tr></table>'
    assert html_to_grid(run(h, h)["html"]).n_rows == 4
    a = "<table><tr><th>A</th></tr><tr><td>B</td></tr></table>"
    assert html_to_grid(run(a, a.replace(">A<", "> A<"))["html"]).n_rows == 4


def test_coverage_validation_reused():
    p = dict(fragment_id="a", page_num=0, part_index=0)
    out = deduplicate_headers_group("g", [], [p])
    assert out["status"] == "failed"
    assert "missing_fragments" in out["diagnostics"]["failure_reasons"]
