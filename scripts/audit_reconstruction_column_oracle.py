"""Bounded monotone column-insertion oracle for the frozen 30 failed train_fit groups."""

import argparse
import hashlib
import json
from collections import Counter
from itertools import combinations
from math import comb
from pathlib import Path

from audit_reconstruction_boundary_oracle import identities, prefix_options, read_jsonl, row_views

from cptla.reconstruction.alignment_baseline import _expand
from cptla.reconstruction.grid import html_to_grid


def column_options(grid, width, budget):
    if comb(width, grid.n_cols) > budget:
        raise OverflowError("column map budget exceeded")
    possibilities = []
    for mapping in combinations(range(width), grid.n_cols):
        try:
            mapped, _ = _expand(grid, list(mapping), width)
        except ValueError:
            continue
        possibilities.append((mapping, mapped, row_views(mapped)))
    return possibilities


def match_columns(options, truth, *, allow_prefix):
    """Count edit paths for dimensions, topology, content, and their conjunction."""
    target_rows = row_views(truth)
    paths = Counter(dict(dimensions=0, topology=0, content=0, joint=0))
    examples = {}
    explored = 0
    for mapping, first_grid, first_rows in options[0]:
        first_n = len(first_rows)
        if first_n > len(target_rows):
            continue

        def matching(rows, offset):
            paired = list(zip(rows, target_rows[offset : offset + len(rows)], strict=True))
            return all(a.topology == b.topology for a, b in paired), all(
                a.text == b.text for a, b in paired
            )

        top, con = matching(first_rows, 0)
        states = {(first_n, top, con): (1, ((mapping, 0),))}
        for current in options[1:]:
            next_states = {}
            for output_map, grid, rows in current:
                cuts = prefix_options(first_grid, grid, False) if allow_prefix else (0,)
                for cut in cuts:
                    part = rows[cut:]
                    for (offset, prefix_top, prefix_con), (count, prior_path) in states.items():
                        end = offset + len(part)
                        if end > len(target_rows):
                            continue
                        explored += 1
                        if explored > 1_000_000:
                            raise OverflowError("column alignment state budget exceeded")
                        local_top, local_con = matching(part, offset)
                        key = (end, prefix_top and local_top, prefix_con and local_con)
                        n, example = next_states.get(key, (0, prior_path + ((output_map, cut),)))
                        next_states[key] = n + count, example
            states = next_states
        for (rows, top, con), (count, example) in states.items():
            if rows != len(target_rows):
                continue
            for key, matched in (
                ("dimensions", True),
                ("topology", top),
                ("content", con),
                ("joint", top and con),
            ):
                if matched:
                    paths[key] += count
                    examples.setdefault(key, example)
    return dict(paths=paths, examples=examples, states_visited=explored)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--boundary-report", type=Path, required=True)
    parser.add_argument("--b0", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    hashes = {}

    def read(name):
        file = (root / name).resolve()
        key = file.relative_to(root).as_posix()
        data = file.read_bytes()
        hashes[key] = hashlib.sha256(data).hexdigest()
        return data

    boundary = json.loads(read(args.boundary_report))
    targets_path = boundary["command_config"]["targets"]
    inputs_path = boundary["command_config"]["inputs"]
    baseline = Path(boundary["command_config"]["baseline"]) / "predictions.json"
    aligned = json.loads(read(baseline))
    b0 = json.loads(read(args.b0))
    failed = [p for p in b0 if p["status"] != "completed"]
    ids = {p["group_id"] for p in failed}
    if (
        len(failed) != 30
        or len(ids) != 30
        or any(p["diagnostics"]["failure_reasons"] != ["column_mismatch"] for p in failed)
    ):
        raise ValueError("expected exactly 30 frozen B0 column conflicts")

    def select(rows):
        result = {}
        for row in rows:
            gid = row["group_id"]
            if gid in ids:
                if gid in result:
                    raise ValueError("duplicate target cohort group")
                result[gid] = row
        if result.keys() != ids:
            raise ValueError("target cohort coverage mismatch")
        return result

    targets = select(read_jsonl(read(targets_path)))
    inputs = select(read_jsonl(read(inputs_path)))
    for name in (targets_path, inputs_path, baseline.as_posix()):
        relative = (root / name).resolve().relative_to(root).as_posix()
        if hashes[relative] != boundary["input_sha256"][relative]:
            raise ValueError(f"frozen input SHA mismatch: {relative}")
    details = []
    coverage = Counter()
    summary = {mode: Counter() for mode in ("keep", "exact_prefix")}
    frozen = select(aligned)
    for gid in sorted(ids):
        inp = inputs[gid]
        if inp["split"] != "train_fit" or inp["source_split"] != "train":
            raise ValueError("invalid split")
        prediction = frozen[gid]
        if prediction["status"] == "completed":
            raise ValueError("historical alignment did not fail on this B0 conflict")
        fragments = prediction["diagnostics"]["raw_predictions"]
        if identities(inp["fragments"]) != identities(fragments):
            raise ValueError("fragment identities differ")
        ordered = sorted(fragments, key=lambda row: (row["page_num"], row["part_index"]))
        if any(f["group_id"] != gid or f["status"] != "completed" for f in ordered):
            raise ValueError("unexpected upstream status or group")
        grids = [html_to_grid(f["html"]) for f in ordered]
        target = targets[gid]
        if sorted({f["page_num"] for f in ordered}) != sorted(target["source_pages"]):
            raise ValueError("target pages differ")
        truth = html_to_grid(target["html"])
        widths = [g.n_cols for g in grids]
        totals = Counter(widths)
        modes = sorted(k for k, n in totals.items() if n == max(totals.values()))
        max_width = max(widths)
        n_rows = sum(g.n_rows for g in grids)
        coverage["truth_width_matches_max"] += truth.n_cols == max_width
        coverage["truth_width_matches_unique_mode"] += modes == [truth.n_cols]
        coverage["truth_width_among_modes"] += truth.n_cols in modes
        record = dict(
            group_id=gid,
            fragment_widths=widths,
            fragment_rows=[g.n_rows for g in grids],
            source_pages=target["source_pages"],
            truth_width=truth.n_cols,
            truth_rows=truth.n_rows,
            observed_max_width=max_width,
            observed_modal_widths=modes,
            metrics={},
        )
        details.append(record)
        if truth.n_cols < max_width:
            record["blocked"] = "overwide_fragment_cannot_insert"
        elif truth.n_rows > n_rows:
            record["blocked"] = "missing_rows_cannot_insert"
        elif truth.n_rows < n_rows - sum(
            min(3, grids[0].n_rows - 1, g.n_rows - 1) for g in grids[1:]
        ):
            record["blocked"] = "too_many_rows_for_prefix_budget"
        if "blocked" in record:
            coverage[record["blocked"]] += 1
            continue
        try:
            options = [column_options(g, truth.n_cols, budget=4096) for g in grids]
            record["valid_maps_per_fragment"] = [len(o) for o in options]
            record["metrics"] = {
                mode: match_columns(options, truth, allow_prefix=mode == "exact_prefix")
                for mode in summary
            }
        except OverflowError as error:
            record["blocked"] = str(error)
            coverage["budget_exceeded"] += 1
            continue
        coverage["enumerated"] += 1
        for mode, result in record["metrics"].items():
            count = result["paths"]
            for metric, paths in count.items():
                summary[mode][metric] += paths > 0
                summary[mode][metric + "_paths_ambiguous"] += paths > 1
            summary[mode]["dimensions_without_topology"] += (
                count["dimensions"] > 0 and not count["topology"]
            )
            summary[mode]["topology_without_content"] += (
                count["topology"] > 0 and not count["content"]
            )
    payload = dict(
        n_tables=30,
        split="train_fit",
        scope="truth-width, GT only used as oracle diagnostic",
        coverage=coverage,
        metrics=summary,
        input_sha256=hashes,
        per_group=details,
    )
    output = (root / args.output).resolve()
    output.relative_to(root)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps({key: value for key, value in payload.items() if key != "per_group"}, indent=2)
    )


if __name__ == "__main__":
    main()
