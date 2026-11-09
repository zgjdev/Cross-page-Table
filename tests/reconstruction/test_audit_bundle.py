import hashlib
from pathlib import Path

import pytest
from PIL import Image

from cptla.reconstruction.audit_bundle import write_audit_bundle


def fixture_bundle(tmp_path: Path):
    image = tmp_path / "data" / "page.jpg"
    image.parent.mkdir()
    Image.new("RGB", (160, 240), "white").save(image)
    row = {
        "group_id": "PMC1-table-0",
        "document_id": "PMC1",
        "fragments": [
            {
                "fragment_id": "PMC1-table-0-part-0",
                "page_num": 0,
                "part_index": 0,
                "image_relpath": "data/page.jpg",
                "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "image_size": [160, 240],
                "bbox": [10.2, 20.4, 120.5, 210.8],
                "crop_box": [10, 20, 121, 211],
            }
        ],
    }
    targets = [{"group_id": row["group_id"], "html": "<table><tr><td>A</td></tr></table>"}]
    sample = {
        "samples": [{"group_id": row["group_id"], "inclusion_probability": 0.5}],
        "coordinate_group_ids": [row["group_id"]],
    }
    output = tmp_path / "artifacts" / "run"
    output.mkdir(parents=True)
    return image, output, [row], targets, sample


def test_bundle_crops_declared_pixels_and_retains_sources(tmp_path):
    image, output, inputs, targets, sample = fixture_bundle(tmp_path)
    before = image.read_bytes()
    report = write_audit_bundle(tmp_path, output, inputs, targets, sample)
    assert report["case_count"] == 1
    assert report["coordinate_case_count"] == 1
    assert report["prediction_status"] == "not_generated"
    with Image.open(output / "review/images/PMC1-table-0-part-0-crop.png") as crop:
        assert crop.size == (111, 191)
    assert image.read_bytes() == before
    assert (output / "review/coordinates/PMC1-table-0.png").is_file()
    case = (output / "review/cases/PMC1-table-0.html").read_text(encoding="utf-8")
    assert "Ground Truth" in case
    assert "尚未生成" in case


def test_bundle_sandboxes_truth_instead_of_executing_markup(tmp_path):
    _, output, inputs, targets, sample = fixture_bundle(tmp_path)
    targets[0]["html"] = '<script>alert(1)</script><table onclick="alert(2)"></table>'
    write_audit_bundle(tmp_path, output, inputs, targets, sample)
    case = (output / "review/cases/PMC1-table-0.html").read_text(encoding="utf-8")
    assert '<iframe sandbox=""' in case
    assert "Content-Security-Policy" in case
    assert "<script>alert(1)</script>" not in case


def test_bundle_rejects_existing_output_without_replacing_it(tmp_path):
    _, output, inputs, targets, sample = fixture_bundle(tmp_path)
    (output / "review").mkdir()
    marker = output / "review/existing.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_audit_bundle(tmp_path, output, inputs, targets, sample)
    assert marker.read_text() == "keep"


@pytest.mark.parametrize("change", ["hash", "outside", "bad_id", "crop"])
def test_bundle_rejects_untrusted_or_changed_source(tmp_path, change):
    _, output, inputs, targets, sample = fixture_bundle(tmp_path)
    f = inputs[0]["fragments"][0]
    if change == "hash":
        f["image_sha256"] = "0" * 64
    elif change == "outside":
        f["image_relpath"] = "../outside.jpg"
    elif change == "bad_id":
        inputs[0]["group_id"] = "../escape"
        targets[0]["group_id"] = "../escape"
        sample["samples"][0]["group_id"] = "../escape"
        sample["coordinate_group_ids"] = ["../escape"]
    else:
        f["crop_box"] = [0, 0, 300, 300]
    with pytest.raises(ValueError):
        write_audit_bundle(tmp_path, output, inputs, targets, sample)


def test_bundle_rejects_missing_sample_instead_of_silently_skipping(tmp_path):
    _, output, inputs, targets, sample = fixture_bundle(tmp_path)
    sample["samples"].append({"group_id": "PMC9-table-1"})
    with pytest.raises(ValueError):
        write_audit_bundle(tmp_path, output, inputs, targets, sample)


def test_coordinate_board_preserves_the_bottom_of_crop_thumbnail(tmp_path):
    image, output, inputs, targets, sample = fixture_bundle(tmp_path)
    Image.new("RGB", (160, 240), "red").save(image, quality=100)
    inputs[0]["fragments"][0]["image_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    write_audit_bundle(tmp_path, output, inputs, targets, sample)
    with Image.open(output / "review/coordinates/PMC1-table-0.png") as board:
        # Header 30 + crop offset 399 + its last row 229 must remain inside the tile.
        assert board.height > 658
        assert board.getpixel((205, 658))[0] > 240
        assert board.getpixel((205, 658))[1] < 10
