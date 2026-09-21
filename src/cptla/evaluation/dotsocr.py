from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from json_repair import repair_json

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", flags=re.IGNORECASE)
_TABLE_START = re.compile(r"^<table(?:\s|>)", flags=re.IGNORECASE)


class DuplicatePredictionError(ValueError):
    """Raised when an append-only prediction stream contains repeated image IDs."""


class CorruptPredictionTailError(ValueError):
    """Raised when safe recovery requires a new append-only output shard."""


@dataclass(frozen=True)
class PredictionScan:
    completed_ids: set[str]
    corrupt_tail: bool


def parse_layout(raw: str) -> list[dict[str, object]]:
    cleaned = _FENCE.sub("", raw.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        value = repair_json(cleaned, return_objects=True)

    if isinstance(value, dict):
        for key in ("layouts", "elements", "result", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return _require_layout_objects(nested)
        return [value]
    if isinstance(value, list):
        return _require_layout_objects(value)
    raise ValueError("layout output is neither an object or a list")


def _require_layout_objects(values: list[object]) -> list[dict[str, object]]:
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("layout list contains a non-object element")
    return values  # type: ignore[return-value]


def _is_table_html(value: str) -> bool:
    stripped = value.strip()
    return _TABLE_START.match(stripped) is not None and stripped.lower().endswith("</table>")


def extract_table_html(raw: str) -> tuple[list[str], list[str]]:
    tables: list[str] = []
    warnings: list[str] = []
    for index, element in enumerate(parse_layout(raw)):
        if str(element.get("category", "")).casefold() != "table":
            continue
        html = element.get("text")
        if isinstance(html, str) and _is_table_html(html):
            tables.append(html.strip())
        else:
            warnings.append(f"invalid_table_html:{index}")
    return tables, warnings


def scan_prediction_file(path: Path) -> PredictionScan:
    if not path.exists():
        return PredictionScan(completed_ids=set(), corrupt_tail=False)

    lines = path.read_text(encoding="utf-8").splitlines()
    completed: set[str] = set()
    corrupt_tail = False
    for index, line in enumerate(lines, start=1):
        try:
            record = PredictionRecord.model_validate_json(line)
        except (ValueError, json.JSONDecodeError) as error:
            if index == len(lines):
                corrupt_tail = True
                continue
            raise ValueError(f"invalid prediction JSONL line {index}: {error}") from error
        if record.image_id in completed:
            raise DuplicatePredictionError(f"duplicate prediction image_id: {record.image_id}")
        completed.add(record.image_id)
    return PredictionScan(completed_ids=completed, corrupt_tail=corrupt_tail)


def pending_manifest_entries(
    entries: list[ImageManifestEntry], completed_ids: set[str]
) -> list[ImageManifestEntry]:
    return [entry for entry in entries if entry.image_id not in completed_ids]


def completed_ids_from_files(paths: list[Path]) -> set[str]:
    completed: set[str] = set()
    for path in paths:
        current = scan_prediction_file(path).completed_ids
        overlap = completed & current
        if overlap:
            duplicate = sorted(overlap)[0]
            raise DuplicatePredictionError(f"duplicate prediction image_id: {duplicate}")
        completed.update(current)
    return completed


def require_appendable_output(path: Path) -> set[str]:
    scan = scan_prediction_file(path)
    if scan.corrupt_tail:
        raise CorruptPredictionTailError(
            f"{path} has a corrupt tail; preserve it and use a new --output with "
            f"--resume-from {path}"
        )
    return scan.completed_ids


def append_boundary_needed(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as stream:
        stream.seek(-1, 2)
        return stream.read(1) not in (b"\n", b"\r")
