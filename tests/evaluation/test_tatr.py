import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cptla.evaluation.pubtables_v2 import ImageManifestEntry
from cptla.evaluation.tatr import (
    associated_cropped_paths,
    cells_to_html,
    load_pdf_words,
    make_official_postprocessor,
    normalize_tatr_processor_size,
    normalize_words_to_image,
    tatr_objects_to_prediction,
)


def test_normalize_tatr_processor_size_preserves_official_max_resize() -> None:
    assert normalize_tatr_processor_size({"longest_edge": 800}) == {
        "shortest_edge": 800,
        "longest_edge": 800,
    }


def test_normalize_tatr_processor_size_preserves_modern_config() -> None:
    size = {"shortest_edge": 800, "longest_edge": 1333}
    assert normalize_tatr_processor_size(size) == size


def test_load_pdf_words_accepts_wrapped_and_direct_lists(tmp_path: Path) -> None:
    wrapped = tmp_path / "wrapped.json"
    direct = tmp_path / "direct.json"
    word = {"bbox": [1, 2, 3, 4], "text": "A"}
    wrapped.write_text(json.dumps({"words": [word]}), encoding="utf-8")
    direct.write_text(json.dumps([word]), encoding="utf-8")

    assert load_pdf_words(wrapped) == [word]
    assert load_pdf_words(direct) == [word]


def test_normalize_words_preserves_image_coordinates_and_clips_small_overflow() -> None:
    words = [{"bbox": [-0.25, 2, 100.2, 50], "text": "A"}]

    normalized = normalize_words_to_image(words, (100, 50))

    assert normalized[0]["bbox"] == [0.0, 2.0, 100.0, 50.0]
    assert normalized[0]["block_num"] == 0
    assert normalized[0]["line_num"] == 0
    assert normalized[0]["span_num"] == 0


@pytest.mark.parametrize(
    "bbox",
    [[4, 2, 1, 3], [-2, 0, 3, 4], [0, 0, 102, 4], [0, 0, 1]],
)
def test_normalize_words_rejects_invalid_or_large_overflow(bbox: list[float]) -> None:
    with pytest.raises(ValueError, match="word bbox"):
        normalize_words_to_image([{"bbox": bbox, "text": "A"}], (100, 50))


def test_associated_cropped_paths_require_exact_stem(tmp_path: Path) -> None:
    entry = ImageManifestEntry(
        image_id="PMC1_table_0.jpg",
        relative_path="PMC1_table_0.jpg",
        unit_id="PMC1_table_0",
        document_id="PMC1",
    )
    words_dir = tmp_path / "words"
    truth_dir = tmp_path / "tables"
    words_dir.mkdir()
    truth_dir.mkdir()
    words = words_dir / "PMC1_table_0_words.json"
    truth = truth_dir / "PMC1_table_0.json"
    words.write_text("[]", encoding="utf-8")
    truth.write_text("{}", encoding="utf-8")

    assert associated_cropped_paths(entry, words_dir, truth_dir) == (words, truth)


def test_associated_cropped_paths_reject_missing_truth(tmp_path: Path) -> None:
    entry = ImageManifestEntry(
        image_id="PMC1_table_0.jpg",
        relative_path="PMC1_table_0.jpg",
        unit_id="PMC1_table_0",
        document_id="PMC1",
    )
    words_dir = tmp_path / "words"
    truth_dir = tmp_path / "tables"
    words_dir.mkdir()
    truth_dir.mkdir()
    (words_dir / "PMC1_table_0_words.json").write_text("[]", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="truth"):
        associated_cropped_paths(entry, words_dir, truth_dir)


def test_cells_to_html_preserves_header_and_spans() -> None:
    cells = [
        {
            "row_nums": [0],
            "column_nums": [0, 1],
            "cell_text": "Header",
            "header": True,
        },
        {"row_nums": [1], "column_nums": [0], "cell_text": "A", "header": False},
        {"row_nums": [1], "column_nums": [1], "cell_text": "B", "header": False},
    ]

    assert cells_to_html(cells) == (
        '<table><thead><tr><th colspan="2">Header</th></tr></thead>'
        "<tbody><tr><td>A</td><td>B</td></tr></tbody></table>"
    )


def test_cells_to_html_creates_one_table_row_per_multilevel_header_row() -> None:
    cells = [
        {
            "row_nums": [0],
            "column_nums": [0, 1],
            "cell_text": "Group",
            "header": True,
        },
        {"row_nums": [1], "column_nums": [0], "cell_text": "A", "header": True},
        {"row_nums": [1], "column_nums": [1], "cell_text": "B", "header": True},
        {"row_nums": [2], "column_nums": [0], "cell_text": "1", "header": False},
        {"row_nums": [2], "column_nums": [1], "cell_text": "2", "header": False},
    ]

    root = ET.fromstring(cells_to_html(cells))

    assert [[cell.text for cell in row] for row in root.findall("./thead/tr")] == [
        ["Group"],
        ["A", "B"],
    ]
    assert root.find("./thead/tr/th").attrib == {"colspan": "2"}
    assert [[cell.text for cell in row] for row in root.findall("./tbody/tr")] == [
        ["1", "2"]
    ]


def test_tatr_adapter_passes_objects_and_direct_text_to_postprocessor() -> None:
    captured: dict[str, object] = {}

    def fake_postprocessor(
        boxes: list[list[float]],
        labels: list[int],
        scores: list[float],
        words: list[dict[str, object]],
        thresholds: dict[str, float],
    ) -> list[dict[str, object]]:
        captured.update(
            boxes=boxes,
            labels=labels,
            scores=scores,
            words=words,
            thresholds=thresholds,
        )
        return [
            {"row_nums": [0], "column_nums": [0], "cell_text": "Direct", "header": False}
        ]

    record = tatr_objects_to_prediction(
        image_id="PMC1_table_0.jpg",
        unit_id="PMC1_table_0",
        boxes=[[0, 0, 10, 10]],
        labels=[2],
        scores=[0.9],
        words=[{"bbox": [0, 0, 5, 5], "text": "Direct"}],
        thresholds={"table row": 0.5},
        postprocessor=fake_postprocessor,
        elapsed_sec=0.25,
    )

    assert captured["words"] == [{"bbox": [0, 0, 5, 5], "text": "Direct"}]
    assert record.tables_html == ["<table><tbody><tr><td>Direct</td></tr></tbody></table>"]
    assert record.status == "ok"
    assert record.raw_output is not None


def test_official_postprocessor_adapter_uses_tokens_inside_predicted_table() -> None:
    calls: dict[str, object] = {}

    class FakePostprocess:
        @staticmethod
        def apply_class_thresholds(boxes, labels, scores, class_names, thresholds):
            calls["class_names"] = class_names
            return boxes, scores, labels

        @staticmethod
        def iob(word_bbox, table_bbox):
            return 1 if word_bbox[0] < table_bbox[2] else 0

        @staticmethod
        def objects_to_cells(table, objects, words, class_names, thresholds):
            calls.update(table=table, objects=objects, words=words, thresholds=thresholds)
            return {}, [{"row_nums": [0], "column_nums": [0], "cell_text": "A"}], 1.0

    adapter = make_official_postprocessor(FakePostprocess)
    cells = adapter(
        [[0, 0, 10, 10]],
        [0],
        [0.9],
        [
            {"bbox": [1, 1, 2, 2], "text": "A"},
            {"bbox": [20, 1, 21, 2], "text": "outside"},
        ],
        {"table": 0.5, "no object": 10},
    )

    assert cells[0]["cell_text"] == "A"
    assert calls["words"] == [{"bbox": [1, 1, 2, 2], "text": "A"}]
