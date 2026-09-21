import json
from pathlib import Path

import pytest

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.dotsocr import (
    CorruptPredictionTailError,
    DuplicatePredictionError,
    append_boundary_needed,
    completed_ids_from_files,
    pending_manifest_entries,
    require_appendable_output,
    scan_prediction_file,
)
from cptla.evaluation.pubtables_v2 import ImageManifestEntry


def _entry(image_id: str) -> ImageManifestEntry:
    stem = Path(image_id).stem
    return ImageManifestEntry(
        image_id=image_id,
        relative_path=image_id,
        unit_id=stem,
        document_id=stem.split("_table_", maxsplit=1)[0],
    )


def _record(image_id: str) -> PredictionRecord:
    return PredictionRecord(
        image_id=image_id,
        unit_id=Path(image_id).stem,
        status="ok",
        tables_html=["<table></table>"],
        elapsed_sec=1,
        raw_output='[{"category":"Table","text":"<table></table>"}]',
        warnings=[],
    )


def test_scan_ignores_only_corrupt_tail_and_selects_pending_inputs(tmp_path: Path) -> None:
    output = tmp_path / "predictions.jsonl"
    first = _record("PMC1_table_0.jpg")
    output.write_text(first.model_dump_json() + "\n" + '{"image_id":', encoding="utf-8")

    scan = scan_prediction_file(output)
    pending = pending_manifest_entries(
        [_entry("PMC1_table_0.jpg"), _entry("PMC2_table_0.jpg")], scan.completed_ids
    )

    assert scan.completed_ids == {"PMC1_table_0.jpg"}
    assert scan.corrupt_tail is True
    assert [entry.image_id for entry in pending] == ["PMC2_table_0.jpg"]
    assert append_boundary_needed(output) is True


def test_scan_rejects_duplicate_terminal_records(tmp_path: Path) -> None:
    output = tmp_path / "predictions.jsonl"
    row = _record("PMC1_table_0.jpg").model_dump(mode="json")
    output.write_text(
        json.dumps(row, default=str) + "\n" + json.dumps(row, default=str) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DuplicatePredictionError, match="PMC1_table_0.jpg"):
        scan_prediction_file(output)


def test_scan_rejects_corrupt_nonterminal_line(tmp_path: Path) -> None:
    output = tmp_path / "predictions.jsonl"
    output.write_text(
        '{"broken":\n' + _record("PMC1_table_0.jpg").model_dump_json() + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 1"):
        scan_prediction_file(output)


def test_corrupt_output_requires_a_new_recovery_shard(tmp_path: Path) -> None:
    damaged = tmp_path / "damaged.jsonl"
    damaged.write_text(
        _record("PMC1_table_0.jpg").model_dump_json() + "\n" + '{"image_id":',
        encoding="utf-8",
    )

    with pytest.raises(CorruptPredictionTailError, match="--resume-from"):
        require_appendable_output(damaged)
    assert completed_ids_from_files([damaged]) == {"PMC1_table_0.jpg"}
