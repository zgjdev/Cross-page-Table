import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cptla.data.models import DocumentRecord
from cptla.data.pubtables_v2 import (
    load_document_bundle,
    normalize_document,
    normalize_document_with_stats,
)

FIXTURE = Path("tests/fixtures/pubtables_v2_document_bundle.json")


def test_normalizes_repository_document_bundle() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    record = DocumentRecord.model_validate(normalize_document(raw))

    assert record.document_id == "PMC_SYNTHETIC"
    assert record.source_split == "test"
    assert record.page_count == 6
    assert [word.page for word in record.words] == [4, 5]
    assert record.words[0].bbox.x0 == pytest.approx(140 / 1126)
    assert record.words[0].bbox.y1 == pytest.approx(180 / 1500)

    table = record.tables[0]
    assert len(table.fragments) == 2
    assert all(fragment.table_id == table.table_id for fragment in table.fragments)
    assert table.fragments[1].bbox.x1 == pytest.approx(488 / 1126)
    assert table.cells[0].row == 0
    assert table.cells[0].column == 0
    assert table.cells[0].column_span == 2
    assert table.cells[0].is_header is True


def test_rejects_fragment_for_page_without_dimensions() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["pages"] = raw["pages"][:1]

    with pytest.raises(ValueError, match="missing page metadata for page 5"):
        normalize_document(raw)


def test_clips_small_word_bbox_overflow_and_reports_it() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["pages"][0]["words"][0]["bbox"] = [-8.56826, 1276.47, 65.1868, 1461.22]

    normalized, stats = normalize_document_with_stats(raw)
    record = DocumentRecord.model_validate(normalized)

    assert record.words[0].bbox.x0 == 0
    assert record.words[0].bbox.y0 == pytest.approx(1276.47 / 1500)
    assert stats.clipped_word_boxes == 1


def test_rejects_word_bbox_with_large_overflow() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["pages"][0]["words"][0]["bbox"] = [-100.0, 100.0, 65.0, 140.0]

    with pytest.raises(ValueError, match="horizontal bbox coordinates are outside"):
        normalize_document(raw)


def test_does_not_clip_table_fragment_bbox() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["tables"][0]["parts"][0]["bbox"] = [-1.0, 150.0, 1000.0, 1390.0]

    with pytest.raises(ValueError, match="horizontal bbox coordinates are outside"):
        normalize_document(raw)


def _write_xml(path: Path, *, filename: str, width: int, height: int) -> None:
    annotation = ET.Element("annotation")
    ET.SubElement(annotation, "filename").text = filename
    size = ET.SubElement(annotation, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"
    ET.ElementTree(annotation).write(path, encoding="utf-8", xml_declaration=True)


def test_loads_document_bundle_from_repository_directories(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    tables_dir = tmp_path / "tables"
    words_dir = tmp_path / "words"
    xml_dir = tmp_path / "xml_annotations"
    tables_dir.mkdir()
    words_dir.mkdir()
    xml_dir.mkdir()

    tables_path = tables_dir / "PMC_SYNTHETIC_tables.json"
    tables_path.write_text(json.dumps(fixture["tables"]), encoding="utf-8")
    for page in fixture["pages"]:
        page_num = page["page_num"]
        (words_dir / f"PMC_SYNTHETIC_page_{page_num}_words.json").write_text(
            json.dumps(page["words"]), encoding="utf-8"
        )
        _write_xml(
            xml_dir / f"PMC_SYNTHETIC_page_{page_num}.xml",
            filename=f"PMC_SYNTHETIC_page_{page_num}.jpg",
            width=page["width"],
            height=page["height"],
        )

    bundle = load_document_bundle(tmp_path, tables_path, source_split="test")
    record = DocumentRecord.model_validate(normalize_document(bundle))

    assert bundle["document_id"] == "PMC_SYNTHETIC"
    assert [page["page_num"] for page in bundle["pages"]] == [4, 5]
    assert len(record.tables[0].fragments) == 2
