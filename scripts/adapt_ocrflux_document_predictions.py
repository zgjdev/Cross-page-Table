"""Read-only, no-GT conversion of instrumented OCRFlux predictions."""

import argparse
import json
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.document_run import digest, write_new_json


def adapt(manifest, predictions, output):
    if output.exists():
        raise FileExistsError(output)
    hashes = {str(manifest.resolve()): digest(manifest)}
    rows = [json.loads(s) for s in manifest.read_text().splitlines()]
    if any(type(r["page_number"]) is not int or r["page_number"] < 0 for r in rows):
        raise ValueError("Invalid page number")
    rows.sort(key=lambda r: (r["document_id"], r["page_number"]))
    keys = [(r["document_id"], r["page_number"]) for r in rows]
    if not rows or len(set(keys)) != len(keys):
        raise ValueError("Invalid manifest coverage")
    modes = {"no_merge": [], "merged": []}
    coverage, evidence = [], []
    for doc in sorted({r["document_id"] for r in rows}):
        entries = [r for r in rows if r["document_id"] == doc]
        if [r["page_number"] for r in entries] != list(range(len(entries))):
            raise ValueError("Noncontiguous manifest coverage")
        path = predictions / (doc + ".json")
        hashes[str(path.resolve())] = digest(path)
        saved = json.loads(path.read_text())
        if saved["document_id"] != doc or len(saved["pages"]) != len(entries):
            raise ValueError("Prediction page coverage mismatch")
        for entry, page in zip(entries, saved["pages"], strict=True):
            filename = f"{doc}_page_{entry['page_number']}.jpg"
            if (
                entry["unit_id"] != doc
                or entry["image_id"] not in (filename, filename[:-4])
                or entry["relative_path"] != filename
            ):
                raise ValueError("Manifest image identity mismatch")
            record = PredictionRecord(
                image_id=entry["image_id"],
                unit_id=doc,
                status=page["status"],
                error=page.get("error"),
                tables_html=[],
                elapsed_sec=page["elapsed_sec"],
                warnings=page.get("warnings", []),
            )
            coverage.append(record.model_dump())
        for mode in modes:
            ids = set()
            for table in saved[mode]:
                source = table["source_pages"]
                if (
                    table["document_id"] != doc
                    or table["table_id"] in ids
                    or not source
                    or source != sorted(set(source))
                    or any(type(p) is not int or not 0 <= p < len(entries) for p in source)
                    or set(table) != {"document_id", "table_id", "html", "source_pages"}
                ):
                    raise ValueError("Invalid table provenance")
                ids.add(table["table_id"])
                modes[mode].append(table)
        evidence.append({"document_id": doc, "decisions": saved["decisions"]})
    for path, sha in hashes.items():
        if digest(Path(path)) != sha:
            raise ValueError("Input changed during adaptation")
    output.mkdir(parents=True, exist_ok=False)

    def jsonl(path, values):
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            for value in values:
                handle.write(json.dumps(value, ensure_ascii=False) + "\n")

    jsonl(output / "input-manifest.jsonl", rows)
    for mode, tables in modes.items():
        folder = output / mode
        folder.mkdir()
        jsonl(folder / "page-results.jsonl", coverage)
        jsonl(folder / "document-tables.jsonl", tables)
    jsonl(output / "decisions.jsonl", evidence)
    write_new_json(
        output / "audit.json",
        {
            "input_sha256": hashes,
            "pages": len(rows),
            "documents": len(evidence),
            "outputs": {
                str(p.relative_to(output)): digest(p) for p in output.rglob("*") if p.is_file()
            },
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    adapt(args.manifest, args.predictions, args.output_dir)
