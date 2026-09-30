import json
from pathlib import Path

import pytest

from cptla.evaluation.pubtables_v2 import build_image_manifest, write_image_manifest
from scripts.build_cross_page_manifest import audit_validation


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, Path]:
    paths = {name: tmp_path / name for name in ("images", "tables", "pairs", "train", "test")}
    for path in paths.values():
        path.mkdir()
    for page in range(4):
        (paths["images"] / f"PMC1_page_{page}.jpg").write_bytes(b"image")
    paths["manifest"] = tmp_path / "full-manifest.jsonl"
    write_image_manifest(build_image_manifest(paths["images"], "full_documents"), paths["manifest"])
    _write_json(
        paths["tables"] / "PMC1_tables.json",
        [
            {
                "html": "<table><tr><td>two pages</td></tr></table>",
                "parts": [
                    {"page_num": 0, "page_object_num": 0, "bbox": [0, 1, 2, 3]},
                    {"page_num": 1, "page_object_num": 0, "bbox": [0, 1, 2, 3]},
                    {"page_num": 2, "page_object_num": 0, "bbox": [0, 1, 2, 3]},
                ],
            },
            {
                "html": "<table><tr><td>same page</td></tr></table>",
                "parts": [
                    {"page_num": 3, "bbox": [0, 1, 2, 3]},
                    {"page_num": 3, "bbox": [3, 1, 5, 3]},
                ],
            },
        ],
    )
    _write_json(
        paths["pairs"] / "PMC1.json",
        [
            {"page_A": "PMC1_page_0", "page_B": "PMC1_page_1", "label": 1},
            {"page_A": "PMC1_page_1", "page_B": "PMC1_page_2", "label": 1},
            {"page_A": "PMC1_page_2", "page_B": "PMC1_page_3", "label": 0},
        ],
    )
    _write_json(paths["train"] / "PMC2_tables.json", [])
    _write_json(paths["test"] / "PMC3_tables.json", [])
    return paths


def _audit(paths: dict[str, Path]):
    return audit_validation(
        manifest_path=paths["manifest"],
        images_dir=paths["images"],
        tables_dir=paths["tables"],
        pairs_dir=paths["pairs"],
        train_tables_dir=paths["train"],
        test_tables_dir=paths["test"],
    )


def test_audit_separates_cross_page_tables_from_same_page_parts(tmp_path: Path) -> None:
    summary, rows = _audit(_fixture(tmp_path))

    assert summary["image_pages"] == 4
    assert summary["cross_page_tables"] == 1
    assert summary["multi_part_single_page_tables"] == 1
    assert summary["cross_page_pages_per_table"] == {3: 1}
    assert summary["official_positive_pairs"] == 2
    assert summary["official_negative_pairs"] == 1
    assert summary["pair_discrepancies"] == 0
    assert rows["gold-cross-page.jsonl"][0]["page_numbers"] == [0, 1, 2]
    assert rows["negative-page-pairs.jsonl"][0]["derived_candidate_table_ids"] == []
    assert rows["official-page-pairs.jsonl"][0]["derived_candidate_table_ids"] == ["PMC1-table-0"]


def test_audit_flags_official_pair_disagreement_without_changing_labels(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    pair_path = paths["pairs"] / "PMC1.json"
    pairs = json.loads(pair_path.read_text(encoding="utf-8"))
    pairs[0]["label"] = 0
    _write_json(pair_path, pairs)

    summary, rows = _audit(paths)

    assert summary["pair_discrepancies"] == 1
    assert summary["discrepancy_reasons"] == {"negative_with_derived_table": 1}
    assert rows["negative-page-pairs.jsonl"][0]["label"] == 0


def test_audit_records_nonadjacent_parts_without_inventing_official_pair(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    table_path = paths["tables"] / "PMC1_tables.json"
    tables = json.loads(table_path.read_text(encoding="utf-8"))
    tables.append(
        {
            "html": "<table><tr><td>gap</td></tr></table>",
            "parts": [
                {"page_num": 1, "bbox": [0, 1, 2, 3]},
                {"page_num": 3, "bbox": [0, 1, 2, 3]},
            ],
        }
    )
    _write_json(table_path, tables)

    summary, rows = _audit(paths)

    assert summary["cross_page_tables"] == 2
    assert summary["nonadjacent_part_page_gaps"] == 1
    assert summary["pair_discrepancies"] == 0
    assert rows["nonadjacent-part-gaps.jsonl"] == [
        {
            "document_id": "PMC1",
            "table_id": "PMC1-table-2",
            "page_before": 1,
            "page_after": 3,
            "intervening_pages": [2],
            "source": "derived_from_logical_table_parts",
        }
    ]


def test_audit_rejects_split_overlap(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    _write_json(paths["train"] / "PMC1_tables.json", [])

    with pytest.raises(ValueError, match="overlap"):
        _audit(paths)


def test_audit_rejects_manifest_with_missing_page(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    (paths["images"] / "PMC1_page_3.jpg").unlink()

    with pytest.raises(ValueError, match="manifest differs"):
        _audit(paths)


def test_audit_rejects_part_page_without_image(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    table_path = paths["tables"] / "PMC1_tables.json"
    tables = json.loads(table_path.read_text(encoding="utf-8"))
    tables[0]["parts"][2]["page_num"] = 8
    _write_json(table_path, tables)

    with pytest.raises(ValueError, match="part page without image"):
        _audit(paths)


def test_audit_rejects_duplicate_official_pairs(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    pair_path = paths["pairs"] / "PMC1.json"
    pairs = json.loads(pair_path.read_text(encoding="utf-8"))
    pairs.append(pairs[0])
    _write_json(pair_path, pairs)

    with pytest.raises(ValueError, match="duplicate pair"):
        _audit(paths)
