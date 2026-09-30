import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from grits import GritsEvaluator
from PIL import Image

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.cross_page import DocumentTablePrediction
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.simple_merge import merge_repeated_header_pages
from scripts.adapt_dotsocr_document_predictions import main as adapt_main
from scripts.merge_dotsocr_repeated_header import main as merge_main

HEADER = "<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>"
TOP = HEADER + "<tr><td>A</td><td>1</td></tr></tbody></table>"
NEXT = HEADER + "<tr><td>B</td><td>2</td></tr></tbody></table>"
THIRD = HEADER + "<tr><td>C</td><td>3</td></tr></tbody></table>"


def setup(htmls=(TOP, NEXT), positions=((10, 85, 90, 100), (10, 0, 90, 30))):
    manifest = []
    pages = []
    tables = []
    evidence = []
    sizes = {}
    for page, (html, bbox) in enumerate(zip(htmls, positions, strict=True)):
        image_id = f"PMC1_page_{page}.jpg"
        manifest.append(
            ImageManifestEntry(
                image_id=image_id,
                unit_id="PMC1",
                document_id="PMC1",
                page_number=page,
                relative_path=image_id,
            )
        )
        pages.append(
            PredictionRecord(
                image_id=image_id, unit_id="PMC1", status="ok", tables_html=[], elapsed_sec=0
            )
        )
        sizes[image_id] = (100, 100)
        table_id = f"PMC1-page-{page}-table-0"
        tables.append(
            DocumentTablePrediction(
                document_id="PMC1", table_id=table_id, html=html, source_pages=[page]
            )
        )
        evidence.append(
            {
                "document_id": "PMC1",
                "table_id": table_id,
                "image_id": image_id,
                "page_number": page,
                "bbox_as_provided": list(bbox),
            }
        )
    return manifest, pages, tables, evidence, sizes


def run(data):
    return merge_repeated_header_pages(*data)


def test_repeated_header_merges_rows_and_preserves_both_pages():
    merged, decisions, report = run(setup())
    assert report["accepted_boundaries"] == 1
    assert len(merged) == 1
    assert merged[0].source_pages == [0, 1]
    assert merged[0].html.count("<th>") == 2
    assert "<td>B</td>" in merged[0].html
    assert decisions[0]["reason"] == "accepted"


def test_three_page_chain_keeps_one_header_and_all_sources():
    data = setup(
        (TOP, NEXT, THIRD),
        ((10, 85, 90, 100), (10, 0, 90, 100), (10, 0, 90, 25)),
    )
    merged, decisions, report = run(data)
    assert len(merged) == 1
    assert merged[0].source_pages == [0, 1, 2]
    assert merged[0].html.count("<th>") == 2
    assert [decision["reason"] for decision in decisions] == ["accepted", "accepted"]
    assert report["output_tables"] == 1


@pytest.mark.parametrize(
    "right_html,reason",
    [
        (
            "<table><tr><td>Key</td><td>Value</td></tr><tr><td>B</td><td>2</td></tr></table>",
            "column_header_or_html_mismatch",
        ),
        (
            "<table><tr><th>Other</th><th>Value</th></tr><tr><td>B</td><td>2</td></tr></table>",
            "column_header_or_html_mismatch",
        ),
        (
            "<table><tr><th>Key</th></tr><tr><td>B</td></tr></table>",
            "column_header_or_html_mismatch",
        ),
        ("<table><tr><th>Key</th><th>Value</th></tr></table>", "column_header_or_html_mismatch"),
        (
            "<table><tr><th>Key</th><th>Value</th></tr>"
            "<tr><td rowspan='2'>B</td><td>2</td></tr></table>",
            "column_header_or_html_mismatch",
        ),
    ],
)
def test_same_column_count_alone_never_merges(right_html, reason):
    merged, decisions, report = run(setup((TOP, right_html)))
    assert len(merged) == 2
    assert decisions[0]["reason"] == reason
    assert report["accepted_boundaries"] == 0


@pytest.mark.parametrize(
    "positions,reason",
    [
        (((10, 0, 90, 40), (10, 0, 90, 25)), "not_at_page_bottom"),
        (((10, 80, 90, 100), (10, 40, 90, 70)), "not_at_page_top"),
    ],
)
def test_geometry_gates(positions, reason):
    merged, decisions, _ = run(setup(positions=positions))
    assert len(merged) == 2
    assert decisions[0]["reason"] == reason


def test_no_fake_nonadjacent_merge_and_error_page():
    manifest, pages, tables, evidence, sizes = setup()
    manifest[1] = manifest[1].model_copy(update={"image_id": "PMC1_page_2.jpg", "page_number": 2})
    pages[1] = pages[1].model_copy(update={"image_id": "PMC1_page_2.jpg"})
    tables[1] = tables[1].model_copy(update={"source_pages": [2]})
    evidence[1].update(image_id="PMC1_page_2.jpg", page_number=2)
    sizes["PMC1_page_2.jpg"] = sizes.pop("PMC1_page_1.jpg")
    merged, decisions, _ = run((manifest, pages, tables, evidence, sizes))
    assert len(merged) == 2 and not decisions
    data = setup()
    data[1][1] = data[1][1].model_copy(update={"status": "error", "error": "failure"})
    assert run(data)[1][0]["reason"] == "inference_error"


def test_invalid_or_mismatched_provenance_is_rejected():
    data = setup()
    data[3][1]["page_number"] = 0
    with pytest.raises(ValueError, match="evidence page mismatch"):
        run(data)
    data = setup()
    data[1].pop()
    with pytest.raises(ValueError, match="complete"):
        run(data)
    data = setup()
    data[3][1]["bbox_as_provided"] = None
    merged, decisions, _ = run(data)
    assert len(merged) == 2
    assert decisions[0]["reason"] == "missing_or_invalid_bbox"


def test_same_headers_on_unrelated_tables_are_a_known_false_positive():
    right = HEADER + "<tr><td>Unrelated</td><td>9</td></tr></tbody></table>"
    merged, decisions, _ = run(setup((TOP, right)))
    assert decisions[0]["reason"] == "accepted"
    assert merged[0].source_pages == [0, 1]
    # This is why this conservative rule is a baseline, not a verified continuation label.
    assert "Unrelated" in merged[0].html


def test_train_whole_table_can_be_artificially_split_and_rejoined():
    source = Path("data/pubtables-v2/extracted/Full Documents/train/tables/PMC10158982_tables.json")
    if not source.exists():
        pytest.skip("train table fixture unavailable")
    truth = json.loads(source.read_text(encoding="utf-8"))[0]["html"]
    first_root = ET.fromstring(truth)
    second_root = ET.fromstring(truth)
    first_body = first_root.find(".//tbody")
    second_body = second_root.find(".//tbody")
    assert first_body is not None and second_body is not None
    # A synthetic row split at a train-only boundary without spanning cells.
    for row in list(first_body)[25:]:
        first_body.remove(row)
    for row in list(second_body)[:25]:
        second_body.remove(row)
    data = setup(
        (ET.tostring(first_root, encoding="unicode"), ET.tostring(second_root, encoding="unicode"))
    )
    merged, decisions, _ = run(data)
    assert decisions[0]["reason"] == "accepted"
    scorer = GritsEvaluator(metrics=["con", "top"])
    scorer.eval_htmls([truth], [merged[0].html])
    assert scorer.compute_grits()["grits_con_grid_exact_match_accuracy"] == 1


def test_existing_validation_smoke_has_no_merge_without_page_two_table():
    root = Path("artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge")
    if not root.exists():
        pytest.skip("saved validation smoke adapter unavailable")
    # The val-smoke input is used only as a frozen no-output-mutation regression.
    assert (root / "document-tables.jsonl").read_text().count("\n") == 1


def test_cpu_cli_roundtrip_and_refuse_existing_output(tmp_path: Path, monkeypatch):
    images = tmp_path / "images"
    images.mkdir()
    manifest, _, _, _, _ = setup()
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        "".join(row.model_dump_json() + "\n" for row in manifest), encoding="utf-8"
    )
    raw_layouts = [
        [{"category": "Table", "bbox": [10, 85, 90, 100], "text": TOP}],
        [{"category": "Table", "bbox": [10, 0, 90, 30], "text": NEXT}],
    ]
    records = []
    for page, layout in enumerate(raw_layouts):
        Image.new("RGB", (100, 100), "white").save(images / manifest[page].image_id)
        records.append(
            PredictionRecord(
                image_id=manifest[page].image_id,
                unit_id="PMC1",
                status="ok",
                tables_html=[layout[0]["text"]],
                raw_output=json.dumps(layout),
                elapsed_sec=0,
            )
        )
    source = tmp_path / "predictions.jsonl"
    source.write_text("".join(row.model_dump_json() + "\n" for row in records), encoding="utf-8")
    converted = tmp_path / "converted"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "adapt_dotsocr_document_predictions.py",
            "--manifest",
            str(manifest_path),
            "--predictions",
            str(source),
            "--output-dir",
            str(converted),
        ],
    )
    assert adapt_main() == 0
    output = tmp_path / "merged"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "merge_dotsocr_repeated_header.py",
            "--manifest",
            str(manifest_path),
            "--adapter-dir",
            str(converted),
            "--images",
            str(images),
            "--output-dir",
            str(output),
        ],
    )
    assert merge_main() == 0
    result = json.loads((output / "document-tables.jsonl").read_text())
    assert result["source_pages"] == [0, 1]
    assert json.loads((output / "summary.json").read_text())["accepted_boundaries"] == 1
    with pytest.raises(FileExistsError):
        merge_main()
    with (converted / "table-evidence.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    monkeypatch.setattr(sys, "argv", [*sys.argv[:-1], str(tmp_path / "tampered")])
    with pytest.raises(ValueError, match="changed since audit"):
        merge_main()
