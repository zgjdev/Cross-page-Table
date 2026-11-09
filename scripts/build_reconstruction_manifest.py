"""Build auditable train-only oracle fragment inputs without changing source data."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import PIL

from cptla.reconstruction.audit_bundle import write_audit_bundle
from cptla.reconstruction.data import DATASET_REVISION, scan_training_data
from cptla.reconstruction.sampling import group_and_split, sample_audit_groups


def _json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def _jsonl(path: Path, values: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _git(source: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=source, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build_run(
    project_root: Path,
    output_dir: Path,
    *,
    limit_documents: int | None = None,
    sample_size: int = 200,
    coordinate_size: int = 20,
) -> dict:
    root = project_root.resolve()
    output = output_dir.resolve()
    allowed = root / "artifacts/reconstruction"
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("output must be a new child of project artifacts/reconstruction")
    if not root.is_dir():
        raise NotADirectoryError(root)
    if any(type(n) is not int or n < 0 for n in (sample_size, coordinate_size)):
        raise ValueError("sample sizes must be nonnegative integers")
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1]

    def event(stage: str, **details) -> None:
        value = {"time_utc": _now(), "stage": stage, **details}
        line = json.dumps(value, ensure_ascii=False)
        with (output / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")
        print(line, flush=True)

    try:
        config_path = source / "configs/reconstruction/data-audit-v1.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config["dataset_revision"] != DATASET_REVISION or config["source_split"] != "train":
            raise ValueError("configuration does not match fixed train protocol")
        manifest = {
            "started_utc": _now(),
            "argv": sys.argv,
            "project_root": str(root),
            "output_dir": str(output),
            "config": config,
            "config_sha256": _sha(config_path),
            "limit_documents": limit_documents,
            "sample_size": sample_size,
            "coordinate_size": coordinate_size,
            "python": platform.python_version(),
            "pillow": PIL.__version__,
            "git_commit": _git(source, "rev-parse", "HEAD"),
            "git_status": _git(source, "status", "--porcelain=v1"),
            "input_track": "image-only",
            "gpu_used": False,
            "code_sha256": {
                str(p.relative_to(source)).replace("\\", "/"): _sha(p)
                for p in [
                    Path(__file__).resolve(),
                    *sorted((source / "src/cptla/reconstruction").glob("*.py")),
                ]
            },
        }
        _json(output / "run-manifest.json", manifest)
        event("scan_started")
        data = scan_training_data(root, limit_documents=limit_documents)
        event("scan_completed", documents=len(data["documents"]), groups=len(data["inputs"]))
        grouped = group_and_split(data["documents"], seed=config["seed"])
        event("grouping_completed", **grouped["summary"]["split_counts"])
        assignments = grouped["assignments"]
        assignment_by_doc = {s["document_id"]: s for s in assignments}
        for row in data["inputs"]:
            assignment = assignment_by_doc[row["document_id"]]
            row["split"] = assignment["split"]
            row["cluster_id"] = assignment["cluster_id"]
            row["split_status"] = "provisional_do_not_train"
        input_ids = [r["group_id"] for r in data["inputs"]]
        target_ids = [r["group_id"] for r in data["targets"]]
        if len(set(input_ids)) != len(input_ids) or set(input_ids) != set(target_ids):
            raise ValueError("input/target ID coverage mismatch")
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("duplicate target group")
        sample = sample_audit_groups(
            data["audit"]["profiles"],
            assignments,
            sample_size=sample_size,
            coordinate_size=coordinate_size,
            seed=config["seed"],
        )
        _jsonl(output / "inputs.jsonl", data["inputs"])
        _jsonl(output / "targets.jsonl", data["targets"])
        _jsonl(output / "source-hashes.jsonl", data["source_hashes"])
        _jsonl(output / "splits.jsonl", assignments)
        _jsonl(output / "duplicate-candidates.jsonl", grouped["duplicate_candidates"])
        _jsonl(output / "audit-sample.jsonl", sample["samples"])
        _jsonl(
            output / "coordinate-sample.jsonl",
            [{"group_id": key} for key in sample["coordinate_group_ids"]],
        )
        _jsonl(
            output / "documents.jsonl",
            [{k: v for k, v in d.items() if k != "text"} for d in data["documents"]],
        )
        _json(output / "data-audit.json", data["audit"])
        _json(output / "split-audit.json", grouped["summary"])
        _json(
            output / "sample-design.json",
            {"summary": sample["summary"], "strata": sample["strata"]},
        )
        event("review_started", groups=len(sample["samples"]))
        review = write_audit_bundle(root, output, data["inputs"], data["targets"], sample)
        event("review_completed", **review)
        # Recheck sources before publishing a completed marker. Never touch source bytes.
        for row in data["source_hashes"]:
            path = (root / row["path"]).resolve()
            if not path.is_relative_to(root) or _sha(path) != row["sha256"]:
                raise ValueError(f"source changed during audit: {row['path']}")
        summary = {
            "status": "completed",
            "ended_utc": _now(),
            "scope": "full_train_inventory"
            if limit_documents is None
            else "partial_train_technical_smoke",
            "training_allowed": False,
            "g0_status": "incomplete",
            "g1_status": "not_started",
            "prediction_status": "not_generated",
            "data_audit": {k: v for k, v in data["audit"].items() if k != "profiles"},
            "split_audit": grouped["summary"],
            "sampling": sample["summary"],
            "review": review,
            "coverage": {"missing": 0, "extra": 0, "duplicate": 0},
            "source_hashes_rechecked": len(data["source_hashes"]),
            "pending": [
                "near-duplicate threshold calibration",
                "image duplication audit",
                "cross-official-split audit",
                "coordinate visual review",
                "independent double review",
                "grid/scoring contract",
                "baseline inference",
            ],
        }
        event("integrity_checked", source_hashes_rechecked=len(data["source_hashes"]))
        _json(
            output / "result-hashes.json",
            {
                p.relative_to(output).as_posix(): _sha(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            },
        )
        summary["result_hashes_sha256"] = _sha(output / "result-hashes.json")
        _json(output / "summary.json", summary)
        return summary
    except Exception as error:
        # Keep an unsuccessful run intact; a retry must reserve a new directory.
        _json(
            output / "failure.json",
            {
                "status": "failed",
                "time_utc": _now(),
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit-documents", type=int)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--coordinate-size", type=int, default=20)
    args = parser.parse_args()
    output = (
        args.output_dir if args.output_dir.is_absolute() else args.project_root / args.output_dir
    )
    build_run(
        args.project_root,
        output,
        limit_documents=args.limit_documents,
        sample_size=args.sample_size,
        coordinate_size=args.coordinate_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
