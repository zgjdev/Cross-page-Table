import hashlib
import json

import pytest
from PIL import Image

from cptla.reconstruction.data import scan_training_data


@pytest.fixture
def train(tmp_path):
    train_root = tmp_path / "data/pubtables-v2/extracted/Full Documents/train"
    (train_root / "images").mkdir(parents=True)
    (train_root / "tables").mkdir()
    return train_root


def _part(page, bbox=None):
    return {
        "page_num": page,
        "page_object_num": 0,
        "bbox": bbox if bbox is not None else [0.2, 1.5, 6.7, 7],
    }


def _table(*parts):
    return {
        "html": "<table><tr><td colspan='2'>A</td></tr></table>",
        "parts": parts,
        "cells": [{"row_nums": [0], "column_nums": [0, 1], "xml_text_content": "A"}],
    }


def _annotation(train, document, *tables):
    path = train / "tables" / f"{document}_tables.json"
    path.write_text(json.dumps(tables), encoding="utf-8")
    return path


def _image(train, document, page):
    path = train / "images" / f"{document}_page_{page}.jpg"
    Image.new("RGB", (10, 8)).save(path)
    return path


def test_cross_page_manifest_keeps_parts_and_isolates_targets(tmp_path, train):
    _image(train, "PMC1", 2)
    image = _image(train, "PMC1", 10)
    logical_table = _table(_part(10, [-1.1, 1.5, 10.1, 7.1]), _part(2), _part(10))
    annotation = _annotation(train, "PMC1", logical_table, _table(_part(2), _part(2)))
    before = {path: path.read_bytes() for path in train.glob("*/*")}

    result = scan_training_data(tmp_path)
    assert result == scan_training_data(tmp_path)
    assert {path: path.read_bytes() for path in train.glob("*/*")} == before

    (group,) = result["inputs"]
    (target,) = result["targets"]
    assert group["group_id"] == target["group_id"]
    assert group["source_split"] == "train"
    assert group["protocol"] == "R0_oracle_gt_parts_and_grouping"
    assert group["page_numbers"] == target["source_pages"] == [2, 10]
    assert [part["page_num"] for part in group["fragments"]] == [2, 10, 10]
    assert [part["part_index"] for part in group["fragments"]] == [1, 0, 2]
    assert len({part["fragment_id"] for part in group["fragments"]}) == 3
    fragment = group["fragments"][1]
    assert fragment["bbox"] == [-1.1, 1.5, 10.1, 7.1]
    assert fragment["crop_box"] == [0, 1, 10, 8]
    assert fragment["clamped"] is True
    assert fragment["image_size"] == [10, 8]
    assert fragment["image_sha256"] == hashlib.sha256(before[image]).hexdigest()
    assert target["source_table_sha256"] == hashlib.sha256(before[annotation]).hexdigest()
    assert target["html"] == logical_table["html"]
    assert "html" not in str(group) and "cells" not in str(group)
    assert len(result["source_hashes"]) == 3

    audit = result["audit"]
    assert audit["multi_part_single_page_tables"] == 1
    assert audit["nonadjacent_part_page_gaps"] == 1
    assert audit["clamped_fragments"] == 1
    assert audit["profiles"] == [
        {
            "group_id": group["group_id"],
            "document_id": "PMC1",
            "page_count": 2,
            "cell_count": 1,
            "has_span": True,
        }
    ]


@pytest.mark.parametrize(
    ("parts", "message"),
    [
        ((_part(1),), "without image"),
        ((_part(0, [10, 0, 11, 1]),), "empty crop"),
        ((_part(0, [0, 0, float("inf"), 1]),), "invalid bbox"),
        ((_part(0, [0, 0, 0, 1]),), "invalid bbox"),
        (({"page_num": True},), "invalid page_num"),
    ],
)
def test_invalid_part_fails(tmp_path, train, parts, message):
    _image(train, "PMC1", 0)
    _annotation(train, "PMC1", _table(*parts))
    with pytest.raises(ValueError, match=message):
        scan_training_data(tmp_path)


def test_duplicate_numeric_page_fails(tmp_path, train):
    _image(train, "PMC1", 0)
    _image(train, "PMC1", "00")
    _annotation(train, "PMC1", _table(_part(0)))
    with pytest.raises(ValueError, match="duplicate page"):
        scan_training_data(tmp_path)


def test_invalid_json_fails(tmp_path, train):
    _image(train, "PMC1", 0)
    annotation = _annotation(train, "PMC1")
    annotation.write_text("[", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON.*PMC1"):
        scan_training_data(tmp_path)


def test_smoke_does_not_require_images_for_unselected_documents(tmp_path, train):
    _image(train, "PMC1", 0)
    _annotation(train, "PMC1", _table(_part(0)))
    _annotation(train, "PMC2", _table(_part(0)))
    result = scan_training_data(tmp_path, limit_documents=1)
    assert result["audit"]["available_documents"] == 2
    assert result["audit"]["is_full_scan"] is False
    assert [doc["document_id"] for doc in result["documents"]] == ["PMC1"]


def test_image_escape_fails(tmp_path, train):
    escaped = tmp_path.parent / f"{tmp_path.name}-image.jpg"
    Image.new("RGB", (10, 8)).save(escaped)
    image = train / "images/PMC1_page_0.jpg"
    try:
        image.symlink_to(escaped)
    except OSError:
        pytest.skip("creating file symlinks requires host permission")
    _annotation(train, "PMC1", _table(_part(0)))
    with pytest.raises(ValueError, match="outside train"):
        scan_training_data(tmp_path)
