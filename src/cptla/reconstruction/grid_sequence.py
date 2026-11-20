"""global-grid-v1严格序列接口，保持文本和单元格角色。"""

import json

from cptla.reconstruction.grid import Cell, Grid, GridError, grid_to_html, html_to_grid


def grid_to_sequence(grid):
    return json.dumps(
        dict(
            schema_version="global-grid-v1",
            num_rows=grid.n_rows,
            num_cols=grid.n_cols,
            cells=[
                dict(
                    r0=c.row_start,
                    r1=c.row_end,
                    c0=c.col_start,
                    c1=c.col_end,
                    text=c.text,
                    role="header" if c.header else "data",
                )
                for c in grid.cells
            ],
        ),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GridError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise GridError("nonfinite JSON constant")


def sequence_to_grid(text):
    if not isinstance(text, str) or len(text) > 2_000_000:
        raise GridError("invalid grid sequence size/type")
    try:
        payload = json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, RecursionError) as error:
        raise GridError("invalid grid JSON") from error
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "num_rows",
        "num_cols",
        "cells",
    }:
        raise GridError("invalid grid schema fields")
    if payload["schema_version"] != "global-grid-v1" or not isinstance(payload["cells"], list):
        raise GridError("unsupported grid schema")
    cells = []
    for c in payload["cells"]:
        if not isinstance(c, dict) or set(c) != {"r0", "r1", "c0", "c1", "text", "role"}:
            raise GridError("invalid cell fields")
        if c["role"] not in ("header", "data"):
            raise GridError("invalid cell role")
        cells.append(Cell(c["r0"], c["r1"], c["c0"], c["c1"], c["text"], c["role"] == "header"))
    return Grid(payload["num_rows"], payload["num_cols"], tuple(cells))


def html_to_sequence(html):
    return grid_to_sequence(html_to_grid(html))


def sequence_to_html(text):
    return grid_to_html(sequence_to_grid(text))
