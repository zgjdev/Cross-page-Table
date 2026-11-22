"""Train and score a bounded CPU boundary-action pilot on frozen R0 predictions."""

import argparse
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from cptla.reconstruction.baselines import concatenate_group
from cptla.reconstruction.boundary_edit import (
    MIN_CANDIDATE_SIMILARITY,
    MIN_FRAGMENT_LABEL_SCORE,
    MIN_LABEL_MARGIN,
    apply_cuts,
    boundary_candidates,
    derive_weak_label,
    fit_ranker,
    predict_cuts,
    split_groups,
)
from cptla.reconstruction.data import DATASET_REVISION
from cptla.reconstruction.grid import grid_to_html, html_to_grid
from cptla.reconstruction.scoring import METRICS, score_groups


def _index(rows, groups=None):
    result = {}
    for row in rows:
        key = row["group_id"]
        if groups is not None and key not in groups:
            continue
        if key in result:
            raise ValueError(f"duplicate group: {key}")
        result[key] = row
    return result


def run(args):
    root = args.project_root.resolve()
    if not re.fullmatch(r"\d{8}T\d{6}Z-[A-Za-z0-9_-]+", args.run):
        raise ValueError("expected a timestamped run ID")

    def safe(path):
        result = (root / path).resolve()
        if not result.is_relative_to(root):
            raise ValueError("path escapes project")
        return result

    out = safe("artifacts/reconstruction-diagnostics/" + args.run)
    out.mkdir(parents=True, exist_ok=False)
    digests = {}

    def read(path, expected=None):
        path = safe(path)
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        key = path.relative_to(root).as_posix()
        if (expected is not None and expected != sha) or digests.setdefault(key, sha) != sha:
            raise ValueError(f"input hash mismatch: {key}")
        return raw

    def write(name, obj):
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(obj, stream, indent=2, ensure_ascii=False, allow_nan=False)

    def load_baseline(path):
        base = safe(path)
        meta = json.loads(read(base / "summary.json"))
        if meta["status"] != "completed" or meta["groups"] != 200:
            raise ValueError("requires completed fixed 200-table baseline")
        artifacts = meta["artifact_hashes"]
        input_hashes = json.loads(read(base / "input-hashes.json", artifacts["input-hashes.json"]))
        target_key = safe(args.targets).relative_to(root).as_posix()
        read(args.targets, input_hashes[target_key])
        return _index(json.loads(read(base / "predictions.json", artifacts["predictions.json"])))

    try:
        write(
            "manifest.json",
            dict(
                argv=sys.argv,
                started_utc=datetime.now(UTC).isoformat(),
                code_commit=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=root, text=True
                ).strip(),
                python=platform.python_version(),
                numpy=np.__version__,
                split="internal fit / internal held-out clusters within provisional train_fit",
                dataset_revision=DATASET_REVISION,
                seed=args.seed,
                track="image-only fixed Paddle predictions; ranker uses recognized grids",
                architecture="conditional linear softmax with L2 regularization; 400 CPU steps",
                min_candidate_similarity=MIN_CANDIDATE_SIMILARITY,
                min_fragment_label_score=MIN_FRAGMENT_LABEL_SCORE,
                min_label_margin=MIN_LABEL_MARGIN,
                gpu=False,
                formal_training_authorized=False,
            ),
        )
        b0 = load_baseline(args.b0)
        heuristic = load_baseline(args.alignment)
        if len(b0) != 200 or set(b0) != set(heuristic):
            raise ValueError("fixed pilot scope mismatch")
        inputs = _index(map(json.loads, io.BytesIO(read(args.inputs))), set(b0))
        targets = _index(map(json.loads, io.BytesIO(read(args.targets))), set(b0))
        if set(inputs) != set(b0) or set(targets) != set(b0):
            raise ValueError("baseline and manifest coverage mismatch")
        fit, dev = split_groups(inputs.values(), args.seed)
        for gid, row in inputs.items():
            if (
                row["source_split"] != "train"
                or row["split"] != "train_fit"
                or row["dataset_revision"] != DATASET_REVISION
                or row["document_id"] != targets[gid]["document_id"]
            ):
                raise ValueError(f"unexpected split, version or document: {gid}")
        write("split.json", dict(fit=fit, dev=dev, input_hashes=digests))

        grids, candidates, identity_predictions = {}, {}, {}
        for g in [*fit, *dev]:
            raw = sorted(
                b0[g]["diagnostics"]["raw_predictions"],
                key=lambda p: (p["page_num"], p["part_index"]),
            )
            identity_predictions[g] = concatenate_group(g, raw, inputs[g]["fragments"])
            if identity_predictions[g]["status"] != "completed":
                continue
            grids[g] = [html_to_grid(p["html"]) for p in raw]
            candidates[g] = boundary_candidates(grids[g])

        def weak_label(g):
            if g not in grids or set(identity_predictions[g]["source_pages"]) != set(
                targets[g]["source_pages"]
            ):
                return None
            return derive_weak_label(grids[g], candidates[g], html_to_grid(targets[g]["html"]))

        fit_labels = {g: label for g in fit if (label := weak_label(g)) is not None}
        examples = [
            (options, next(i for i, c in enumerate(options) if c.cut == chosen))
            for g, label in fit_labels.items()
            for options, chosen in zip(candidates[g], label["cuts"], strict=True)
            if len(options) > 1
        ]
        model_weights = {
            name: fit_ranker(examples, context)
            for name, context in (("local", False), ("shared_context", True))
        }
        write("weights.json", {k: v.tolist() for k, v in model_weights.items()})
        predicted_cuts = {}
        predictions = {"concat": [b0[g] for g in dev], "heuristic": [heuristic[g] for g in dev]}
        for name, weights in model_weights.items():
            predicted_cuts[name] = {
                g: predict_cuts(candidates[g], weights, name == "shared_context")
                for g in dev
                if g in candidates
            }
            scored_rows = []
            for g in dev:
                record = identity_predictions[g]
                pred = {k: record[k] for k in ("group_id", "source_pages", "status", "html")}
                if g in grids:
                    pred["html"] = grid_to_html(apply_cuts(grids[g], predicted_cuts[name][g]))
                    pred["cuts"] = predicted_cuts[name][g]
                scored_rows.append(pred)
            predictions[name] = scored_rows
        write("predictions.json", predictions)

        # Evaluate all held-out tables. Weak labels are derived for this split only after inference.
        dev_labels = {g: label for g in dev if (label := weak_label(g)) is not None}
        scores = {
            name: score_groups([targets[g] for g in dev], preds)
            for name, preds in predictions.items()
        }
        baseline = scores["heuristic"]["per_group"]
        metrics = {}
        for name, result in scores.items():
            paired = list(zip(baseline, result["per_group"], strict=True))
            metrics[name] = dict(
                n_tables=len(dev),
                scorable=sum(r["failure_reason"] is None for r in result["per_group"]),
                exact={metric: sum(r[metric] for r in result["per_group"]) for metric in METRICS},
                transitions_vs_heuristic={
                    metric: dict(
                        improved=sum((not a[metric]) and b[metric] for a, b in paired),
                        regressed=sum(a[metric] and (not b[metric]) for a, b in paired),
                    )
                    for metric in ("top_exact", "con_exact")
                },
            )
            if name in predicted_cuts:
                decisions = [
                    (cut, label)
                    for g in dev_labels
                    for cut, label, options in zip(
                        predicted_cuts[name][g], dev_labels[g]["cuts"], candidates[g], strict=True
                    )
                    if len(options) > 1
                ]
                metrics[name]["heldout_weak_labels"] = dict(
                    total=len(decisions),
                    correct=sum(a == b for a, b in decisions),
                    predicted_deletion=sum(a > 0 for a, _ in decisions),
                    labelled_deletion=sum(b > 0 for _, b in decisions),
                )
        report = dict(
            scope="200 fixed upstream groups; score all held-out groups, including failures",
            n_fit=len(fit),
            n_dev=len(dev),
            fit_weak_label_groups=len(fit_labels),
            dev_weak_label_groups=len(dev_labels),
            fit_actions=dict(Counter(candidates[winner].cut for candidates, winner in examples)),
            reviewers=0,
            labels_status="unreviewed weak labels; agreement is not probability of correctness",
            pilot_limits="equal-width prefix deletion only; no boundary merge or cell rewriting",
            metrics=metrics,
            ended_utc=datetime.now(UTC).isoformat(),
        )
        write("weak-labels.json", dict(fit=fit_labels, dev=dev_labels))
        write("scores.json", scores)
        write("report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as error:
        write("failure.json", dict(error_type=type(error).__name__, error=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--seed", type=int, default=20261123)
    for name in ("inputs", "targets", "b0", "alignment"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
