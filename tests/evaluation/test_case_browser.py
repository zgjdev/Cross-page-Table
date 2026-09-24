import json
import os
import subprocess
import sys
import threading
import types
import urllib.request
from pathlib import Path

import pytest

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

from cptla.evaluation.case_browser import LiveCaseBrowser
from scripts.serve_table_case_browser import create_server

HTML_A = "<table><tr><td>A</td></tr></table>"
HTML_B = "<table><tr><td>B</td></tr></table>"


def _browser(tmp_path: Path) -> LiveCaseBrowser:
    images = tmp_path / "images"
    truth = tmp_path / "truth"
    images.mkdir()
    truth.mkdir()
    manifest_rows = []
    prediction_rows = []
    for index, table_html in enumerate((HTML_A, HTML_B)):
        unit_id = f"PMC1_table_{index}"
        image_id = f"{unit_id}.jpg"
        (images / image_id).write_bytes(f"image-{index}".encode())
        (truth / f"{unit_id}.json").write_text(
            json.dumps({"id": unit_id, "html": table_html}), encoding="utf-8"
        )
        manifest_rows.append(
            {
                "image_id": image_id,
                "relative_path": image_id,
                "unit_id": unit_id,
                "document_id": "PMC1",
                "page_number": None,
            }
        )
        prediction_rows.append(
            {
                "image_id": image_id,
                "unit_id": unit_id,
                "status": "ok",
                "tables_html": [table_html],
                "elapsed_sec": 1,
                "error": None,
                "raw_output": None,
                "warnings": [],
            }
        )
    manifest = tmp_path / "manifest.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    manifest.write_text(
        "".join(json.dumps(row) + "\n" for row in manifest_rows), encoding="utf-8"
    )
    predictions.write_text(
        "".join(json.dumps(row) + "\n" for row in prediction_rows), encoding="utf-8"
    )
    return LiveCaseBrowser(
        manifest_path=manifest,
        prediction_paths=[predictions],
        truth_dir=truth,
        images_dir=images,
        session_dir=tmp_path / "session",
        cache_size=2,
    )


def test_browser_loads_and_scores_only_requested_case(tmp_path: Path) -> None:
    browser = _browser(tmp_path)

    assert browser.cache_entries == 0
    case = browser.get_case(0)

    assert browser.total == 2
    assert browser.cache_entries == 1
    assert case["unit_id"] == "PMC1_table_0"
    assert case["position"] == 1
    assert case["grits_top"] == 1
    assert 'class="comparison-table truth"' in case["truth_table_html"]
    assert browser.resolve_index("PMC1_table_1") == 1
    assert browser.resolve_index("2") == 1


def test_browser_logs_views_and_rejects_out_of_range(tmp_path: Path) -> None:
    browser = _browser(tmp_path)
    case = browser.get_case(1)
    browser.record_view(case)

    event = json.loads((browser.session_dir / "viewed-cases.jsonl").read_text())
    assert event["unit_id"] == "PMC1_table_1"
    assert event["index"] == 1
    with pytest.raises(IndexError):
        browser.get_case(2)


def test_http_server_exposes_live_case_and_image(tmp_path: Path) -> None:
    browser = _browser(tmp_path)
    server = create_server(browser, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/case?index=0") as response:
            payload = json.load(response)
        assert payload["unit_id"] == "PMC1_table_0"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/image?index=1") as response:
            assert response.read() == b"image-1"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
            page = response.read().decode()
        assert "下一个" in page
        assert "localStorage" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_server_refuses_non_loopback_binding(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback"):
        create_server(_browser(tmp_path), host="0.0.0.0", port=8765)


def test_script_entrypoint_can_load_from_repository_root(tmp_path: Path) -> None:
    (tmp_path / "pylcs.py").write_text(
        "def lcs_sequence_length(left, right): return 0\n", encoding="utf-8"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "scripts/serve_table_case_browser.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert "--config" in result.stdout
