from __future__ import annotations

import csv
from pathlib import Path

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "year",
    "venue",
    "url",
    "task",
    "data",
    "context",
    "modality",
    "method",
    "metrics",
    "code",
    "status",
    "notes",
)


def validate_literature_csv(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            return [f"missing columns: {', '.join(missing)}"]
        seen: set[str] = set()
        for line_no, row in enumerate(reader, start=2):
            paper_id = row["paper_id"].strip()
            if not paper_id:
                errors.append(f"line {line_no}: empty paper_id")
            elif paper_id in seen:
                errors.append(f"line {line_no}: duplicate paper_id {paper_id}")
            seen.add(paper_id)
            if row["status"] not in {"candidate", "screened", "read", "excluded"}:
                errors.append(f"line {line_no}: invalid status {row['status']}")
            if not row["url"].startswith(("https://", "http://")):
                errors.append(f"line {line_no}: invalid url")
    return errors
