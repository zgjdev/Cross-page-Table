import pytest

from scripts.adapt_paddle_document_predictions import adapt_run


def test_existing_output_refused_before_loading_any_inputs(tmp_path):
    marker = tmp_path / "keep"
    marker.write_bytes(b"unchanged")
    with pytest.raises(FileExistsError):
        adapt_run(tmp_path / "missing", tmp_path / "missing", tmp_path / "missing", tmp_path)
    assert marker.read_bytes() == b"unchanged"
