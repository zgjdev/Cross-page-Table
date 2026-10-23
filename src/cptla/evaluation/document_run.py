"""Append-only per-document checkpoints with content-verified recovery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def read_frozen_manifest(path, images, expected_sha, expected_pages, expected_documents):
    if digest(path) != expected_sha:
        raise ValueError("Frozen input manifest SHA mismatch")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if len(rows) != expected_pages:
        raise ValueError("Frozen input page count mismatch")
    documents = {}
    seen = set()
    for row in rows:
        doc, number = row["document_id"], row["page_number"]
        if not re.fullmatch(r"PMC[0-9]+", doc) or type(number) is not int or number < 0:
            raise ValueError("Invalid document/page identity")
        filename = f"{doc}_page_{number}.jpg"
        if (
            row["unit_id"] != doc
            or row["relative_path"] != filename
            or row["image_id"] != filename
            or filename in seen
        ):
            raise ValueError("Invalid or duplicate image identity")
        seen.add(filename)
        target = images / filename
        if not target.is_file() or target.stat().st_size < 2:
            raise ValueError(f"Missing source image: {filename}")
        with target.open("rb") as handle:
            if handle.read(2) != b"\xff\xd8":
                raise ValueError(f"Invalid JPEG header: {filename}")
        documents.setdefault(doc, []).append(number)
    if len(documents) != expected_documents:
        raise ValueError("Frozen input document count mismatch")
    for doc, numbers in documents.items():
        if numbers != list(range(len(numbers))):
            raise ValueError(f"Noncontiguous or out-of-order document pages: {doc}")
    return [{"document_id": doc, "pages": len(numbers)} for doc, numbers in documents.items()]


def _verify_result(result, doc, project):
    if result["document_id"] != doc["document_id"] or result["pages"] != doc["pages"]:
        raise ValueError("Checkpoint document coverage mismatch")
    files = result["files"]
    if not files:
        raise ValueError("Checkpoint lacks artifact hashes")
    for path, expected in files.items():
        path = Path(path).resolve()
        if not path.is_relative_to(project.resolve()):
            raise ValueError("Checkpoint artifact outside project")
        if not path.is_file() or digest(path) != expected:
            raise ValueError("Checkpoint artifact SHA mismatch")


def run_batch(documents, output, protocol, worker, *, project, resume=()):
    if output.exists():
        raise FileExistsError(output)
    expected = {d["document_id"]: d for d in documents}
    if not expected or len(expected) != len(documents):
        raise ValueError("Expected unique nonempty document list")
    for doc in documents:
        if (
            not re.fullmatch(r"PMC[0-9]+", doc["document_id"])
            or type(doc["pages"]) is not int
            or doc["pages"] < 1
        ):
            raise ValueError("Invalid document job")
    completed = {}
    for previous in resume:
        previous = previous.resolve()
        if not previous.is_relative_to(project.resolve()):
            raise ValueError("Resume directory outside project")
        previous_manifest = json.loads((previous / "run-manifest.json").read_text())
        if previous_manifest["protocol"] != protocol:
            raise ValueError("Resume protocol differs from current fixed protocol")
        for path in sorted((previous / "checkpoints").glob("*.json")):
            checkpoint = json.loads(path.read_text())
            doc, result = checkpoint["document"], checkpoint["result"]
            identifier = doc["document_id"]
            if (
                identifier not in expected
                or expected[identifier] != doc
                or identifier in completed
                or checkpoint["protocol"] != protocol
            ):
                raise ValueError("Duplicate, out-of-scope or incompatible checkpoint")
            _verify_result(result, doc, project)
            completed[identifier] = result
    resumed = len(completed)
    output.mkdir(parents=True, exist_ok=False)
    (output / "checkpoints").mkdir()
    write_new_json(
        output / "run-manifest.json",
        {"protocol": protocol, "documents": documents, "resume": [str(p) for p in resume]},
    )
    summary = {
        "status": "running",
        "resumed_documents": resumed,
        "expected_documents": len(documents),
        "expected_pages": sum(d["pages"] for d in documents),
    }
    try:
        for doc in documents:
            identifier = doc["document_id"]
            if identifier in completed:
                continue
            result = worker(doc)
            _verify_result(result, doc, project)
            write_new_json(
                output / "checkpoints" / f"{identifier}.json",
                {"protocol": protocol, "document": doc, "result": result},
            )
            completed[identifier] = result
            print(
                json.dumps(
                    {
                        "event": "document_checkpoint",
                        "document": identifier,
                        "completed_documents": len(completed),
                        "expected_documents": len(documents),
                    }
                ),
                flush=True,
            )
        summary["status"] = "completed"
        return summary
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        summary["completed_documents"] = len(completed)
        summary["pages"] = sum(r["pages"] for r in completed.values())
        summary["results"] = completed
        write_new_json(output / "summary.json", summary)
