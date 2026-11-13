"""B0 纯纵向拼接；保留重复表头，不作列修复或内容规范化。"""

from collections import Counter
from copy import deepcopy
from dataclasses import replace

from cptla.reconstruction.grid import Grid, GridError, grid_to_html, html_to_grid


def _identity(item):
    if not isinstance(item, dict):
        raise ValueError("fragment must be a record")
    fid = item.get("fragment_id")
    if not isinstance(fid, str) or not fid.strip():
        raise ValueError("invalid fragment_id")
    for key in ("page_num", "part_index"):
        if type(item.get(key)) is not int or item[key] < 0:
            raise ValueError(f"invalid {key}")
    return fid, item["page_num"], item["part_index"]


def concatenate_group(
    group_id: str, predictions: list[dict], expected_fragments: list[dict]
) -> dict:
    """expected_fragments 仅含输入来源身份，不得由目标 HTML 挑选预测。

    输入清单错误抛 ValueError；预测覆盖/解析失败返回整组 failed 和完整原始记录。
    """
    if not isinstance(group_id, str) or not group_id.strip():
        raise ValueError("invalid group_id")
    if not isinstance(predictions, list) or not isinstance(expected_fragments, list):
        raise ValueError("fragment collections must be lists")
    identities = [_identity(item) for item in expected_fragments]
    if not identities or len({i[0] for i in identities}) != len(identities):
        raise ValueError("empty or duplicate expected fragments")
    if len({i[1:] for i in identities}) != len(identities):
        raise ValueError("ambiguous fragment order")
    expected = {item[0]: item for item in identities}
    result = dict(
        group_id=group_id,
        html=None,
        source_pages=[],
        status="failed",
        diagnostics=dict(
            baseline="B0_vertical_concat_v1",
            failure_reasons=[],
            raw_predictions=deepcopy(predictions),
        ),
    )
    diagnostics = result["diagnostics"]
    reasons = diagnostics["failure_reasons"]
    actual = []
    for prediction in predictions:
        try:
            actual.append(_identity(prediction))
        except ValueError:
            reasons.append("invalid_source_identity")
    counts = Counter(item[0] for item in actual)
    diagnostics["missing_fragment_ids"] = sorted(set(expected) - set(counts))
    diagnostics["extra_fragment_ids"] = sorted(set(counts) - set(expected))
    diagnostics["duplicate_fragment_ids"] = sorted(k for k, n in counts.items() if n > 1)
    for field, reason in [
        ("missing_fragment_ids", "missing_fragments"),
        ("extra_fragment_ids", "extra_fragments"),
        ("duplicate_fragment_ids", "duplicate_fragments"),
    ]:
        if diagnostics[field]:
            reasons.append(reason)
    if any(item[0] in expected and item != expected[item[0]] for item in actual):
        reasons.append("source_identity_mismatch")
    result["source_pages"] = sorted({item[1] for item in actual})
    if reasons:
        return result
    ordered = sorted(predictions, key=lambda p: (p["page_num"], p["part_index"]))
    diagnostics["ordered_fragment_ids"] = [p["fragment_id"] for p in ordered]
    cells, rows, width = [], 0, None
    for prediction in ordered:
        if prediction.get("status") != "completed":
            reasons.append("fragment_failed")
            return result
        try:
            grid = html_to_grid(prediction.get("html"))
        except (GridError, ValueError, TypeError) as exc:
            reasons.append("invalid_html")
            diagnostics["error"] = str(exc)
            return result
        if width is not None and grid.n_cols != width:
            reasons.append("column_mismatch")
            return result
        width = grid.n_cols
        cells.extend(
            replace(c, row_start=c.row_start + rows, row_end=c.row_end + rows) for c in grid.cells
        )
        rows += grid.n_rows
    try:
        result["html"] = grid_to_html(Grid(rows, width, tuple(cells)))
    except GridError as exc:
        reasons.append("merged_grid_invalid")
        diagnostics["error"] = str(exc)
        return result
    result["status"] = "completed"
    return result
