import json
import subprocess
import sys
from pathlib import Path

from cptla.evaluation.html_audit import diagnose_html


def test_standard_table_requires_no_format_change():
    result = diagnose_html("<table><tr><td>A &amp; B</td></tr></table>")
    assert result["xml_ok"]
    assert result["lexical_xml_ok"]
    assert result["structural_issues"] == []


def test_void_tags_and_html_entities_are_only_diagnostic_candidates():
    result = diagnose_html("<table><tr><td>A<br>B&nbsp;C & D</td></tr></table>")
    assert not result["xml_ok"]
    assert result["lexical_xml_ok"]
    assert result["structural_issues"] == []
    assert result["cell_count"] == 1


def test_missing_cell_close_is_not_silently_repaired():
    result = diagnose_html("<table><tr><td>A</tr></table>")
    assert not result["lexical_xml_ok"]
    assert result["structural_issues"]


def test_multiple_tables_are_flagged():
    result = diagnose_html("<table></table><table></table>")
    assert not result["xml_ok"]
    assert result["table_count"] == 2


def test_non_string_output_is_explicit():
    assert diagnose_html(None)["input_type"] == "NoneType"


def test_literal_angle_bracket_text_and_quoted_attributes_are_not_repaired():
    result = diagnose_html('<table><tr><td title="a>b">x < y</td></tr></table>')
    assert not result["lexical_xml_ok"]


def test_audit_reconciles_two_stages_and_refuses_existing_output(tmp_path):
    def save(name, records):
        path = tmp_path / name
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path

    table = "<table><tr><td>A<br>B</td></tr></table>"
    manifest = save("manifest.jsonl", [{"image_id": "page"}])
    predictions = save(
        "predictions.jsonl",
        [
            {
                "image_id": "page",
                "status": "ok",
                "warnings": ["invalid_table_html:1"],
                "tables_html": [table],
                "raw_output": json.dumps(
                    [
                        {"category": "Table", "text": table},
                        {"category": "Table", "text": "<table><tr><td>cut"},
                    ]
                ),
            }
        ],
    )
    save("document-tables.jsonl", [{"table_id": "t", "html": table}])
    save(
        "table-evidence.jsonl",
        [
            {"table_id": "t", "image_id": "page", "layout_element_index": 0},
        ],
    )
    failures = save("failures.jsonl", [{"table_id": "t"}])
    output = tmp_path / "new-output"
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[2] / "scripts/audit_dotsocr_html.py"),
        "--manifest",
        str(manifest),
        "--predictions",
        str(predictions),
        "--adapter-dir",
        str(tmp_path),
        "--failures",
        str(failures),
        "--output-dir",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["runner_rejected"] == 1
    assert summary["counts"]["score_rejected"] == 1
    assert summary["pages_both_rejections"] == 1
    assert summary["buckets"]["score_rejected/lexical_candidate"] == 1
    assert summary["inputs_unchanged"]
    original = (output / "summary.json").read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert (output / "summary.json").read_bytes() == original
