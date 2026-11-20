import importlib.util
from pathlib import Path

import pytest


def probe():
    path = Path(__file__).parents[1] / "scripts/probe_reconstruction_structure_prefix.py"
    assert path.exists(), "structure prefix probe is not implemented"
    spec = importlib.util.spec_from_file_location("structure_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nodes_use_only_prediction_and_normalize_positions():
    records = probe().prediction_nodes(
        [
            {
                "prediction_html": "<table><tr><td>A</td><td>B</td></tr></table>",
                "image_path": "a.png",
            },
            {"prediction_html": "<table><tr><td>C</td></tr></table>", "image_path": "b.png"},
        ]
    )
    assert records == [
        ("A", [0.0, 1.0, 0.0, 0.5, 0.0]),
        ("B", [0.0, 1.0, 0.5, 1.0, 0.0]),
        ("C", [0.0, 1.0, 0.0, 1.0, 1.0]),
    ]


def test_rejects_invalid_prediction_without_target_fallback():
    with pytest.raises(ValueError):
        probe().prediction_nodes([{"prediction_html": "<table>", "image_path": "a.png"}])


def test_target_fields_are_forbidden_in_feature_input():
    with pytest.raises(ValueError):
        probe().prediction_nodes(
            [
                {
                    "prediction_html": "<table><tr><td>A</td></tr></table>",
                    "image_path": "a.png",
                    "target_html": "GT",
                }
            ]
        )
