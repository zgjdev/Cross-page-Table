"""CPU-only, auditable three-condition Paddle document adaptation (no GT inputs)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from cptla.evaluation.paddle_document import (
    OFFICIAL_MERGE_SHA256,
    adapt_document,
    load_official_merger,
    remerge_document,
)


def adapt_run(inputs, predictions, official_source, output):
    if output.exists():
        raise FileExistsError(output)
    hashes = {}

    def read(path):
        blob = path.read_bytes()
        hashes[str(path.resolve())] = hashlib.sha256(blob).hexdigest()
        return blob

    manifest = json.loads(read(inputs / "packing-manifest.json"))
    coverage_rows = [json.loads(s) for s in read(inputs / "input-manifest.jsonl").splitlines()]
    run_summary = json.loads(read(predictions / "summary.json"))
    raw_rows = [json.loads(s) for s in read(predictions / "pages.jsonl").splitlines()]
    if run_summary["status"] != "completed" or run_summary["pages"] != len(coverage_rows):
        raise ValueError("Require a complete original inference run")
    expected = [(r["document_id"], r["page_number"]) for r in coverage_rows]
    actual = [(r["document_id"], r["prediction"]["res"]["page_index"]) for r in raw_rows]
    if actual != expected or len(set(expected)) != len(expected):
        raise ValueError("Original page coverage/order mismatch")
    if len({r["image_id"] for r in coverage_rows}) != len(expected):
        raise ValueError("Duplicate manifest image IDs")
    page_results = []
    for row in coverage_rows:
        if row["unit_id"] != row["document_id"]:
            raise ValueError("Manifest unit/document mismatch")
        page_results.append(
            {
                "image_id": row["image_id"],
                "unit_id": row["unit_id"],
                "status": "ok",
                "tables_html": [],
                "elapsed_sec": 0.0,
                "warnings": ["coverage_only_elapsed_not_recorded"],
            }
        )
    read(official_source)
    merger = load_official_merger(official_source)
    modes = {
        name: {"tables": [], "evidence": [], "restructured": {}}
        for name in ("no_merge", "native_merge_official", "native_merge_content_compat")
    }
    documents = []
    for doc in manifest["pdfs"]:
        identifier = doc["document_id"]
        if not re.fullmatch(r"PMC[0-9]+", identifier) or identifier in documents:
            raise ValueError("Invalid/duplicate document ID")
        documents.append(identifier)
        entries = [r for r in coverage_rows if r["document_id"] == identifier]
        if [r["page_number"] for r in entries] != list(range(doc["pages"])):
            raise ValueError("Manifest document coverage mismatch")
        original = json.loads(read(predictions / identifier / "no_merge.json"))
        official = json.loads(read(predictions / identifier / "native_merge.json"))
        if remerge_document(original, merger) != official:
            raise ValueError("Official replay differs from saved native_merge")
        compat = remerge_document(original, merger, content_compat=True)
        for mode, pages in [
            ("no_merge", original),
            ("native_merge_official", official),
            ("native_merge_content_compat", compat),
        ]:
            tables, evidence = adapt_document(pages, identifier, doc["pages"])
            modes[mode]["tables"].extend(tables)
            modes[mode]["evidence"].extend(evidence)
            modes[mode]["restructured"][identifier] = pages
    if set(documents) != {r["document_id"] for r in coverage_rows}:
        raise ValueError("PDF documents do not match original coverage")
    for path, digest in hashes.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError("Input changed during adaptation")
    output.mkdir(parents=True, exist_ok=False)
    outputs = {}

    def write(path, value, jsonl=False):
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            if jsonl:
                for row in value:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                json.dump(value, handle, ensure_ascii=False, indent=2)
        outputs[str(path.relative_to(output))] = hashlib.sha256(path.read_bytes()).hexdigest()

    write(output / "input-manifest.jsonl", coverage_rows, True)
    for mode, bundle in modes.items():
        folder = output / mode
        folder.mkdir()
        write(folder / "page-results.jsonl", page_results, True)
        write(folder / "document-tables.jsonl", bundle["tables"], True)
        write(folder / "table-evidence.jsonl", bundle["evidence"], True)
        for doc, pages in bundle["restructured"].items():
            write(folder / f"{doc}.json", pages)
    summary = {
        "status": "completed",
        "expected_pages": len(expected),
        "pages": len(actual),
        "missing": 0,
        "extra": 0,
        "duplicates": 0,
        "documents": documents,
        "official_replay": "identical",
        "input_hashes": hashes,
        "output_hashes": outputs,
        "official_merge_source_sha256": OFFICIAL_MERGE_SHA256,
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "coverage_elapsed": "0 is an unknown sentinel, not measured runtime",
        "modes": {
            mode: {
                "tables": len(b["tables"]),
                "multisource_tables": sum(len(t["source_pages"]) > 1 for t in b["tables"]),
            }
            for mode, b in modes.items()
        },
    }
    write(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--official-merge-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    if any(
        not path.resolve().is_relative_to(root)
        for path in (args.inputs, args.predictions, args.official_merge_source, args.output_dir)
    ):
        parser.error("All paths must be inside the current project")
    print(
        json.dumps(
            adapt_run(args.inputs, args.predictions, args.official_merge_source, args.output_dir)
        )
    )


if __name__ == "__main__":
    main()
