import json
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

try:
    import pylcs  # noqa: F401
except ImportError:
    pylcs_stub = types.ModuleType("pylcs")

    def lcs_sequence_length(left: str, right: str) -> int:
        previous = [0] * (len(right) + 1)
        for left_character in left:
            current = [0]
            for index, right_character in enumerate(right, start=1):
                current.append(
                    previous[index - 1] + 1
                    if left_character == right_character
                    else max(previous[index], current[-1])
                )
            previous = current
        return previous[-1]

    pylcs_stub.lcs_sequence_length = lcs_sequence_length
    sys.modules["pylcs"] = pylcs_stub

from scripts import build_table_case_report as script

HTML = "<table><tr><td>A</td></tr></table>"


def _fixture_config(tmp_path: Path) -> script.CaseReportConfig:
    images = tmp_path / "images"
    truth = tmp_path / "truth"
    images.mkdir()
    truth.mkdir()
    (images / "x.jpg").write_bytes(b"image")
    (truth / "x.json").write_text(json.dumps({"html": HTML}), encoding="utf-8")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "image_id": "x.jpg",
                "relative_path": "x.jpg",
                "unit_id": "x",
                "document_id": "PMC1",
                "page_number": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        json.dumps(
            {
                "image_id": "x.jpg",
                "unit_id": "x",
                "status": "ok",
                "tables_html": [HTML],
                "elapsed_sec": 1,
                "error": None,
                "raw_output": None,
                "warnings": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return script.CaseReportConfig(
        manifest=manifest,
        predictions=[predictions],
        truth_dir=truth,
        images_dir=images,
        collection="cropped_tables",
        output_root=tmp_path / "reports",
        run_name="tatr-cropped-case-report",
        sample_size=1,
        seed=17,
    )


def test_run_builds_timestamped_report_from_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _fixture_config(tmp_path)
    monkeypatch.setattr(
        script, "utc_run_id", lambda name: f"20260924T120000Z-{name}"
    )

    assert script.run(config) == 0
    report = tmp_path / "reports" / "20260924T120000Z-tatr-cropped-case-report"
    assert (report / "index.html").is_file()
    payload = json.loads((report / "cases.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["coverage"] == 1


@pytest.mark.parametrize("failure", ["missing", "duplicate", "image"])
def test_run_rejects_incomplete_or_ambiguous_inputs(
    tmp_path: Path, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _fixture_config(tmp_path)
    monkeypatch.setattr(script, "utc_run_id", lambda name: f"fixed-{name}")
    if failure == "missing":
        config.predictions[0].write_text("", encoding="utf-8")
    elif failure == "duplicate":
        row = config.predictions[0].read_text(encoding="utf-8")
        config.predictions[0].write_text(row + row, encoding="utf-8")
    else:
        (config.images_dir / "x.jpg").unlink()

    with pytest.raises((ValueError, FileNotFoundError)):
        script.run(config)
    assert not config.output_root.exists()


def test_run_refuses_existing_timestamped_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _fixture_config(tmp_path)
    monkeypatch.setattr(script, "utc_run_id", lambda name: f"fixed-{name}")
    (config.output_root / "fixed-tatr-cropped-case-report").mkdir(parents=True)

    with pytest.raises(FileExistsError):
        script.run(config)


def test_config_rejects_full_documents() -> None:
    with pytest.raises(ValidationError, match="cropped_tables"):
        script.CaseReportConfig(
            manifest="manifest.jsonl",
            predictions=["predictions.jsonl"],
            truth_dir="truth",
            images_dir="images",
            collection="full_documents",
            output_root="reports",
            run_name="report",
            sample_size=60,
            seed=17,
        )
