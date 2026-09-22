import json
from pathlib import Path

import pytest

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.tatr_rebuild import (
    rebuild_tatr_prediction,
    rebuild_tatr_predictions_jsonl,
)


def _ok_record(cells: list[dict[str, object]]) -> PredictionRecord:
    return PredictionRecord(
        image_id="PMC1_table_0.jpg",
        unit_id="PMC1_table_0",
        status="ok",
        tables_html=["<table><thead><th>old</th></thead></table>"],
        elapsed_sec=1.25,
        raw_output=json.dumps({"cells": cells}),
        warnings=["kept"],
    )


def test_rebuild_tatr_prediction_regenerates_standard_html_and_preserves_metadata() -> None:
    record = _ok_record(
        [
            {"row_nums": [0], "column_nums": [0], "cell_text": "H", "header": True},
            {"row_nums": [1], "column_nums": [0], "cell_text": "A", "header": False},
        ]
    )

    rebuilt = rebuild_tatr_prediction(record)

    assert rebuilt.tables_html == [
        "<table><thead><tr><th>H</th></tr></thead>"
        "<tbody><tr><td>A</td></tr></tbody></table>"
    ]
    assert rebuilt.image_id == record.image_id
    assert rebuilt.unit_id == record.unit_id
    assert rebuilt.status == record.status
    assert rebuilt.elapsed_sec == record.elapsed_sec
    assert rebuilt.warnings == ["kept"]
    assert rebuilt.raw_output == record.raw_output


def test_rebuild_tatr_prediction_preserves_error_and_empty_cell_records() -> None:
    failed = PredictionRecord(
        image_id="failed.jpg",
        unit_id="failed",
        status="error",
        tables_html=[],
        elapsed_sec=0.5,
        error="ValueError: failed",
    )
    empty = _ok_record([])

    assert rebuild_tatr_prediction(failed) == failed
    assert rebuild_tatr_prediction(empty).tables_html == []


@pytest.mark.parametrize("raw_output", [None, "{}", "[]", '{"cells": "not-a-list"}'])
def test_rebuild_tatr_prediction_rejects_missing_or_invalid_cells(
    raw_output: str | None,
) -> None:
    record = _ok_record([]).model_copy(update={"raw_output": raw_output})

    with pytest.raises(ValueError, match="raw_output.cells"):
        rebuild_tatr_prediction(record)


def test_rebuild_tatr_predictions_jsonl_streams_lightweight_records(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    destination = tmp_path / "rebuilt.jsonl"
    records = [
        _ok_record(
            [{"row_nums": [0], "column_nums": [0], "cell_text": "H", "header": True}]
        ),
        PredictionRecord(
            image_id="failed.jpg",
            unit_id="failed",
            status="error",
            tables_html=[],
            elapsed_sec=0.5,
            error="ValueError: failed",
        ),
    ]
    source.write_text(
        "".join(record.model_dump_json() + "\n" for record in records),
        encoding="utf-8",
    )

    summary = rebuild_tatr_predictions_jsonl(source, destination)

    rows = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
    assert summary == {"records": 2, "ok": 1, "error": 1, "tables": 1}
    assert [row["image_id"] for row in rows] == ["PMC1_table_0.jpg", "failed.jpg"]
    assert all("raw_output" not in row for row in rows)
    assert rows[0]["tables_html"] == ["<table><thead><tr><th>H</th></tr></thead></table>"]


def test_rebuild_tatr_predictions_jsonl_refuses_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    destination = tmp_path / "rebuilt.jsonl"
    source.write_text(_ok_record([]).model_dump_json() + "\n", encoding="utf-8")
    destination.write_text("do not overwrite\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        rebuild_tatr_predictions_jsonl(source, destination)

    assert destination.read_text(encoding="utf-8") == "do not overwrite\n"
