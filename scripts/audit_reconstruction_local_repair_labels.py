"""Train-fit 审计。用严格行锚点从整表真值提取待人工验证的局部弱标签。"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

from probe_reconstruction_visual_repair import (
    BASELINE,
    BASELINE_HASHES_SHA,
    BASELINE_PREDICTIONS_SHA,
    IDENTITY,
    INPUTS,
    ORDER,
    TARGETS,
    safe,
)

from cptla.reconstruction.data import DATASET_REVISION
from cptla.reconstruction.grid import Grid, grid_to_html, html_to_grid

MAX_REPEAT = 3
MIN_ANCHOR_CHAR_SIMILARITY = 0.95


def row_cells(grid):
    rows = [[] for _ in range(grid.n_rows)]
    for cell in grid.cells:
        rows[cell.row_start].append(cell)
    return rows


def row_signatures(grid):
    """保留原始文字、列跨度和行跨度，标签角色不参与行定位。"""
    return tuple(
        tuple((c.row_end - c.row_start, c.col_start, c.col_end, c.text) for c in row)
        for row in row_cells(grid)
    )


def split_points(grid):
    forbidden = {r for c in grid.cells for r in range(c.row_start + 1, c.row_end)}
    return set(range(grid.n_rows + 1)) - forbidden


def text_rows(grid):
    """忽略列坐标但保留每个单元格的原文；末端词证据不得跨行。"""
    return tuple(tuple(c.text for c in row if c.text.strip()) for row in row_cells(grid))


def prefix_options(local, global_table, *, repeated, text_only=False):
    local_cut, global_cut = split_points(local), split_points(global_table)
    if not repeated:
        return [0]
    signature = text_rows if text_only else row_signatures
    given, reference = signature(local), signature(global_table)
    return [0] + [
        n
        for n in range(1, min(MAX_REPEAT, local.n_rows - 1, global_table.n_rows - 1) + 1)
        if n in local_cut
        and n in global_cut
        and any(text_rows(local)[:n])
        and given[:n] == reference[:n]
    ]


def character_similarity(cells):
    """以字符数量加权，并禁止跨单元格匹配文字。"""
    matches = size = 0
    for left, right in cells:
        size += len(left) + len(right)
        matches += (
            len(left)
            if left == right
            else sum(
                m.size
                for m in SequenceMatcher(None, left, right, autojunk=False).get_matching_blocks()
            )
        )
    return 2 * matches / size if size else 1.0


def aligned_cell_text(rows, target):
    return [
        [(c[-1], expected[-1]) for c, expected in zip(a, b, strict=True)]
        for a, b in zip(rows, target, strict=True)
    ]


def anchor_matches(rows, target, occurrences, mode):
    if rows == target:
        return True
    if mode == "strict":
        return False
    if len(rows) != len(target) or any(
        tuple(c[:3] for c in row) != tuple(c[:3] for c in expected)
        for row, expected in zip(rows, target, strict=True)
    ):
        return False
    if mode == "shape_only":
        return True
    pairs_by_row = aligned_cell_text(rows, target)
    for boundary in (pairs_by_row[0], pairs_by_row[-1]):
        if character_similarity(boundary) < MIN_ANCHOR_CHAR_SIMILARITY or not any(
            left == right and occurrences.get(right) == 1 and sum(c.isalnum() for c in right) >= 3
            for left, right in boundary
        ):
            return False
    return (
        character_similarity(pair for pairs in pairs_by_row for pair in pairs)
        >= MIN_ANCHOR_CHAR_SIMILARITY
    )


def anchor_evidence(fragments, truth, anchors):
    signature = row_signatures(truth)
    rows = []
    for index, cut, start, end in anchors:
        pairs = aligned_cell_text(
            row_signatures(html_to_grid(fragments[index]["html"]))[cut:], signature[start:end]
        )
        rows.append(
            dict(
                fragment_id=fragments[index]["fragment_id"],
                exact=all(left == right for row in pairs for left, right in row),
                character_similarity=character_similarity(pair for row in pairs for pair in row),
                first_row_character_similarity=character_similarity(pairs[0]),
                last_row_character_similarity=character_similarity(pairs[-1]),
            )
        )
    return rows


def anchor_paths(grids, indices, truth, *, from_end=False, mode="strict"):
    """严格从整表一端开始贴合锚片；每个边界只需保留最多两个歧义路径。"""
    target = row_signatures(truth)
    safe_cuts = split_points(truth)
    occurrences = Counter(text for row in text_rows(truth) for text in set(row))
    paths = {truth.n_rows if from_end else 0: [()]}
    for index in indices:
        grid = grids[index]
        signatures = row_signatures(grid)
        valid_prefix = prefix_options(grid, truth, repeated=index > 0)
        next_paths = {}
        for cursor, previous in paths.items():
            for cut in valid_prefix:
                rows = signatures[cut:]
                start, end = (
                    (cursor - len(rows), cursor) if from_end else (cursor, cursor + len(rows))
                )
                if (
                    start not in safe_cuts
                    or end not in safe_cuts
                    or not anchor_matches(rows, target[start:end], occurrences, mode)
                ):
                    continue
                bucket = next_paths.setdefault(start if from_end else end, [])
                bucket.extend(path + ((index, cut, start, end),) for path in previous)
                del bucket[2:]
        paths = next_paths
    return paths


def derive_candidates(grids, truth, index, *, mode="strict"):
    """一个待修片段的全部通过区间，以失败阶段说明弃样原因。"""
    if any(grid.n_cols != truth.n_cols for i, grid in enumerate(grids) if i != index):
        return [], "anchor_width_differs_from_truth"
    left = anchor_paths(grids, range(index), truth, mode=mode)
    right = anchor_paths(grids, range(len(grids) - 1, index, -1), truth, from_end=True, mode=mode)
    if not left or not right:
        return [], "anchor_rows_not_exact_and_contiguous"
    intervals = [(start, end) for start in left for end in right if start < end]
    if not intervals:
        return [], "no_nonempty_span_safe_residual"
    grid = grids[index]
    local_text = text_rows(grid)
    truth_text = text_rows(truth)
    occurrences = Counter(text for row in truth_text for text in set(row))
    cuts = prefix_options(grid, truth, repeated=index > 0, text_only=True)

    def witness(observed, expected):
        return len(
            {
                text
                for text in set(observed) & set(expected)
                if occurrences[text] == 1 and sum(c.isalnum() for c in text) >= 3
            }
        )

    candidates, count_compatible = [], False
    for start, end in intervals:
        for cut in cuts:
            if end - start != grid.n_rows - cut:
                continue
            count_compatible = True
            first = witness(local_text[cut], truth_text[start])
            last = witness(local_text[-1], truth_text[end - 1])
            if not first or not last:
                continue
            for before in left[start]:
                for after in right[end]:
                    candidates.append(
                        dict(
                            target_index=index,
                            truth_row_start=start,
                            truth_row_end=end,
                            first_row_cell_witnesses=first,
                            last_row_cell_witnesses=last,
                            target_removed_repeated_prefix=cut,
                            anchors=sorted(before + after),
                        )
                    )
    if candidates:
        return candidates, "candidate"
    if count_compatible:
        return [], "target_boundary_missing_unique_text_or_split_row_suspected"
    return [], "target_rows_disagree_with_residual_or_split_row_suspected"


def inspect_group(parts, truth, *, mode="strict"):
    if len({p["page_num"] for p in parts}) != len(parts):
        return None, "multiple_fragments_on_same_page", []
    grids = [html_to_grid(part["html"]) for part in parts]
    widths = [grid.n_cols for grid in grids]
    eligible = [
        i
        for i, width in enumerate(widths)
        if len(set(widths[:i] + widths[i + 1 :])) == 1 and widths.count(width) == 1
    ]
    if not eligible:
        return None, "no_single_width_outlier", []
    candidates, attempts = [], []
    for index in eligible:
        found, reason = derive_candidates(grids, truth, index, mode=mode)
        candidates.extend(found)
        attempts.append(dict(target_index=index, status=reason, paths=len(found)))
    if len(candidates) == 1:
        return candidates[0], "accepted_weak_label", attempts
    if len(candidates) > 1:
        return None, "multiple_exact_paths_or_target_fragments", attempts
    # Prefer the deepest failed validation for tables with both possible outlier orientations.
    return (
        None,
        next(
            reason
            for reason in (
                "target_boundary_missing_unique_text_or_split_row_suspected",
                "target_rows_disagree_with_residual_or_split_row_suspected",
                "no_nonempty_span_safe_residual",
                "anchor_rows_not_exact_and_contiguous",
                "anchor_width_differs_from_truth",
            )
            if any(a["status"] == reason for a in attempts)
        ),
        attempts,
    )


def records(raw, groups):
    ids = b"|".join(re.escape(group).encode() for group in sorted(groups))
    selected = re.compile(rb'"group_id"\s*:\s*"(?:' + ids + rb')"')
    rows = [
        row
        for line in raw.split(b"\n")
        if selected.search(line)
        and (row := json.loads(line.decode("utf-8-sig")))["group_id"] in groups
    ]
    indexed = {row["group_id"]: row for row in rows}
    if len(rows) != len(groups) or indexed.keys() != groups:
        raise ValueError("duplicate or missing group rows")
    return indexed


def run(root, name, *, code_sha, relaxed=False):
    root = root.resolve()
    if not re.fullmatch(r"\d{8}T\d{6}Z-[A-Za-z0-9_-]+", name):
        raise ValueError("timestamped run required")
    hashes = {}

    def read(path, expected=None):
        raw = safe(root, path).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if expected is not None and sha != expected:
            raise ValueError(f"frozen input changed: {path}")
        hashes[path.as_posix()] = sha
        return raw

    snapshot = json.loads(read(BASELINE / "predictions.json", BASELINE_PREDICTIONS_SHA))
    pinned = json.loads(read(BASELINE / "input-hashes.json", BASELINE_HASHES_SHA))
    failed = [
        row for row in snapshot if row["diagnostics"]["failure_reasons"] == ["column_mismatch"]
    ]
    groups = {row["group_id"] for row in failed}
    if len(failed) != 30 or len(groups) != 30:
        raise ValueError("expected 30 frozen column conflicts")
    originals = records(read(INPUTS), groups)
    targets = records(read(TARGETS, pinned[TARGETS.as_posix()]), groups)

    counts, labels, details, comparison = Counter(), [], [], Counter()
    for row in sorted(failed, key=lambda r: r["group_id"]):
        group = row["group_id"]
        source, target = originals[group], targets[group]
        fragments = sorted(
            row["diagnostics"]["raw_predictions"], key=lambda p: tuple(p[k] for k in ORDER)
        )
        raw_ids = {(p["fragment_id"], p["page_num"], p["part_index"]) for p in fragments}
        expected_ids = {
            (p["fragment_id"], p["page_num"], p["part_index"]) for p in source["fragments"]
        }
        if (
            source["split"] != "train_fit"
            or source["source_split"] != "train"
            or source["dataset_revision"] != DATASET_REVISION
            or raw_ids != expected_ids
            or len(raw_ids) != len(fragments)
            or any(p["group_id"] != group or p["status"] != "completed" for p in fragments)
            or target["document_id"] != source["document_id"]
            or set(target["source_pages"]) != {p["page_num"] for p in fragments}
        ):
            raise ValueError(f"split/identity/source validation failed: {group}")
        truth = html_to_grid(target["html"])
        mode = "char95" if relaxed else "strict"
        candidate, status, attempts = inspect_group(fragments, truth, mode=mode)
        if relaxed and candidate is not None:
            status = "manual_review_candidate_only"
            candidate["anchor_character_evidence"] = anchor_evidence(
                fragments, truth, candidate["anchors"]
            )
        detail = dict(group_id=group, status=status, attempts=attempts)
        if relaxed:
            _, strict_status, _ = inspect_group(fragments, truth)
            detail["strict_status"] = strict_status
            comparison["strict_accepted"] += strict_status == "accepted_weak_label"
            comparison["new_review_candidates"] += (
                strict_status != "accepted_weak_label" and candidate is not None
            )
            if strict_status == "anchor_rows_not_exact_and_contiguous":
                _, geometry_status, _ = inspect_group(fragments, truth, mode="shape_only")
                detail["geometry_only_status"] = geometry_status
                comparison["strict_anchor_failures"] += 1
                comparison["strict_anchor_failures_still_blocked_by_geometry"] += (
                    geometry_status
                    in {
                        "anchor_rows_not_exact_and_contiguous",
                        "no_nonempty_span_safe_residual",
                        "target_rows_disagree_with_residual_or_split_row_suspected",
                    }
                )
                comparison["strict_anchor_failures_rescued"] += candidate is not None
        details.append(detail)
        counts[status] += 1
        if candidate is None:
            continue
        index = candidate["target_index"]
        start, end = candidate["truth_row_start"], candidate["truth_row_end"]
        target_grid = Grid(
            end - start,
            truth.n_cols,
            tuple(
                replace(c, row_start=c.row_start - start, row_end=c.row_end - start)
                for c in truth.cells
                if start <= c.row_start and c.row_end <= end
            ),
        )
        html = grid_to_html(target_grid)
        labels.append(
            dict(
                **{key: fragments[index][key] for key in IDENTITY},
                **candidate,
                document_id=source["document_id"],
                cluster_id=source["cluster_id"],
                split="train_fit",
                status="manual_review_candidate_only"
                if relaxed
                else "weak_global_residual_unreviewed",
                page_gt_available=False,
                training_authorized=False,
                target_html=html,
                target_html_sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
            )
        )
    encoded = "".join(
        json.dumps(label, ensure_ascii=False, sort_keys=True) + "\n" for label in labels
    )
    output = safe(root, Path("artifacts/reconstruction-diagnostics") / name)
    output.mkdir(parents=True, exist_ok=False)
    filename = "manual-review-candidates.jsonl" if relaxed else "weak-candidates.jsonl"
    with (output / filename).open("xb") as stream:
        stream.write(encoded.encode("utf-8"))
    report = dict(
        created_utc=datetime.now(UTC).isoformat(),
        argv=sys.argv,
        code_sha256=code_sha,
        dataset_revision=DATASET_REVISION,
        split="train_fit",
        scope="30 column conflicts; no dev/confirm/test; offline supervision feasibility only",
        label_status="unreviewed weak residual slice; not page GT",
        training_authorized=False,
        n_groups=len(groups),
        n_accepted=len(labels),
        n_residual_intervals=sum(
            any(
                a["status"]
                in {
                    "candidate",
                    "target_boundary_missing_unique_text_or_split_row_suspected",
                    "target_rows_disagree_with_residual_or_split_row_suspected",
                }
                for a in detail["attempts"]
            )
            for detail in details
        ),
        counts=counts,
        input_sha256=hashes,
        candidate_sha256=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        per_group=details,
    )
    if relaxed:
        report.update(
            label_status="manual visual review candidates only; not page GT or training labels",
            anchor_minimum_character_similarity=MIN_ANCHOR_CHAR_SIMILARITY,
            anchor_witness_rule=(
                "new fuzzy anchors require overall and first/last >= threshold "
                "and unique exact cell at each boundary"
            ),
            candidate_file=filename,
            strict_comparison=comparison,
        )
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "per_group"}, ensure_ascii=False))


def main(code_sha=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--relaxed-anchors", action="store_true", help="manual visual review only")
    args = parser.parse_args()
    run(
        args.project_root,
        args.run,
        relaxed=args.relaxed_anchors,
        code_sha=code_sha or hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )


if __name__ == "__main__":
    main()
