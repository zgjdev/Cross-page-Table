"""Score frozen boundary-edit weights on the preselected train_dev development pilot."""

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

from cptla.reconstruction.alignment_baseline import BASELINE_ID as ALIGNMENT_ID
from cptla.reconstruction.baselines import concatenate_group
from cptla.reconstruction.boundary_edit import apply_cuts, boundary_candidates, predict_cuts
from cptla.reconstruction.data import DATASET_REVISION
from cptla.reconstruction.grid import grid_to_html, html_to_grid
from cptla.reconstruction.scoring import METRICS, score_groups

MODULE = "src/cptla/reconstruction/boundary_edit.py"


def indexed(records, key, subset=None):
    rows = {}
    for row in records:
        name = row[key]
        if subset is not None and name not in subset:
            continue
        if name in rows:
            raise ValueError(f"duplicate {key}: {name}")
        rows[name] = row
    return rows


def validate_selection(selection, inputs, overlay, seen_docs, seen_clusters):
    if len(selection) != 16:
        raise ValueError("expected locked 16-table scope")
    group_ids = [selection_row["group_id"] for selection_row in selection]
    if len(set(group_ids)) != 16:
        raise ValueError("duplicate group in locked scope")
    docs, clusters = set(), set()
    strata = Counter()
    for planned in selection:
        row = inputs[planned["group_id"]]
        doc = row["document_id"]
        cluster = row["cluster_id"]
        current = overlay.get(doc, {})
        count = len(row["fragments"])
        if (
            doc in docs
            or doc in seen_docs
            or cluster in clusters
            or cluster in seen_clusters
            or planned["document_id"] != doc
            or planned["cluster_id"] != cluster
            or planned["fragments"] != count
            or count < 2
            or row["source_split"] != "train"
            or row["split"] != "train_dev"
            or row["dataset_revision"] != DATASET_REVISION
            or current.get("effective_split") != "train_dev"
            or current.get("cluster_id") != cluster
            or current.get("observed_cluster") is not False
        ):
            raise ValueError(f"locked train_dev scope violation for {planned['group_id']}")
        docs.add(doc)
        clusters.add(cluster)
        strata[min(count, 3)] += 1
    if strata != {2: 8, 3: 8}:
        raise ValueError("locked scope must contain eight tables per stratum")
    return group_ids


def score_summary(groups, inputs, results):
    strata = {
        "all": set(groups),
        "two_fragments": {g for g in groups if len(inputs[g]["fragments"]) == 2},
        "three_plus_fragments": {g for g in groups if len(inputs[g]["fragments"]) >= 3},
    }
    summary = {}
    for name, scope in strata.items():
        control = {r["group_id"]: r for r in results["heuristic"]["per_group"]}
        summary[name] = {}
        for method, score in results.items():
            rows = [r for r in score["per_group"] if r["group_id"] in scope]
            summary[name][method] = dict(
                groups=len(rows),
                scorable=sum(r["failure_reason"] is None for r in rows),
                exact={metric: sum(r[metric] for r in rows) for metric in METRICS},
                topology_improved=sum(
                    r["top_exact"] and not control[r["group_id"]]["top_exact"] for r in rows
                ),
                topology_regressed=sum(
                    not r["top_exact"] and control[r["group_id"]]["top_exact"] for r in rows
                ),
            )
    return summary


def run(args):
    root = args.project_root.resolve()
    if not re.fullmatch(r"\d{8}T\d{6}Z-[A-Za-z0-9_-]+", args.run):
        raise ValueError("expected timestamped run ID")

    def safe(path):
        result = (root / path).resolve()
        if not result.is_relative_to(root):
            raise ValueError("path escapes project")
        return result

    out = safe("artifacts/reconstruction-diagnostics/" + args.run)
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def read(path, expected=None):
        path = safe(path)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        key = path.relative_to(root).as_posix()
        if (expected is not None and expected != sha) or hashes.setdefault(key, sha) != sha:
            raise ValueError(f"SHA mismatch for {key}")
        return data

    def write(name, value):
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)

    # Load hashes of the held-out targets from the baseline receipts, not target contents.
    target_key = safe(args.targets).relative_to(root).as_posix()

    def baseline(path, expected):
        directory = safe(path)
        receipt = json.loads(read(directory / "summary.json"))
        if receipt["status"] != "completed" or receipt["groups"] != 16:
            raise ValueError("expected completed locked-scope baseline")
        if receipt["extra_prediction_paths"] or receipt["missing_prediction_paths"]:
            raise ValueError("baseline artifact coverage mismatch")
        artifact_hashes = receipt["artifact_hashes"]
        meta = json.loads(
            read(directory / "run-manifest.json", artifact_hashes["run-manifest.json"])
        )
        if meta["baseline"] != expected:
            raise ValueError(f"expected baseline {expected}")
        inputs = json.loads(
            read(directory / "input-hashes.json", artifact_hashes["input-hashes.json"])
        )
        payload = read(directory / "predictions.json", artifact_hashes["predictions.json"])
        return indexed(json.loads(payload), "group_id"), inputs

    try:
        fit_root = safe(args.fit_run)
        fit_run = json.loads(read(fit_root / "manifest.json"))
        fit_report = json.loads(read(fit_root / "report.json"))
        fit_split = json.loads(read(fit_root / "split.json"))
        if (
            fit_run["dataset_revision"] != DATASET_REVISION
            or fit_report["n_fit"] + fit_report["n_dev"] != 200
        ):
            raise ValueError("requires completed frozen 200-table CPU pilot")
        previous_commit = fit_run["code_commit"]
        if not re.fullmatch(r"[0-9a-f]{40}", previous_commit):
            raise ValueError("invalid frozen code commit")
        # Refuse evaluation if the feature or edit implementation differs from training.
        subprocess.run(
            ["git", "diff", "--quiet", previous_commit, "--", MODULE], cwd=root, check=True
        )
        frozen_path = fit_root / "weights.json"
        weights = json.loads(read(frozen_path, args.weights_sha256))
        vectors = {
            name: np.asarray(weights[name], dtype=float) for name in ("local", "shared_context")
        }
        for name, size in (("local", 9), ("shared_context", 13)):
            vector = vectors[name]
            if vector.shape != (size,) or not np.isfinite(vector).all():
                raise ValueError(f"invalid frozen {name} weights")
        selection = json.loads(read(args.selection))
        if selection["split"] != "train_dev":
            raise ValueError("invalid locked selection split")
        fit_groups = set(fit_split["fit"]) | set(fit_split["dev"])
        if len(fit_groups) != 200:
            raise ValueError("expected 200 distinct previously observed fit pilot tables")
        raw_inputs = read(args.inputs, selection["input_sha256"])
        input_key = safe(args.inputs).relative_to(root).as_posix()
        if fit_split["input_hashes"][input_key] != hashes[input_key]:
            raise ValueError("input manifest changed since frozen model")
        eval_groups = {r["group_id"] for r in selection["groups"]}
        if eval_groups & fit_groups:
            raise ValueError("train_dev overlaps the previously observed fit pilot")
        inputs = indexed(
            map(json.loads, io.BytesIO(raw_inputs)), "group_id", eval_groups | fit_groups
        )
        overlay = indexed(
            map(json.loads, io.BytesIO(read(args.overlay, selection["overlay_sha256"]))),
            "document_id",
        )
        groups = validate_selection(
            selection["groups"],
            inputs,
            overlay,
            {inputs[g]["document_id"] for g in fit_groups},
            {inputs[g]["cluster_id"] for g in fit_groups},
        )
        direct, direct_hashes = baseline(args.b0, "B0_vertical_concat_v1")
        heuristic, heuristic_hashes = baseline(args.alignment, ALIGNMENT_ID)
        if (
            set(direct) != eval_groups
            or set(heuristic) != eval_groups
            or direct_hashes != heuristic_hashes
        ):
            raise ValueError("baseline scope or shared inputs mismatch")
        target_sha256 = direct_hashes[target_key]
        write(
            "manifest.json",
            dict(
                argv=sys.argv,
                started_utc=datetime.now(UTC).isoformat(),
                dataset_revision=DATASET_REVISION,
                python=platform.python_version(),
                numpy=np.__version__,
                frozen_fit_run=args.fit_run.as_posix(),
                frozen_code_commit=previous_commit,
                frozen_weights_sha256=hashes[frozen_path.relative_to(root).as_posix()],
                split="train_dev via provisional document overlay",
                seed=selection["seed"],
                groups=groups,
                track="image-only fixed Paddle predictions; ranker uses recognized grids",
                fit_pilot_docs_overlap=0,
                fit_pilot_clusters_overlap=0,
                evaluation_only=True,
                gpu=False,
                input_sha256=hashes,
            ),
        )
        predictions = {
            "concat": [direct[g] for g in groups],
            "heuristic": [heuristic[g] for g in groups],
            "fuzzy_largest": [],
            "local": [],
            "shared_context": [],
        }
        for group in groups:
            raw = direct[group]["diagnostics"]["raw_predictions"]
            if (
                any(p["group_id"] != group for p in raw)
                or raw != heuristic[group]["diagnostics"]["raw_predictions"]
            ):
                raise ValueError("baseline per-fragment prediction mismatch")
            expected = inputs[group]["fragments"]
            record = concatenate_group(group, raw, expected)
            pred = {k: record[k] for k in ("group_id", "source_pages", "status", "html")}
            if record["status"] != "completed":
                for name in ("fuzzy_largest", *vectors):
                    predictions[name].append(
                        dict(pred, cuts=None, failures=record["diagnostics"]["failure_reasons"])
                    )
                continue
            ordered = sorted(raw, key=lambda p: (p["page_num"], p["part_index"]))
            grids = [html_to_grid(f["html"]) for f in ordered]
            candidates = boundary_candidates(grids)
            actions = {
                "fuzzy_largest": tuple(max(c.cut for c in options) for options in candidates)
            }
            actions.update(
                {
                    name: predict_cuts(candidates, weights, name == "shared_context")
                    for name, weights in vectors.items()
                }
            )
            for name, cuts in actions.items():
                predictions[name].append(
                    dict(pred, cuts=cuts, html=grid_to_html(apply_cuts(grids, cuts)))
                )
        write("predictions.json", predictions)

        # Until this point, no held-out target payload has been opened or decoded.
        target_rows = indexed(
            map(json.loads, io.BytesIO(read(args.targets, target_sha256))), "group_id", eval_groups
        )
        if set(target_rows) != eval_groups or any(
            target_rows[g]["document_id"] != inputs[g]["document_id"] for g in groups
        ):
            raise ValueError("held-out target identity mismatch")
        results = {
            name: score_groups([target_rows[g] for g in groups], records)
            for name, records in predictions.items()
        }
        write("scores.json", results)
        report = dict(
            status="completed",
            ended_utc=datetime.now(UTC).isoformat(),
            target_sha256=target_sha256,
            group_count=len(groups),
            metrics=score_summary(groups, inputs, results),
            scope="16 preselected train_dev groups; diagnostic, not formal confirmation",
        )
        write("report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as error:
        write("failure.json", dict(error_type=type(error).__name__, error=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "project-root",
        "fit-run",
        "selection",
        "overlay",
        "inputs",
        "targets",
        "b0",
        "alignment",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--weights-sha256", required=True)
    parser.add_argument("--run", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
