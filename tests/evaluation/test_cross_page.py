import json
import sys
from pathlib import Path

import pytest

from cptla.evaluation.contracts import PredictionRecord
from cptla.evaluation.cross_page import DocumentTablePrediction, score_cross_page
from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.scoring import IncompleteCoverageError
from scripts.score_cross_page_predictions import main

HEADER = "<table><tr><td>A</td></tr></table>"
OTHER = "<table><tr><td>B</td></tr></table>"
MERGED = "<table><tr><td>A</td></tr><tr><td>B</td></tr></table>"


def fixture():
    manifest = [
        ImageManifestEntry(
            image_id=f"PMC1_page_{page}.jpg",
            relative_path=f"PMC1_page_{page}.jpg",
            unit_id="PMC1",
            document_id="PMC1",
            page_number=page,
        )
        for page in range(4)
    ]
    status = [
        PredictionRecord(
            image_id=row.image_id, unit_id="PMC1", status="ok", tables_html=[], elapsed_sec=0
        )
        for row in manifest
    ]
    truth = {
        "PMC1": [
            {"html": HEADER, "parts": [{"page_num": 0}, {"page_num": 0}]},
            {"html": MERGED, "parts": [{"page_num": 1}, {"page_num": 3}]},
            {"html": OTHER, "parts": [{"page_num": 2}]},
        ]
    }
    gold = [
        {
            "document_id": "PMC1",
            "table_index": 1,
            "table_id": "PMC1-table-1",
            "html": MERGED,
            "page_numbers": [1, 3],
        }
    ]
    return manifest, status, truth, gold


def pred(table_id, html, pages):
    return DocumentTablePrediction(
        document_id="PMC1", table_id=table_id, html=html, source_pages=pages
    )


def score(preds, *, changes=None):
    manifest, status, truth, gold = fixture()
    if changes:
        changes(manifest, status, truth, gold)
    return score_cross_page(manifest, status, preds, truth, gold)


def test_perfect_cross_page_and_same_page_multipart_exclusion():
    metrics, matches, failures = score(
        [pred("one", OTHER, [2]), pred("two", MERGED, [1, 3]), pred("three", HEADER, [0])]
    )
    assert metrics["cross_page_truth_tables"] == 1
    assert metrics["cross_page"]["grits_con_grid_exact_match_accuracy"] == 1
    assert metrics["full_document"]["grits_con_grid_exact_match_accuracy"] == 1
    assert matches[0]["predicted_table_id"] == "two"
    assert matches[0]["truth_pages"] == [1, 3]
    assert failures == []


def test_all_truth_competes_before_cross_page_subset():
    metrics, matches, _ = score([pred("single", HEADER, [0])])
    assert matches[0]["predicted_table_id"] is None
    assert metrics["cross_page"]["grits_con"] == 0


def test_one_prediction_cannot_match_two_tables_and_split_is_not_exact():
    metrics, matches, _ = score([pred("mixed", MERGED, [1, 2, 3])])
    assert metrics["cross_page_matched_tables"] == 1
    assert metrics["diagnostics"]["matched_cross_page_extra_source_pages"] == 1
    assert len(matches) == 1
    metrics, _, _ = score([pred("left", HEADER, [1]), pred("right", OTHER, [3])])
    assert metrics["cross_page"]["grits_con_grid_exact_match_accuracy"] == 0
    assert metrics["diagnostics"]["matched_cross_page_missing_source_pages"] == 1


def test_unmatched_multisource_and_invalid_html_reported():
    metrics, _, failures = score(
        [
            pred("unmatched", "<table><tr><td>Z</td></tr></table>", [0, 2]),
            pred("bad", "<table><tr><td>broken", [1, 3]),
        ]
    )
    assert metrics["diagnostics"]["unmatched_multisource_tables"] == 1
    assert metrics["diagnostics"]["invalid_table_html"] == 1
    assert failures[0]["table_id"] == "bad"


def test_full_coverage_includes_empty_pages_and_errors():
    manifest, status, truth, gold = fixture()
    with pytest.raises(IncompleteCoverageError):
        score_cross_page(manifest, status[:-1], [], truth, gold)
    status[0] = status[0].model_copy(update={"status": "error", "error": "out of memory"})
    metrics, _, _ = score_cross_page(manifest, status, [], truth, gold)
    assert metrics["diagnostics"]["inference_error_pages"] == 1
    assert metrics["coverage"]["is_complete"]


@pytest.mark.parametrize(
    "changes",
    [
        lambda m, s, t, g: g.clear(),
        lambda m, s, t, g: g[0].update(html=OTHER),
        lambda m, s, t, g: g[0].update(page_numbers=[1, 2]),
    ],
)
def test_gold_integrity_rejected(changes):
    with pytest.raises(ValueError, match="cross-page"):
        score([], changes=changes)


@pytest.mark.parametrize("pages", [[1, 1], [4], [-1]])
def test_invalid_provenance_rejected(pages):
    with pytest.raises(ValueError, match="source pages"):
        score([pred("x", MERGED, pages)])


def test_deterministic_and_unknown_doc_rejected():
    rows = [pred("a", MERGED, [1, 3]), pred("b", OTHER, [2])]
    first = score(rows)
    assert json.dumps(first, sort_keys=True) == json.dumps(score(rows), sort_keys=True)
    with pytest.raises(ValueError, match="out-of-scope"):
        score([pred("a", MERGED, [1, 3]).model_copy(update={"document_id": "PMC2"})])


def test_real_validation_nonadjacent_case_is_preserved():
    root = Path("artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit")
    if not root.exists():
        pytest.skip("validation audit artifacts unavailable")
    with (root / "gold-cross-page.jsonl").open(encoding="utf-8") as handle:
        rows = (json.loads(line) for line in handle)
        case = next(row for row in rows if row["table_id"] == "PMC12274235-table-1")
    assert case["page_numbers"] == [4, 5, 7]


def test_cli_writes_new_output_only(tmp_path: Path, monkeypatch):
    manifest, status, truth, gold = fixture()
    inputs = {
        "manifest.jsonl": [row.model_dump(mode="json") for row in manifest],
        "pages.jsonl": [row.model_dump(mode="json") for row in status],
        "preds.jsonl": [pred("merged", MERGED, [1, 3]).model_dump(mode="json")],
        "gold.jsonl": gold,
    }
    for filename, rows in inputs.items():
        (tmp_path / filename).write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
    truth_dir = tmp_path / "truth"
    truth_dir.mkdir()
    (truth_dir / "PMC1_tables.json").write_text(json.dumps(truth["PMC1"]), encoding="utf-8")
    output = tmp_path / "result"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "score_cross_page_predictions.py",
            "--manifest",
            str(tmp_path / "manifest.jsonl"),
            "--page-results",
            str(tmp_path / "pages.jsonl"),
            "--document-tables",
            str(tmp_path / "preds.jsonl"),
            "--truth-dir",
            str(truth_dir),
            "--cross-page-gold",
            str(tmp_path / "gold.jsonl"),
            "--output-dir",
            str(output),
        ],
    )
    assert main() == 0
    assert json.loads((output / "metrics.json").read_text())["cross_page_truth_tables"] == 1
    assert len((output / "matches.jsonl").read_text().splitlines()) == 1
    with pytest.raises(FileExistsError):
        main()

    # A smoke manifest may be one complete document from a full-val gold file.
    with (tmp_path / "gold.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"document_id": "PMC2", "table_index": 0}) + "\n")
    monkeypatch.setattr(sys, "argv", [*sys.argv[:-1], str(tmp_path / "partial"), "--partial"])
    assert main() == 0
    assert json.loads((tmp_path / "partial" / "metrics.json").read_text())["scope"] == "partial"
