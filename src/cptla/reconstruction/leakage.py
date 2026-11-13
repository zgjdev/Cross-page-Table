"""Read-only exact normalized table-text overlap audit; never a training gate."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

REVISION = "aa575e798cb00a296925e2086addb3e3fd9a1903"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe(root, path):
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("path escapes project root")
    return resolved


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []

    def handle_data(self, data):
        self.chunks.append(data)


def _canonical(html):
    parser = _Text()
    parser.feed(html)
    parser.close()
    return " ".join(unicodedata.normalize("NFKC", " ".join(parser.chunks)).split())


def audit_leakage(project_root: Path, run: str, *, official_splits=False, splits_path=None):
    root = Path(project_root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run):
        raise ValueError("invalid run identifier")
    output = _safe(root, root / "artifacts/reconstruction-leakage" / run)
    output.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        with (output / name).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
            ).stdout.strip()
            or "unknown"
        )
        write(
            "run-manifest.json",
            {
                "dataset_revision": REVISION,
                "code_commit": commit,
                "implementation_sha256": _sha(Path(__file__).read_bytes()),
                "started_utc": datetime.now(UTC).isoformat(),
                "python": platform.python_version(),
                "parameters": {
                    "run": run,
                    "official_splits": official_splits,
                    "splits_path": str(splits_path) if splits_path else None,
                },
                "normalization": "v1: HTML data chunks, NFKC, whitespace collapse; case preserved",
                "document_scope": "ordered table text only, not full article text",
                "training_authorized": False,
                "argv": sys.argv,
                "actual_splits": ["train", "val", "test"] if official_splits else ["train"],
            },
        )
        assignments = {}
        sources = []
        if splits_path:
            path = _safe(root, root / splits_path)
            raw = path.read_bytes()
            sources.append({"path": path.relative_to(root).as_posix(), "sha256": _sha(raw)})
            for line in raw.decode("utf-8-sig").splitlines():
                row = json.loads(line)
                doc, split = row["document_id"], row["split"]
                if doc in assignments or split not in {"train_fit", "train_dev", "train_confirm"}:
                    raise ValueError("invalid or repeated provisional assignment")
                assignments[doc] = split
        tables, documents = defaultdict(list), defaultdict(list)
        counts = {"documents": 0, "tables": 0, "empty_tables": 0, "empty_documents": 0}
        seen_train = set()
        counts_by_split = {}
        for split in ("train", "val", "test") if official_splits else ("train",):
            before = counts.copy()
            expected = root / "data/pubtables-v2/extracted/Full Documents" / split / "tables"
            directory = _safe(root, expected)
            if directory != expected:
                raise ValueError("split directory is redirected")
            if not directory.is_dir():
                raise FileNotFoundError("required split tables directory missing")
            paths = sorted(directory.iterdir())
            if not paths:
                raise ValueError("empty annotation directory")
            for path in paths:
                match = re.fullmatch(r"(PMC[0-9]+)_tables.json", path.name)
                if not match:
                    raise ValueError("unexpected annotation filename")
                path = _safe(directory, path)
                raw = path.read_bytes()
                sources.append({"path": path.relative_to(root).as_posix(), "sha256": _sha(raw)})
                rows = json.loads(raw)
                if not isinstance(rows, list):
                    raise ValueError("annotation must be list")
                doc = match[1]
                if split == "train":
                    seen_train.add(doc)
                identity = {
                    "document_id": doc,
                    "official_split": split,
                    "provisional_split": assignments.get(doc) if split == "train" else None,
                }
                texts = []
                for index, row in enumerate(rows):
                    if not isinstance(row, dict) or not isinstance(row.get("html"), str):
                        raise ValueError("invalid table HTML field")
                    text = _canonical(row["html"])
                    texts.append(text)
                    counts["tables"] += 1
                    counts["empty_tables"] += not bool(text)
                    if text:
                        tables[_sha(text.encode())].append({**identity, "table_index": index})
                counts["documents"] += 1
                counts["empty_documents"] += not any(texts)
                if any(texts):
                    documents[_sha(json.dumps(texts, ensure_ascii=False).encode())].append(identity)
            counts_by_split[split] = {key: counts[key] - before[key] for key in counts}
        if splits_path and set(assignments) != seen_train:
            raise ValueError("assignment coverage mismatch")
        if set(assignments) - seen_train:
            raise ValueError("assignment document absent from train")

        def groups(mapping):
            return [
                {
                    "sha256": key,
                    "members": members,
                    "cross_official_split": len({m["official_split"] for m in members}) > 1,
                    "cross_provisional_split": len(
                        {m["provisional_split"] for m in members if m["provisional_split"]}
                    )
                    > 1,
                }
                for key, members in sorted(mapping.items())
                if len(members) > 1
            ]

        table_groups, document_groups = groups(tables), groups(documents)
        write("source-hashes.json", sources)
        write("overlaps.json", {"tables": table_groups, "documents": document_groups})
        write(
            "pending.json",
            {
                "pending": ["近重复与图像污染未核验", "独立人工审计未完成", "基座预训练污染未知"],
                "split_changes": False,
            },
        )
        for source in sources:
            path = _safe(root, root / source["path"])
            if _sha(path.read_bytes()) != source["sha256"]:
                raise ValueError("source changed during audit")
        artifact_hashes = {path.name: _sha(path.read_bytes()) for path in sorted(output.iterdir())}
        write(
            "summary.json",
            {
                **counts,
                "status": "completed_exact_text_only",
                "table_duplicate_groups": len(table_groups),
                "document_duplicate_groups": len(document_groups),
                "unassigned_train_documents": len(seen_train - assignments.keys()),
                "counts_by_split": counts_by_split,
                "ended_utc": datetime.now(UTC).isoformat(),
                "artifact_hashes": artifact_hashes,
                "training_authorized": False,
            },
        )
    except Exception as exc:
        write(
            "failure.json",
            {
                "status": "failed",
                "exception_type": type(exc).__name__,
                "ended_utc": datetime.now(UTC).isoformat(),
            },
        )
        raise
    return output
