"""CPU-only B0 pilot diagnostics from prepared input identities; not formal evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from cptla.reconstruction.baselines import concatenate_group
from cptla.reconstruction.scoring import score_groups


def run(project_root, upstream_run, targets, run_id):
    root = Path(project_root).resolve()

    def inside(base, path):
        resolved = (base / path).resolve()
        if not resolved.is_relative_to(base):
            raise ValueError("path escapes permitted root")
        return resolved

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id):
        raise ValueError("invalid run identifier")
    output = inside(root, Path("artifacts/reconstruction-baselines") / run_id)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def write(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)

    def read(path, expected=None):
        path = inside(root, path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        key = path.relative_to(root).as_posix()
        if (expected is not None and digest != expected) or (
            key in hashes and hashes[key] != digest
        ):
            raise ValueError("input SHA mismatch")
        hashes[key] = digest
        return data

    try:
        upstream = inside(root, Path(upstream_run))
        targets = inside(root, Path(targets))
        write(
            "run-manifest.json",
            dict(
                status="pilot_diagnostic_not_formal",
                baseline="B0_vertical_concat_v1",
                started_utc=datetime.now(UTC).isoformat(),
                argv=sys.argv,
                parameters=dict(upstream_run=str(upstream), targets=str(targets), run=run_id),
                python=platform.python_version(),
                platform=platform.platform(),
                device="cpu",
                code_commit=subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip(),
                implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                training_authorized=False,
                hash_scope=(
                    "source/crop checked against prepared; "
                    "prediction/source JSON snapshotted and reverified"
                ),
            ),
        )
        prepared = json.loads(read(inside(upstream, Path("prepared.json"))))
        summary = json.loads(read(inside(upstream, Path("summary.json"))))
        if prepared.get("status") != "prepared" or summary.get("status") != "completed":
            raise ValueError("upstream is not completed/prepared")
        records = prepared.get("fragments")
        if not isinstance(records, list) or not records:
            raise ValueError("empty or invalid prepared fragments")
        if summary.get("expected") != len(records) or summary.get("completed") != len(records):
            raise ValueError("upstream coverage mismatch")
        expected, predictions = defaultdict(list), defaultdict(list)
        expected_paths, identities = set(), set()
        for record in records:
            group = record["group_id"]
            fid = record["fragment_id"]
            if not isinstance(group, str) or not group or (group, fid) in identities:
                raise ValueError("invalid or duplicate prepared group/fragment")
            identities.add((group, fid))
            crop = inside(upstream, Path(record["crop_relpath"]))
            if crop.name != "crop.png" or not crop.is_relative_to(upstream / "fragments"):
                raise ValueError("invalid crop location")
            prediction_path = crop.parent / "prediction.json"
            if prediction_path in expected_paths:
                raise ValueError("duplicate crop directory")
            expected_paths.add(prediction_path)
            source = json.loads(read(inside(upstream, crop.parent / "source.json")))
            if source != record:
                raise ValueError("prepared/source mismatch")
            read(root / record["image_relpath"], record["image_sha256"])
            read(crop, record["crop_sha256"])
            expected[group].append(record)
            if prediction_path.exists():
                prediction = json.loads(read(inside(upstream, prediction_path)))
                if not isinstance(prediction, dict) or prediction.get("group_id") != group:
                    raise ValueError("prediction group mismatch")
                predictions[group].append(prediction)
        fragments_root = inside(upstream, Path("fragments"))
        actual_paths = set(fragments_root.rglob("prediction.json"))
        extras = sorted(actual_paths - expected_paths)
        for path in extras:
            read(inside(upstream, path))
        target_rows = {}
        for line in read(targets).decode("utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            group = row["group_id"]
            if group in target_rows:
                raise ValueError("duplicate target group")
            target_rows[group] = row
        if not expected.keys() <= target_rows.keys():
            raise ValueError("missing target groups")
        # Selection and ordering come exclusively from the prepared input manifest.
        combined = [
            concatenate_group(group, predictions[group], records)
            for group, records in expected.items()
        ]
        scores = score_groups([target_rows[group] for group in expected], combined)
        write("predictions.json", combined)
        write("scores.json", scores)
        write("input-hashes.json", hashes)
        for path, digest in hashes.items():
            read(root / path, digest)
        if set(fragments_root.rglob("prediction.json")) != actual_paths:
            raise ValueError("prediction inventory changed during scoring")
        artifact_hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.iterdir())
        }
        write(
            "summary.json",
            dict(
                status="completed",
                evaluation_status="pilot_diagnostic_not_formal",
                ended_utc=datetime.now(UTC).isoformat(),
                groups=len(combined),
                failed_groups=sum(row["status"] != "completed" for row in combined),
                extra_prediction_paths=[path.relative_to(root).as_posix() for path in extras],
                missing_prediction_paths=[
                    path.relative_to(root).as_posix()
                    for path in sorted(expected_paths - actual_paths)
                ],
                artifact_hashes=artifact_hashes,
                training_authorized=False,
            ),
        )
    except (Exception, KeyboardInterrupt) as exc:
        write(
            "failure.json",
            dict(
                status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                exception_type=type(exc).__name__,
                ended_utc=datetime.now(UTC).isoformat(),
            ),
        )
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--upstream-run", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    print(run(args.project_root, args.upstream_run, args.targets, args.run))


if __name__ == "__main__":
    main()
