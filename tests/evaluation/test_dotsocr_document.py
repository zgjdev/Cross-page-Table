import json
import sys
from pathlib import Path

import pytest

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.dotsocr_document import adapt_unmerged_dotsocr
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import IncompleteCoverageError
from scripts.adapt_dotsocr_document_predictions import main

HTML = "<table><tr><td>A</td></tr></table>"


def entry(page: int) -> ImageManifestEntry:
    image_id = f"PMC1_page_{page}.jpg"
    return ImageManifestEntry(
        image_id=image_id,
        relative_path=image_id,
        unit_id="PMC1",
        document_id="PMC1",
        page_number=page,
    )


def record(page: int, layouts: list[dict] | None = None) -> PredictionRecord:
    image_id = entry(page).image_id
    layouts = layouts or []
    return PredictionRecord(
        image_id=image_id,
        unit_id="PMC1",
        status="ok",
        tables_html=[item["text"] for item in layouts if item["category"] == "Table"],
        raw_output=json.dumps(layouts),
        elapsed_sec=0,
    )


def test_unmerged_tables_trace_to_distinct_pages_and_layout_items():
    layout = [
        {"category": "Text", "text": "intro"},
        {"category": "Table", "text": HTML, "bbox": [1, 2, 3, 4]},
        {"category": "Table", "text": HTML, "bbox": [5, 6, 7, 8]},
    ]
    pages, tables, evidence, summary = adapt_unmerged_dotsocr(
        [entry(0), entry(1), entry(2)],
        [record(2), record(1, layout), record(0)],
    )
    assert [row.image_id for row in pages] == [entry(i).image_id for i in range(3)]
    assert all(row.tables_html == [] and row.raw_output is None for row in pages)
    assert [row.table_id for row in tables] == ["PMC1-page-1-table-0", "PMC1-page-1-table-1"]
    assert [row.source_pages for row in tables] == [[1], [1]]
    assert [row["layout_element_index"] for row in evidence] == [1, 2]
    assert evidence[0]["bbox_as_provided"] == [1, 2, 3, 4]
    assert evidence[0]["raw_output_sha256"] == evidence[1]["raw_output_sha256"]
    assert summary["counts"]["document_tables"] == 2
    assert summary["coverage"]["is_complete"] is True


def test_error_page_and_invalid_table_warning_are_preserved():
    failed = PredictionRecord(
        image_id=entry(0).image_id,
        unit_id="PMC1",
        status="error",
        tables_html=[],
        elapsed_sec=0,
        error="OOM",
    )
    invalid = PredictionRecord(
        image_id=entry(1).image_id,
        unit_id="PMC1",
        status="ok",
        tables_html=[],
        elapsed_sec=0,
        raw_output='[{"category":"Table","text":"bad"}]',
        warnings=["invalid_table_html:0"],
    )
    pages, tables, evidence, summary = adapt_unmerged_dotsocr(
        [entry(0), entry(1)], [failed, invalid]
    )
    assert not tables and not evidence
    assert [row.status for row in pages] == ["error", "ok"]
    assert summary["counts"]["inference_errors"] == 1
    assert summary["counts"]["runner_warnings"] == 1


def test_manifest_and_prediction_gates():
    with pytest.raises(IncompleteCoverageError):
        adapt_unmerged_dotsocr([entry(0), entry(1)], [record(0)])
    _, _, _, summary = adapt_unmerged_dotsocr(
        [entry(0), entry(1)], [record(0)], require_complete=False
    )
    assert summary["coverage"]["missing"] == [entry(1).image_id]
    with pytest.raises(ValueError, match="duplicate input"):
        adapt_unmerged_dotsocr([entry(0)], [record(0), record(0)])
    with pytest.raises(ValueError, match="outside manifest"):
        adapt_unmerged_dotsocr([entry(0)], [record(0), record(2)])
    with pytest.raises(ValueError, match="unit mismatch"):
        adapt_unmerged_dotsocr([entry(0)], [record(0).model_copy(update={"unit_id": "PMC2"})])
    with pytest.raises(ValueError, match="duplicate document/page"):
        adapt_unmerged_dotsocr([entry(0), entry(0).model_copy(update={"image_id": "x.jpg"})], [])


def test_raw_output_is_required_for_table_provenance():
    row = record(0, [{"category": "Table", "text": HTML}])
    with pytest.raises(ValueError, match="requires raw_output"):
        adapt_unmerged_dotsocr([entry(0)], [row.model_copy(update={"raw_output": None})])
    with pytest.raises(ValueError, match="differs"):
        adapt_unmerged_dotsocr([entry(0)], [row.model_copy(update={"tables_html": []})])
    with pytest.raises(ValueError, match="differs"):
        adapt_unmerged_dotsocr([entry(0)], [row.model_copy(update={"warnings": ["invented"]})])


def test_cli_produces_immutable_inputs_and_sha(tmp_path: Path, monkeypatch):
    manifest = tmp_path / "manifest.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    manifest.write_text(entry(0).model_dump_json() + "\n", encoding="utf-8")
    predictions.write_text(
        record(0, [{"category": "Table", "text": HTML}]).model_dump_json() + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "converted"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "adapt_dotsocr_document_predictions.py",
            "--manifest",
            str(manifest),
            "--predictions",
            str(predictions),
            "--output-dir",
            str(output),
        ],
    )
    assert main() == 0
    summary = json.loads((output / "summary.json").read_text())
    assert summary["outputs"]["document-tables.jsonl"]["rows"] == 1
    assert json.loads((output / "table-evidence.jsonl").read_text())["page_number"] == 0
    with pytest.raises(FileExistsError):
        main()
