"""R0 固定组匹配诊断 v1；并非已核准的官方 Acc-Con/Acc-Top。

内容比较展开位置的原文，结构比较 cell 半开边界；不规范化空白。
无效预测全组失败，全部 target 保持在分母中；额外预测单列。
"""

from collections import defaultdict

from cptla.reconstruction.grid import GRID_VERSION, GridError, html_to_grid

SCORE_VERSION = "cptla-r0-diagnostic-v1"
METRICS = ("top_exact", "con_exact", "source_exact", "joint_exact", "source_joint_exact")


def _pages(value):
    if (
        not isinstance(value, list)
        or not value
        or any(type(p) is not int or p < 0 for p in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError("invalid source_pages")
    return frozenset(value)


def _top(grid):
    return frozenset((c.row_start, c.row_end, c.col_start, c.col_end) for c in grid.cells)


def _content(grid):
    return {
        (r, col): c.text
        for c in grid.cells
        for r in range(c.row_start, c.row_end)
        for col in range(c.col_start, c.col_end)
    }


def score_groups(targets: list[dict], predictions: list[dict]) -> dict:
    """一组一表固定匹配。空 target 集的比率为 None，禁止空分母报满分。"""
    if not isinstance(targets, list) or not isinstance(predictions, list):
        raise ValueError("targets and predictions must be lists")
    truth = {}
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("invalid target record")
        gid = target.get("group_id")
        if not isinstance(gid, str) or not gid.strip() or gid in truth:
            raise ValueError("invalid or duplicate target group_id")
        truth[gid] = (html_to_grid(target.get("html")), _pages(target.get("source_pages")))
    grouped = defaultdict(list)
    extras = []
    for index, prediction in enumerate(predictions):
        gid = prediction.get("group_id") if isinstance(prediction, dict) else None
        if not isinstance(gid, str) or gid not in truth:
            extras.append({"prediction_index": index, "group_id": gid})
        else:
            grouped[gid].append(prediction)
    per_group = []
    for gid, (target_grid, target_pages) in truth.items():
        result = {"group_id": gid, **dict.fromkeys(METRICS, False), "failure_reason": None}
        candidates = grouped[gid]
        if not candidates:
            result["failure_reason"] = "missing_prediction"
        elif len(candidates) != 1:
            result["failure_reason"] = "multiple_predictions"
        elif "status" in candidates[0] and candidates[0]["status"] != "completed":
            result["failure_reason"] = "prediction_failed"
        else:
            prediction = candidates[0]
            try:
                grid = html_to_grid(prediction.get("html"))
            except (GridError, TypeError, ValueError) as exc:
                result.update(failure_reason="invalid_html", failure_detail=str(exc))
            else:
                try:
                    pages = _pages(prediction.get("source_pages"))
                except ValueError:
                    result["failure_reason"] = "invalid_source_pages"
                else:
                    result["top_exact"] = _top(grid) == _top(target_grid)
                    result["con_exact"] = _content(grid) == _content(target_grid)
                    result["source_exact"] = pages == target_pages
                    result["joint_exact"] = result["top_exact"] and result["con_exact"]
                    result["source_joint_exact"] = result["joint_exact"] and result["source_exact"]
        per_group.append(result)
    n = len(truth)
    return {
        "score_version": SCORE_VERSION,
        "grid_version": GRID_VERSION,
        "metric_status": "project_diagnostic_not_official_accuracy",
        "n_targets": n,
        "n_predictions": len(predictions),
        "extra_prediction_count": len(extras),
        "extra_predictions": extras,
        "per_group": per_group,
        "diagnostic_rates": {
            key: sum(r[key] for r in per_group) / n if n else None for key in METRICS
        },
    }
