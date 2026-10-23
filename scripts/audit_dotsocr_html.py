"""Audit saved dots.ocr HTML without ground truth, scoring or prediction changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from cptla.evaluation.dotsocr import extract_table_html, parse_layout
from cptla.evaluation.html_audit import diagnose_html


def rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, nargs="+", required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--failures", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = {r["image_id"] for r in rows(args.manifest)}
    evidence_path = args.adapter_dir / "table-evidence.jsonl"
    table_path = args.adapter_dir / "document-tables.jsonl"
    evidence = {(r["image_id"], r["layout_element_index"]): r for r in rows(evidence_path)}
    tables = {r["table_id"]: r["html"] for r in rows(table_path)}
    failures = {r["table_id"] for r in rows(args.failures)}
    inputs = [args.manifest, *args.predictions, evidence_path, table_path, args.failures]
    before = {str(p): digest(p) for p in inputs}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    counts = Counter()
    buckets = Counter()
    details = Counter()
    tags = Counter()
    seen = set()
    accepted_ids = set()
    rejected_pages = set()
    failed_pages = set()
    samples = defaultdict(list)
    raw_missing = Counter()
    raw_examples = []
    with (args.output_dir / "table-diagnostics.jsonl").open("x", encoding="utf-8") as output:
        for path in args.predictions:
            for row in rows(path):
                image_id = row["image_id"]
                if image_id in seen or image_id not in manifest:
                    raise ValueError(f"duplicate/extra page: {image_id}")
                seen.add(image_id)
                counts["pages"] += 1
                counts["inference_errors"] += row["status"] == "error"
                counts["runner_warnings"] += len(row["warnings"])
                if row["status"] != "ok":
                    continue
                raw = row["raw_output"]
                extracted, warnings = extract_table_html(raw)
                if extracted != row["tables_html"] or warnings != row["warnings"]:
                    raise ValueError(f"raw output differs from saved extraction: {image_id}")
                layout = parse_layout(raw)
                if any(
                    str(e.get("category", "")).casefold() == "table" and "text" not in e
                    for e in layout
                ):
                    raw_missing["pages"] += 1
                    raw_missing["pages_no_text_in_any_element"] += not any(
                        "text" in e for e in layout
                    )
                    raw_missing["pages_literal_text_key"] += '"text"' in raw
                    raw_missing["pages_table_markup"] += "<table" in raw.lower()
                    try:
                        json.loads(raw)
                        raw_missing["raw_valid_json"] += 1
                    except json.JSONDecodeError as error:
                        raw_missing[f"raw_json_error/{error.msg}"] += 1
                    if len(raw_examples) < 3:
                        raw_examples.append(
                            {
                                "image_id": image_id,
                                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                                "raw_start": raw[:600],
                                "raw_end": raw[-200:],
                            }
                        )
                for index, element in enumerate(layout):
                    if str(element.get("category", "")).casefold() != "table":
                        continue
                    value = element.get("text")
                    record = {"image_id": image_id, "layout_index": index, **diagnose_html(value)}
                    record["layout_keys"] = sorted(element)
                    entry = evidence.get((image_id, index))
                    accepted = entry is not None
                    record["runner_accepted"] = accepted
                    record["table_id"] = entry["table_id"] if accepted else None
                    if accepted:
                        table_id = entry["table_id"]
                        if tables[table_id] != value.strip():
                            raise ValueError(f"adapter differs from raw HTML: {table_id}")
                        accepted_ids.add(table_id)
                        counts["runner_accepted"] += 1
                        record["score_rejected"] = table_id in failures
                        if record["score_rejected"]:
                            failed_pages.add(image_id)
                            counts["score_rejected"] += 1
                            tags.update(record.get("tags", {}))
                        stage = "score_rejected" if record["score_rejected"] else "score_accepted"
                    else:
                        counts["runner_rejected"] += 1
                        rejected_pages.add(image_id)
                        stage = "runner_rejected"
                    kind = (
                        "xml_ok"
                        if record["xml_ok"]
                        else "lexical_candidate"
                        if record["lexical_xml_ok"]
                        else "unresolved"
                    )
                    bucket = f"{stage}/{kind}"
                    record["bucket"] = bucket
                    buckets[bucket] += 1
                    details[f"{stage}/input_type/{record['input_type']}"] += 1
                    details[f"{stage}/xml_error/{record.get('xml_error')}"] += 1
                    details[f"{stage}/table_count/{record.get('table_count')}"] += 1
                    if not accepted:
                        if "text" not in element:
                            details["runner_rejected/missing_text_key"] += 1
                        for key, item in element.items():
                            if key != "text" and isinstance(item, str) and "<table" in item.lower():
                                details[f"runner_rejected/alternative_html/{key}"] += 1
                    sample_bucket = f"{bucket}/{record.get('xml_error')}/{record['input_type']}"
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    if len(samples[sample_bucket]) < 3:
                        samples[sample_bucket].append({**record, "original_html": value})
    if seen != manifest or accepted_ids != set(tables):
        raise ValueError("manifest/adapter coverage mismatch")
    if counts["runner_rejected"] != counts["runner_warnings"]:
        raise ValueError("warning count does not reconcile")
    if counts["score_rejected"] != len(failures):
        raise ValueError("score failures do not reconcile")
    after = {str(p): digest(p) for p in inputs}
    if before != after:
        raise ValueError("input changed during audit")
    with (args.output_dir / "samples.jsonl").open("x", encoding="utf-8") as output:
        for bucket in sorted(samples):
            for sample in samples[bucket]:
                output.write(json.dumps(sample, ensure_ascii=False) + "\n")
    summary = {
        "created_utc": datetime.now(UTC).isoformat(),
        "command": sys.argv,
        "python": platform.python_version(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "counts": dict(counts),
        "buckets": dict(buckets),
        "details": dict(details),
        "missing_text_page_diagnostics": dict(raw_missing),
        "missing_text_raw_examples": raw_examples,
        "pages_runner_rejected": len(rejected_pages),
        "pages_score_rejected": len(failed_pages),
        "pages_both_rejections": len(rejected_pages & failed_pages),
        "score_rejected_tag_counts": dict(tags),
        "inputs_sha256": before,
        "inputs_unchanged": True,
        "sample_policy": "first three per stage/syntax/XML-error/input-type bucket in shard order",
        "limits": "No GT read. Lexical probe is diagnostic, not validated normalization or score.",
        "outputs_sha256": {p.name: digest(p) for p in args.output_dir.iterdir()},
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
