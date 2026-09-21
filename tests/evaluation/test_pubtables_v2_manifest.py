import json
from pathlib import Path

import pytest

from cptla.evaluation.pubtables_v2 import (
    build_image_manifest,
    manifest_sha256,
    parse_cropped_table_id,
    parse_full_document_image_id,
    write_image_manifest,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("PMC123_page_7.jpg", ("PMC123", 7)),
        ("PMC123_page_0.jpg", ("PMC123", 0)),
    ],
)
def test_parse_full_document_image_id(name: str, expected: tuple[str, int]) -> None:
    assert parse_full_document_image_id(name) == expected


@pytest.mark.parametrize(
    "name",
    ["PMC123_page_-1.jpg", "PMC123_page_1.png", "PMC123.jpg", "_page_1.jpg"],
)
def test_parse_full_document_image_id_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="Full Documents image name"):
        parse_full_document_image_id(name)


def test_parse_cropped_table_id_uses_official_stem() -> None:
    assert parse_cropped_table_id("PMC10649402_table_1.jpg") == "PMC10649402_table_1"


@pytest.mark.parametrize(
    "name",
    ["PMC10649402_table_-1.jpg", "PMC10649402_table_1.png", "table_1.jpg"],
)
def test_parse_cropped_table_id_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="Cropped Tables image name"):
        parse_cropped_table_id(name)


def test_full_document_manifest_is_sorted_and_ignores_non_jpg(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    for name in ("PMC2_page_1.jpg", "notes.txt", "PMC1_page_0.jpg", "PMC1_page_2.JPG"):
        (images / name).write_bytes(b"fixture")

    records = build_image_manifest(images, "full_documents")

    assert [record.image_id for record in records] == ["PMC1_page_0.jpg", "PMC2_page_1.jpg"]
    assert records[0].model_dump(mode="json") == {
        "image_id": "PMC1_page_0.jpg",
        "relative_path": "PMC1_page_0.jpg",
        "unit_id": "PMC1",
        "document_id": "PMC1",
        "page_number": 0,
    }


def test_cropped_manifest_hash_and_jsonl_are_deterministic(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    for name in ("PMC2_table_1.jpg", "PMC1_table_0.jpg"):
        (images / name).write_bytes(b"fixture")

    first = build_image_manifest(images, "cropped_tables")
    second = build_image_manifest(images, "cropped_tables")
    output = tmp_path / "manifest.jsonl"
    digest = write_image_manifest(first, output)

    assert manifest_sha256(first) == manifest_sha256(second) == digest
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [row["unit_id"] for row in rows] == ["PMC1_table_0", "PMC2_table_1"]
    assert all(row["page_number"] is None for row in rows)
