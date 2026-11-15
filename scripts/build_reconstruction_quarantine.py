"""生成只追加的整文档污染隔离层，原始split/官方评估分母不变。"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from cptla.reconstruction.quarantine import quarantine_splits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--splits", required=True)
    p.add_argument("--overlap-run", required=True)
    p.add_argument("--observed-sample", required=True)
    p.add_argument("--run", required=True)
    args = p.parse_args()
    root = args.project_root.resolve()
    hashes = {}

    def path(name):
        value = (root / name).resolve()
        if not value.is_relative_to(root):
            raise ValueError("path escapes root")
        return value

    def read(name, expected=None):
        file = path(name)
        raw = file.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        key = file.relative_to(root).as_posix()
        if (expected and digest != expected) or (key in hashes and hashes[key] != digest):
            raise ValueError("source SHA changed")
        hashes[key] = digest
        return raw.decode("utf-8-sig")

    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z(?:-[A-Za-z0-9_-]+)?", args.run):
        raise ValueError("timestamp run required")
    output = path("artifacts/reconstruction-quarantine/" + args.run)
    output.mkdir(parents=True, exist_ok=False)
    audit = path(args.overlap_run)
    summary = json.loads(read(audit / "summary.json"))
    if summary["status"] != "completed_exact_text_only":
        raise ValueError("exact audit not completed")
    overlaps = json.loads(
        read(audit / "overlaps.json", summary["artifact_hashes"]["overlaps.json"])
    )
    splits = [json.loads(line) for line in read(args.splits).split("\n") if line.strip()]
    observed = {
        json.loads(line)["document_id"]
        for line in read(args.observed_sample).split("\n")
        if line.strip()
    }
    rows = quarantine_splits(splits, overlaps, observed)
    with (output / "document-overlay.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    for name, digest in list(hashes.items()):
        read(name, digest)
    report = dict(
        status="completed_provisional_overlay",
        coverage=dict(expected=len(splits), completed=len(rows), missing=0, extra=0, duplicate=0),
        counts=dict(Counter(row["effective_split"] for row in rows)),
        quarantined_documents=[
            r["document_id"] for r in rows if r["effective_split"] == "quarantine"
        ],
        observed_documents=len(observed),
        source_hashes=hashes,
        overlay_sha256=hashlib.sha256((output / "document-overlay.jsonl").read_bytes()).hexdigest(),
        original_splits_modified=False,
        official_evaluation_denominator_changed=False,
        training_authorized=False,
        argv=sys.argv,
        code_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        ended_utc=datetime.now(UTC).isoformat(),
        limitations=(
            "Exact overlaps only; visual near-duplicate calibration "
            "and research gates remain pending."
        ),
    )
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
