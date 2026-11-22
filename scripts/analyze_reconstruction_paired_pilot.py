"""从两臂逐表产物生成已知分组短表的配对诊断。"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from cptla.reconstruction.grid import html_to_grid
from cptla.reconstruction.scoring import score_groups


def compare(targets, arms):
    metrics = ("top_exact", "con_exact", "joint_exact")
    result = {"n_tables": len(targets), "transitions": {}, "arms": {}, "per_table": []}
    details = {}
    for arm, predictions in arms.items():
        score = score_groups(targets, predictions)
        if score["extra_prediction_count"]:
            raise ValueError(f"{arm} includes predictions outside the heldout list")
        grouped = defaultdict(list)
        for pred in predictions:
            grouped[pred["group_id"]].append(pred)
        summary = Counter()
        details[arm] = {}
        for target, row in zip(targets, score["per_group"], strict=True):
            group = row["group_id"]
            gt = html_to_grid(target["html"])
            values = grouped[group]
            raw = values[0] if len(values) == 1 else {}
            data = dict(row, status=raw.get("status"), row_delta=None, column_delta=None)
            if row["failure_reason"] is None:
                pred = html_to_grid(raw["html"])
                data.update(row_delta=pred.n_rows - gt.n_rows, column_delta=pred.n_cols - gt.n_cols)
                summary["scorable"] += 1
                summary["row_count_wrong"] += data["row_delta"] != 0
                summary["column_count_wrong"] += data["column_delta"] != 0
            else:
                summary["failed"] += 1
            for metric in metrics:
                summary[metric] += data[metric]
            details[arm][group] = data
        result["arms"][arm] = {
            k: summary[k]
            for k in (*metrics, "scorable", "failed", "row_count_wrong", "column_count_wrong")
        }
    for target in targets:
        group = target["group_id"]
        grid = html_to_grid(target["html"])
        result["per_table"].append(
            dict(
                group_id=group,
                rows=grid.n_rows,
                columns=grid.n_cols,
                **{arm: rows[group] for arm, rows in details.items()},
            )
        )
    for metric in metrics:
        counts = Counter((r["direct"][metric], r["structure"][metric]) for r in result["per_table"])
        result["transitions"][metric] = dict(
            both_correct=counts[True, True],
            improved=counts[False, True],
            regressed=counts[True, False],
            both_wrong=counts[False, False],
        )
    return result


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("direct", "structure", "targets", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    raw = args.targets.read_bytes()
    target_sha = hashlib.sha256(raw).hexdigest()
    manifests = {}
    input_hashes = {}
    predictions = {}
    digests = {}
    for arm, folder in (("direct", args.direct), ("structure", args.structure)):
        manifest = read(folder / "manifest.json")
        config = manifest["config"]
        if config["arm"] != arm or read(folder / "summary.json")["status"] != "completed":
            raise ValueError(f"{arm}: incomplete or wrong arm")
        hashes = read(folder / "input-hashes.json")
        input_hashes[arm] = hashes
        root = Path(config["project_root"]).resolve()
        key = (root / config["targets"]).resolve().relative_to(root).as_posix()
        if hashes.get(key) != target_sha:
            raise ValueError("target hash mismatch")
        manifests[arm] = {
            k: manifest[k]
            for k in (
                "revision",
                "model_revision",
                "train",
                "heldout",
                "documents",
                "track",
                "dtype",
                "seed",
                "commit",
                "lora_rank",
                "lora_alpha",
                "dropout",
                "lr",
                "weight_decay",
            )
        }
        manifests[arm]["config"] = {
            k: v for k, v in config.items() if k not in ("run", "arm", "gpu")
        }
        payload = (folder / "predictions.json").read_bytes()
        predictions[arm] = json.loads(payload)
        digests[arm] = hashlib.sha256(payload).hexdigest()
    if manifests["direct"] != manifests["structure"]:
        raise ValueError("pilot configurations or document splits differ")
    if input_hashes["direct"] != input_hashes["structure"]:
        raise ValueError("pilot inputs differ by SHA256")
    heldout = manifests["direct"]["heldout"]
    rows = [
        r
        for line in raw.decode("utf-8-sig").split("\n")
        if line.strip() and (r := json.loads(line))["group_id"] in heldout
    ]
    truth = {r["group_id"]: r for r in rows}
    if len(rows) != len(truth) or set(truth) != set(heldout) or len(set(heldout)) != len(heldout):
        raise ValueError("target coverage mismatch")
    result = compare([truth[g] for g in heldout], predictions)
    result.update(
        prediction_sha256=digests,
        targets_sha256=target_sha,
        metric_status="project_diagnostic_not_official_accuracy",
    )
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
