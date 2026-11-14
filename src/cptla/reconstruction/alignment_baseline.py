"""预测专用保守列对齐与单独记录的重复前缀启发式；非完整 B1。"""

from dataclasses import replace

from cptla.reconstruction.baselines import concatenate_group
from cptla.reconstruction.grid import Cell, Grid, GridError, grid_to_html, html_to_grid

BASELINE_ID = "monotone_first_row_alignment_exact_prefix_v1"


def _labels(grid):
    cells = [c for c in grid.cells if c.row_start == 0]
    if len(cells) != grid.n_cols or any(
        not c.text.strip() or c.row_end != 1 or c.col_end - c.col_start != 1 for c in cells
    ):
        raise ValueError("missing_simple_first_row_label_evidence")
    return [c.text for c in cells]


def _mapping(grid, reference):
    if grid.n_cols == reference.n_cols:
        return list(range(grid.n_cols))
    labels, refs = _labels(grid), _labels(reference)
    mapping = []
    for label in labels:
        hits = [i for i, text in enumerate(refs) if text == label]
        if len(hits) != 1:
            raise ValueError("ambiguous_or_unmatched_column")
        mapping.append(hits[0])
    if mapping != sorted(set(mapping)):
        raise ValueError("non_monotone_mapping")
    return mapping


def _expand(grid, mapping, width):
    cells = []
    for c in grid.cells:
        cols = mapping[c.col_start : c.col_end]
        if cols != list(range(cols[0], cols[-1] + 1)):
            raise ValueError("colspan_crosses_inserted_column")
        cells.append(replace(c, col_start=cols[0], col_end=cols[-1] + 1))
    missing = sorted(set(range(width)) - set(mapping))
    cells.extend(Cell(r, r + 1, col, col + 1, "") for r in range(grid.n_rows) for col in missing)
    return Grid(grid.n_rows, width, tuple(cells)), missing


def _prefix(first, grid):
    # 最大三行，完整边界，绝不删除整个片段；不声称是表头标签。
    best = 0
    for end in range(1, min(3, first.n_rows - 1, grid.n_rows - 1) + 1):
        if any(c.row_start < end < c.row_end for g in (first, grid) for c in g.cells):
            continue
        a = tuple(c for c in first.cells if c.row_end <= end)
        b = tuple(c for c in grid.cells if c.row_end <= end)
        if a == b and any(c.text.strip() for c in a):
            best = end
    return best


def align_group(group_id, predictions, expected_fragments):
    result = concatenate_group(group_id, predictions, expected_fragments)
    diag = result["diagnostics"]
    diag.update(
        alignment_heuristic="first_row_exact_label_heuristic",
        audit_status="unreviewed_candidate_not_official_labels",
        prefix_risk="may_remove_repeated_body_rows",
        baseline=BASELINE_ID,
        column_maps={},
        inserted_columns={},
        removed_prefix_rows={},
        prefix_heuristic="exact_nonempty_prefix_max3_v1_not_official_labels",
        alignment_evidence=(
            "widest_first_reference; equal_width_identity; "
            "unequal_unique_exact_first_row_labels"
        ),
    )
    if result["status"] != "completed" and diag["failure_reasons"] != ["column_mismatch"]:
        return result
    # B0 may stop at first width mismatch: validate all remaining fragments independently.
    for p in predictions:
        check = concatenate_group(group_id, [p], [p])
        if check["status"] != "completed":
            diag["failure_reasons"] = check["diagnostics"]["failure_reasons"]
            result.update(status="failed", html=None)
            return result
    ordered = sorted(predictions, key=lambda p: (p["page_num"], p["part_index"]))
    try:
        grids = [html_to_grid(p["html"]) for p in ordered]
        reference = max(grids, key=lambda g: g.n_cols)
        expanded = []
        for p, grid in zip(ordered, grids, strict=True):
            mapping = _mapping(grid, reference)
            mapped, missing = _expand(grid, mapping, reference.n_cols)
            fid = p["fragment_id"]
            diag["column_maps"][fid] = mapping
            diag["inserted_columns"][fid] = missing
            expanded.append(mapped)
        cells, rows = [], 0
        for i, (p, grid) in enumerate(zip(ordered, expanded, strict=True)):
            remove = _prefix(expanded[0], grid) if i else 0
            diag["removed_prefix_rows"][p["fragment_id"]] = remove
            cells.extend(
                replace(c, row_start=c.row_start + rows - remove, row_end=c.row_end + rows - remove)
                for c in grid.cells
                if c.row_start >= remove
            )
            rows += grid.n_rows - remove
        result.update(
            status="completed", html=grid_to_html(Grid(rows, reference.n_cols, tuple(cells)))
        )
        diag["failure_reasons"] = []
    except (ValueError, GridError) as exc:
        result.update(status="failed", html=None)
        diag["failure_reasons"] = [str(exc)]
    return result
