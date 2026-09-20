import importlib
import json
import sys
from pathlib import Path


def test_normalization_script_writes_valid_jsonl(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    fixture = json.loads(
        Path("tests/fixtures/pubtables_v2_document_bundle.json").read_text(encoding="utf-8")
    )
    input_root = tmp_path / "input"
    output = tmp_path / "documents.jsonl"
    rejects = tmp_path / "rejects.jsonl"
    tables_dir = input_root / "tables"
    tables_dir.mkdir(parents=True)
    (tables_dir / "PMC_SYNTHETIC_tables.json").write_text(
        json.dumps(fixture["tables"]), encoding="utf-8"
    )

    module = importlib.import_module("scripts.normalize_pubtables_v2")
    monkeypatch.setattr(module, "load_document_bundle", lambda *args, **kwargs: fixture)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "normalize_pubtables_v2.py",
            "--input",
            str(input_root),
            "--output",
            str(output),
            "--rejects",
            str(rejects),
            "--source-split",
            "test",
            "--source-revision",
            "abc123",
            "--limit",
            "1",
        ],
    )

    assert module.main() == 0
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["document_id"] == "PMC_SYNTHETIC"
    assert rejects.read_text(encoding="utf-8") == ""
    summary = json.loads(capsys.readouterr().out)
    assert summary["clipped_word_boxes"] == 0
