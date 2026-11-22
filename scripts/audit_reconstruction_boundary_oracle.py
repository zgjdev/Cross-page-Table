"""Measure the attainable exact scores of fixed-text boundary edits on train_fit."""

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cptla.reconstruction.alignment_baseline import _expand, _mapping
from cptla.reconstruction.grid import GridError, html_to_grid


@dataclass(frozen=True)
class Row:
    topology: tuple
    text: tuple
    flat_body: bool


def row_views(grid):
    topology = [[] for _ in range(grid.n_rows)]
    texts = [[""] * grid.n_cols for _ in range(grid.n_rows)]
    flat = [True] * grid.n_rows
    for cell in grid.cells:
        height = cell.row_end - cell.row_start
        topology[cell.row_start].append((height, cell.col_start, cell.col_end))
        for index in range(cell.row_start, cell.row_end):
            texts[index][cell.col_start : cell.col_end] = [cell.text] * (
                cell.col_end - cell.col_start
            )
            flat[index] &= height == 1 and not cell.header
    return tuple(Row(tuple(t), tuple(x), f) for t, x, f in zip(topology, texts, flat, strict=True))


def prefix_options(first, current, relaxed):
    yield 0
    for k in range(1, min(3, first.n_rows - 1, current.n_rows - 1) + 1):
        if any(c.row_start < k < c.row_end for c in current.cells):
            continue
        if relaxed:
            yield k
        elif not any(c.row_start < k < c.row_end for c in first.cells):
            reference = tuple(c for c in first.cells if c.row_end <= k)
            prefix = tuple(c for c in current.cells if c.row_end <= k)
            if prefix == reference and any(c.text.strip() for c in prefix):
                yield k


def boundary_oracle(grids, target, *, relaxed=False, allow_merge=False):
    """Count exact topology and joint edit paths without materializing rejected candidates.

    A matched topology can never change under later edits: an optional merge requires
    the exact same single-row cell partition on both sides. Content of the final row
    stays mutable for the next boundary; all earlier rows must already match for joint
    success. Equivalent states retain action-path counts and one representative path.
    """
    if not grids or any(g.n_cols != target.n_cols for g in grids):
        return dict(topology_paths=0, joint_paths=0, example=None, joint_example=None)
    rows = [row_views(g) for g in grids]
    truth = row_views(target)
    if len(rows[0]) > len(truth) or tuple(r.topology for r in rows[0]) != tuple(
        r.topology for r in truth[: len(rows[0])]
    ):
        return dict(topology_paths=0, joint_paths=0, example=None, joint_example=None)

    def content_exact(fragment, offset):
        return all(row.text == truth[index].text for index, row in enumerate(fragment, offset))

    def state(count, last, closed_text_matches):
        return count, last.flat_body, last.text if closed_text_matches else None

    first = rows[0]
    states = {state(len(first), first[-1], content_exact(first[:-1], 0)): (1, ())}
    for grid, fragment in zip(grids[1:], rows[1:], strict=True):
        next_states = {}
        for cut in prefix_options(grids[0], grid, relaxed):
            part = fragment[cut:]
            for (offset, left_flat, text), (count, path) in states.items():
                can_merge = (
                    allow_merge
                    and left_flat
                    and part[0].flat_body
                    and truth[offset - 1].topology == part[0].topology
                )
                for merge in range(int(can_merge) + 1):
                    suffix = part[merge:]
                    end = offset + len(suffix)
                    if end > len(truth) or tuple(r.topology for r in suffix) != tuple(
                        r.topology for r in truth[offset:end]
                    ):
                        continue
                    left_text = text
                    if merge and left_text is not None:
                        left_text = tuple(
                            " ".join(t for t in pair if t)
                            for pair in zip(left_text, part[0].text, strict=True)
                        )
                    if suffix:
                        key = state(
                            end,
                            suffix[-1],
                            left_text == truth[offset - 1].text
                            and content_exact(suffix[:-1], offset),
                        )
                    else:
                        key = (end, left_flat, left_text)
                    total, exemplar = next_states.get(key, (0, path + ((cut, bool(merge)),)))
                    next_states[key] = total + count, exemplar
        states = next_states
    final = [
        (text, count, path) for (n, _, text), (count, path) in states.items() if n == len(truth)
    ]
    joint = [(count, path) for text, count, path in final if text == truth[-1].text]
    return dict(
        topology_paths=sum(count for _, count, _ in final),
        joint_paths=sum(count for count, _ in joint),
        example=final[0][2] if final else None,
        joint_example=joint[0][1] if joint else None,
    )


CATALOGS = {
    "exact_prefix": (False, False),
    "exact_prefix_and_merge": (False, True),
    "span_safe_prefix": (True, False),
    "span_safe_prefix_and_merge": (True, True),
}


def identities(rows):
    return sorted((r["page_num"], r["part_index"], r["fragment_id"]) for r in rows)


def read_jsonl(payload):
    for line in payload.decode("utf-8-sig").split("\n"):
        if line.strip():
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    hashes = {}

    def read(path):
        path = (root / path).resolve()
        key = path.relative_to(root).as_posix()
        data = path.read_bytes()
        hashes[key] = hashlib.sha256(data).hexdigest()
        return data

    baseline = json.loads(read(args.baseline / "predictions.json"))
    historical = json.loads(read(args.baseline / "scores.json"))
    recorded_hashes = json.loads(read(args.baseline / "input-hashes.json"))
    inputs_payload = read(args.inputs)
    targets_payload = read(args.targets)
    target_key = (root / args.targets).resolve().relative_to(root).as_posix()
    if recorded_hashes[target_key] != hashes[target_key]:
        raise ValueError("baseline targets SHA mismatch")
    ids = {row["group_id"] for row in baseline}
    if len(ids) != 200 or len(baseline) != 200:
        raise ValueError("expected frozen 200-table sample")

    def keyed(rows):
        result = {}
        for row in rows:
            gid = row["group_id"]
            if gid not in ids:
                continue
            if gid in result:
                raise ValueError(f"duplicate group {gid}")
            result[gid] = row
        if result.keys() != ids:
            raise ValueError("group coverage mismatch")
        return result

    inputs = keyed(read_jsonl(inputs_payload))
    targets = keyed(read_jsonl(targets_payload))
    scores = keyed(historical["per_group"])
    summary = {key: Counter() for key in CATALOGS}
    coverage = Counter()
    details = []
    for pred in baseline:
        gid = pred["group_id"]
        inp, target = inputs[gid], targets[gid]
        if inp["split"] != "train_fit" or inp["source_split"] != "train":
            raise ValueError(f"unexpected split: {gid}")
        fragments = pred["diagnostics"]["raw_predictions"]
        if identities(fragments) != identities(inp["fragments"]) or any(
            f["group_id"] != gid for f in fragments
        ):
            raise ValueError(f"fragment mismatch: {gid}")
        ordered = sorted(fragments, key=lambda f: (f["page_num"], f["part_index"]))
        if sorted({f["page_num"] for f in ordered}) != sorted(target["source_pages"]):
            raise ValueError(f"target pages mismatch: {gid}")
        row = dict(group_id=gid, n_fragments=len(ordered), catalogs={})
        details.append(row)
        truth = html_to_grid(target["html"])
        try:
            if any(f["status"] != "completed" for f in ordered):
                raise ValueError("incomplete_upstream")
            grids = [html_to_grid(f["html"]) for f in ordered]
            ref = max(grids, key=lambda grid: grid.n_cols)
            grids = [_expand(g, _mapping(g, ref), ref.n_cols)[0] for g in grids]
        except (GridError, ValueError) as error:
            row["failure"] = str(error)
            coverage["upstream_or_alignment_failed"] += 1
            continue
        coverage["aligned"] += 1
        coverage["target_width_matches"] += grids[0].n_cols == truth.n_cols
        for key, (relaxed, merge) in CATALOGS.items():
            result = boundary_oracle(grids, truth, relaxed=relaxed, allow_merge=merge)
            row["catalogs"][key] = result
            c = summary[key]
            c["top_exact"] += result["topology_paths"] > 0
            c["joint_exact"] += result["joint_paths"] > 0
            c["topology_label_ambiguous"] += result["topology_paths"] > 1
            c["joint_label_ambiguous"] += result["joint_paths"] > 1
            c["additional_top_exact"] += (
                result["topology_paths"] > 0 and not scores[gid]["top_exact"]
            )
            c["additional_joint_exact"] += (
                result["joint_paths"] > 0 and not scores[gid]["joint_exact"]
            )
            if scores[gid]["top_exact"] and not result["topology_paths"]:
                raise ValueError(f"catalog dropped an exact historical candidate: {gid} {key}")
    payload = dict(
        created_utc=datetime.now(UTC).isoformat(),
        n_tables=len(ids),
        split="train_fit only",
        protocol="oracle diagnostic; target used only to score boundary action paths",
        coverage=coverage,
        historical_top_exact=sum(row["top_exact"] for row in scores.values()),
        historical_joint_exact=sum(row["joint_exact"] for row in scores.values()),
        catalogs=summary,
        input_sha256=hashes,
        command_config={k: str(v) for k, v in vars(args).items()},
        per_group=details,
    )
    out = (root / args.output).resolve()
    out.relative_to(root)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in payload.items() if k != "per_group"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
