import pytest

import cptla.reconstruction.grid as module
from cptla.reconstruction.grid import Cell, Grid, GridError, grid_to_html, html_to_grid


def test_semantic_roundtrip():
    grid = html_to_grid(
        '<table><thead><tr><th colspan="2">A&nbsp;<b>&amp;</b>B</th></tr></thead>'
        '<tbody><tr><td rowspan="2"> x </td><td></td></tr>'
        "<tr><td>C<br>D</td></tr></tbody></table>"
    )
    assert grid.n_rows == 3 and grid.n_cols == 2
    assert grid.cells[0] == Cell(0, 1, 0, 2, "A\xa0&B", True)
    assert grid.cells[-1].text == "C\nD"
    assert html_to_grid(grid_to_html(grid)) == grid


def test_optional_cell_closing():
    assert len(html_to_grid("<table><tr><td>A<td>B</tr></table>").cells) == 2


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<table><tr><td>A",
        "<table><tr><td>A</tr>",
        "<table></table><table></table>",
        '<table><tr><td rowspan="0">A</td></tr></table>',
        '<table><tr><td rowspan="2">A</td></tr></table>',
        '<table><tr><td>A</td><td rowspan="2">B</td></tr><tr><td colspan="2">C</td></tr></table>',
        "<table><tr><td><table></table></td></tr></table>",
        '<table><tr><td><img src="x"></td></tr></table>',
        "<table><caption>lost</caption><tr><td>A</td></tr></table>",
        "<table><tr><td>A</td></tr></table>lost",
        "<table><tr><td><b>A</td></tr></table>",
    ],
)
def test_invalid_html_is_rejected(html):
    with pytest.raises(GridError):
        html_to_grid(html)


@pytest.mark.parametrize(
    "cells",
    [
        (Cell(0, 1, 0, 1, "a"), Cell(0, 1, 0, 1, "b")),
        (Cell(0, 2, 0, 1, "a"),),
        (Cell(-1, 1, 0, 1, "a"),),
    ],
)
def test_invalid_grid(cells):
    with pytest.raises(GridError):
        Grid(1, 1, cells)


def test_holes_rejected_not_filled():
    with pytest.raises(GridError):
        html_to_grid("<table><tr><td>A</td><td>B</td></tr><tr><td>C</td></tr></table>")


def test_empty_cell_and_escaping():
    g = Grid(1, 2, (Cell(0, 1, 0, 1, ""), Cell(0, 1, 1, 2, '<>&"\n')))
    assert html_to_grid(grid_to_html(g)) == g


@pytest.mark.parametrize(
    "limit, value, html",
    [
        ("MAX_HTML_CHARS", 10, "<table><tr><td>A</td></tr></table>"),
        ("MAX_ROWS", 1, "<table><tr><td>A</td></tr><tr><td>B</td></tr></table>"),
        ("MAX_COLS", 1, '<table><tr><td colspan="2">A</td></tr></table>'),
        ("MAX_POSITIONS", 1, '<table><tr><td colspan="2">A</td></tr></table>'),
    ],
)
def test_parser_limits(monkeypatch, limit, value, html):
    monkeypatch.setattr(module, limit, value, raising=False)
    with pytest.raises(GridError, match="limit"):
        html_to_grid(html)


def test_grid_limit_before_expansion(monkeypatch):
    monkeypatch.setattr(module, "MAX_POSITIONS", 1, raising=False)
    with pytest.raises(GridError, match="limit"):
        Grid(1, 2, (Cell(0, 1, 0, 2, ""),))


def test_unsupported_version():
    with pytest.raises(GridError, match="version"):
        Grid(1, 1, (Cell(0, 1, 0, 1, ""),), version="unknown")


def test_boolean_coordinates():
    with pytest.raises(GridError):
        Grid(1, 1, (Cell(False, 1, 0, 1, ""),))
    with pytest.raises(GridError):
        Grid(True, 1, (Cell(0, 1, 0, 1, ""),))


@pytest.mark.parametrize("span", ["99999999999999999999", "9" * 5000])
def test_huge_span_rejected_before_expansion(span):
    with pytest.raises(GridError, match="limit"):
        html_to_grid(f'<table><tr><td colspan="{span}">A</td></tr></table>')


@pytest.mark.parametrize(
    "prefix,suffix",
    [("<html>", "</html>"), ("<html><body>", "</body></html>"), ("<body>", "</body>")],
)
def test_optional_document_wrappers(prefix, suffix):
    bare = "<table><thead><tr><th>A</th></tr></thead><tbody><tr><td>B</td></tr></tbody></table>"
    assert html_to_grid(prefix + bare + suffix) == html_to_grid(bare)


@pytest.mark.parametrize(
    "html",
    [
        "<html><table><tr><td>A</td></tr></table>",
        "<html><body><table><tr><td>A</td></tr></table></html>",
        "<html>outside<table><tr><td>A</td></tr></table></html>",
        "<html><table><tr><td>A</td></tr></table>outside</html>",
        "<html><table><tr><td>A</td></tr></table><table><tr><td>B</td></tr></table></html>",
        "<html><script>alert(1)</script><table><tr><td>A</td></tr></table></html>",
        "<html><html><table><tr><td>A</td></tr></table></html></html>",
        "<html></html><table><tr><td>A</td></tr></table>",
        "<table><tr><td>A</td></tr></table><html></html>",
    ],
)
def test_document_wrapper_contract_rejections(html):
    with pytest.raises(GridError):
        html_to_grid(html)
