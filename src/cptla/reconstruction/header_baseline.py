"""预测显式表头完全匹配的保守去重；不实现列对齐或完整 B1。"""

from dataclasses import replace

from cptla.reconstruction.baselines import concatenate_group
from cptla.reconstruction.grid import Grid, grid_to_html, html_to_grid

BASELINE_ID = "explicit_header_exact_v1"


def _header_prefix(grid):
    """只接受全部位置均为 th/thead 的完整首部；不截断 rowspan。"""
    end = 0
    for row in range(grid.n_rows):
        covering = [c for c in grid.cells if c.row_start <= row < c.row_end]
        if not all(c.header for c in covering):
            break
        end = row + 1
    if any(c.row_start < end < c.row_end for c in grid.cells):
        return 0
    return end


def deduplicate_headers_group(group_id, predictions, expected_fragments):
    result = concatenate_group(group_id, predictions, expected_fragments)
    diag = result["diagnostics"]
    diag["baseline"] = BASELINE_ID
    diag["header_evidence"] = (
        "all_cells_th_or_thead; exact_text_and_spans; first_fragment_reference"
    )
    diag["removed_header_rows"] = {}
    if result["status"] != "completed":
        return result
    ordered = sorted(predictions, key=lambda p: (p["page_num"], p["part_index"]))
    grids = [html_to_grid(p["html"]) for p in ordered]
    first = grids[0]
    prefix = _header_prefix(first)
    reference = tuple(c for c in first.cells if c.row_end <= prefix)
    cells, rows = [], 0
    for index, (prediction, grid) in enumerate(zip(ordered, grids, strict=True)):
        remove = 0
        if (
            index
            and prefix
            and prefix < grid.n_rows
            and _header_prefix(grid) == prefix
            and tuple(c for c in grid.cells if c.row_end <= prefix) == reference
        ):
            remove = prefix
        diag["removed_header_rows"][prediction["fragment_id"]] = remove
        cells.extend(
            replace(c, row_start=c.row_start + rows - remove, row_end=c.row_end + rows - remove)
            for c in grid.cells
            if c.row_start >= remove
        )
        rows += grid.n_rows - remove
    result["html"] = grid_to_html(Grid(rows, first.n_cols, tuple(cells)))
    return result
