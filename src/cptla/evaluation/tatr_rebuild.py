from __future__ import annotations

import json
from pathlib import Path

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.tatr import cells_to_html


def rebuild_tatr_prediction(record: PredictionRecord) -> PredictionRecord:
    """Regenerate TATR HTML from the saved postprocessed cells."""
    if record.status == "error":
        return record
    if record.raw_output is None:
        raise ValueError("successful prediction is missing raw_output.cells")
    try:
        raw = json.loads(record.raw_output)
    except json.JSONDecodeError as error:
        raise ValueError("successful prediction has invalid raw_output.cells") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("cells"), list):
        raise ValueError("successful prediction has invalid raw_output.cells")
    cells = raw["cells"]
    if not all(isinstance(cell, dict) for cell in cells):
        raise ValueError("successful prediction has invalid raw_output.cells")
    html = cells_to_html(cells)
    return record.model_copy(update={"tables_html": [html] if cells else []})


def rebuild_tatr_predictions_jsonl(source: Path, destination: Path) -> dict[str, int]:
    """Stream rebuilt predictions to a new lightweight JSONL file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    summary = {"records": 0, "ok": 0, "error": 0, "tables": 0}
    with source.open("r", encoding="utf-8") as input_stream, destination.open(
        "x", encoding="utf-8", newline="\n"
    ) as output_stream:
        for line_number, line in enumerate(input_stream, start=1):
            if not line.strip():
                continue
            try:
                record = PredictionRecord.model_validate_json(line)
                rebuilt = rebuild_tatr_prediction(record)
            except ValueError as error:
                location = f"{source}:{line_number}"
                raise ValueError(f"invalid prediction at {location}: {error}") from error
            output_stream.write(rebuilt.model_dump_json(exclude={"raw_output"}) + "\n")
            summary["records"] += 1
            summary[rebuilt.status] += 1
            summary["tables"] += len(rebuilt.tables_html)
    return summary
