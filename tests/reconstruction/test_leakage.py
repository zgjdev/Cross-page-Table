import json

import pytest

from cptla.reconstruction.leakage import audit_leakage


def source(root, split, doc, html):
    p = root / "data/pubtables-v2/extracted/Full Documents" / split / "tables"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{doc}_tables.json").write_text(json.dumps([{"html": html}]), encoding="utf-8")


def test_duplicates_and_empty(tmp_path):
    for doc, html in [
        ("PMC1", "<td>secret A</td>"),
        ("PMC2", "<td> secret  A </td>"),
        ("PMC3", ""),
        ("PMC4", ""),
    ]:
        source(tmp_path, "train", doc, html)
    out = audit_leakage(tmp_path, "one")
    result = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert result["table_duplicate_groups"] == 1
    assert result["document_duplicate_groups"] == 1
    assert result["empty_tables"] == 2
    assert "secret" not in "".join(p.read_text(encoding="utf-8") for p in out.iterdir())
    with pytest.raises(FileExistsError):
        audit_leakage(tmp_path, "one")


def test_missing_split_saved(tmp_path):
    source(tmp_path, "train", "PMC1", "<td>A</td>")
    with pytest.raises(FileNotFoundError):
        audit_leakage(tmp_path, "two", official_splits=True)
    out = tmp_path / "artifacts/reconstruction-leakage/two"
    assert json.loads((out / "failure.json").read_text(encoding="utf-8"))["status"] == "failed"


def test_invalid_run(tmp_path):
    with pytest.raises(ValueError):
        audit_leakage(tmp_path, "../escape")


def test_official_and_provisional_overlap(tmp_path):
    for split, doc in [("train", "PMC1"), ("train", "PMC2"), ("val", "PMC3"), ("test", "PMC4")]:
        source(tmp_path, split, doc, "<td>same</td>")
    assignments = tmp_path / "splits.jsonl"
    assignments.write_text(
        "\n".join(
            json.dumps({"document_id": doc, "split": split})
            for doc, split in [("PMC1", "train_fit"), ("PMC2", "train_dev")]
        ),
        encoding="utf-8",
    )
    out = audit_leakage(tmp_path, "all", official_splits=True, splits_path=assignments)
    groups = json.loads((out / "overlaps.json").read_text(encoding="utf-8"))
    assert groups["tables"][0]["cross_official_split"]
    assert groups["tables"][0]["cross_provisional_split"]
    assert len(groups["documents"][0]["members"]) == 4


def test_external_assignments_rejected(tmp_path):
    source(tmp_path, "train", "PMC1", "x")
    with pytest.raises(ValueError, match="escapes"):
        audit_leakage(tmp_path, "external", splits_path=tmp_path.parent / "outside.jsonl")


def test_invalid_annotation_no_plaintext_failure(tmp_path):
    source(tmp_path, "train", "PMC1", "x")
    path = next(tmp_path.rglob("*_tables.json"))
    path.write_text("SECRET_INVALID_JSON", encoding="utf-8")
    with pytest.raises(ValueError):
        audit_leakage(tmp_path, "bad")
    assert "SECRET" not in (
        tmp_path / "artifacts/reconstruction-leakage/bad/failure.json"
    ).read_text(encoding="utf-8")


def test_partial_assignments_fail(tmp_path):
    source(tmp_path, "train", "PMC1", "a")
    source(tmp_path, "train", "PMC2", "b")
    assignments = tmp_path / "splits.jsonl"
    assignments.write_text(
        json.dumps({"document_id": "PMC1", "split": "train_fit"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="coverage"):
        audit_leakage(tmp_path, "partial", splits_path=assignments)
    assert not (tmp_path / "artifacts/reconstruction-leakage/partial/summary.json").exists()


def test_source_change_prevents_summary(tmp_path, monkeypatch):
    import cptla.reconstruction.leakage as module

    source(tmp_path, "train", "PMC1", "a")
    annotation = next(tmp_path.rglob("*_tables.json"))
    original = module._canonical

    def changed(html):
        annotation.write_text("[]", encoding="utf-8")
        return original(html)

    monkeypatch.setattr(module, "_canonical", changed)
    with pytest.raises(ValueError, match="changed"):
        audit_leakage(tmp_path, "changed")
    assert not (tmp_path / "artifacts/reconstruction-leakage/changed/summary.json").exists()


def test_completion_manifest(tmp_path):
    source(tmp_path, "train", "PMC1", "a")
    out = audit_leakage(tmp_path, "complete")
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts_by_split"]["train"]["documents"] == 1
    assert summary["ended_utc"]
    assert summary["artifact_hashes"]["pending.json"]


def test_cross_split_symlink_rejected(tmp_path):
    source(tmp_path, "train", "PMC1", "a")
    source(tmp_path, "val", "PMC2", "b")
    directory = tmp_path / "data/pubtables-v2/extracted/Full Documents"
    link = directory / "train/tables/PMC2_tables.json"
    try:
        link.symlink_to(directory / "val/tables/PMC2_tables.json")
    except OSError:
        pytest.skip("symlink privilege unavailable")
    with pytest.raises(ValueError, match="escapes"):
        audit_leakage(tmp_path, "symlink")
