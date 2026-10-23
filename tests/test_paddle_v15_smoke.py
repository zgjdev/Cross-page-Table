import json

import pytest

from scripts.run_paddle_v15_smoke import configure_cache, run_documents


class Result:
    def __init__(self, data):
        self.json = {"res": data}


class FakePipeline:
    def __init__(self, missing=False):
        self.inputs = []
        self.modes = []
        self.missing = missing

    def predict_iter(self, path):
        self.inputs.append(path)
        for i in range(1 if self.missing else 2):
            yield Result(
                {
                    "page_index": i,
                    "page_count": 2,
                    "parsing_res_list": [{"block_label": "table", "block_content": "<table/>"}],
                }
            )

    def restructure_pages(self, pages, **kwargs):
        self.modes.append(kwargs["merge_tables"])
        assert pages[0]["res"]["parsing_res_list"][0]["block_content"] == "<table/>"
        if kwargs["merge_tables"]:
            pages[0]["res"]["parsing_res_list"][0]["block_content"] = "changed"
        return [Result(page["res"]) for page in pages]


def manifest():
    return {"pdfs": [{"document_id": "PMC1", "file": "PMC1.pdf", "pages": 2}]}


def test_same_prediction_used_for_both_restructure_modes(tmp_path):
    pipeline = FakePipeline()
    out = tmp_path / "new"
    summary = run_documents(pipeline, tmp_path, manifest(), out)
    assert len(pipeline.inputs) == 1
    assert pipeline.modes == [False, True]
    assert summary["status"] == "completed"
    assert summary["pages"] == 2
    raw = [json.loads(line) for line in (out / "pages.jsonl").read_text().splitlines()]
    assert raw[0]["prediction"]["res"]["parsing_res_list"][0]["block_content"] == "<table/>"
    assert (out / "PMC1/native_merge.json").exists()
    assert (out / "PMC1/no_merge.json").exists()


def test_missing_pages_fails_with_preserved_prefix(tmp_path):
    out = tmp_path / "new"
    with pytest.raises(ValueError, match="coverage"):
        run_documents(FakePipeline(missing=True), tmp_path, manifest(), out)
    assert len((out / "pages.jsonl").read_text().splitlines()) == 1
    assert json.loads((out / "summary.json").read_text())["status"] == "failed"
    assert not (out / "PMC1/native_merge.json").exists()


def test_existing_output_rejected_before_inference(tmp_path):
    pipeline = FakePipeline()
    with pytest.raises(FileExistsError):
        run_documents(pipeline, tmp_path, manifest(), tmp_path)
    assert pipeline.inputs == []


def test_cache_paths_are_explicit_and_project_local(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    keys = (
        "PADDLE_PDX_CACHE_HOME",
        "PADDLE_HOME",
        "PPNLP_HOME",
        "CUDA_CACHE_PATH",
        "HF_HOME",
        "MODELSCOPE_CACHE",
        "XDG_CACHE_HOME",
        "TMPDIR",
        "MPLCONFIGDIR",
        "TRITON_CACHE_DIR",
        "TORCH_HOME",
        "FLAGS_jit_kernel_cache_path",
        "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK",
        "HF_HUB_OFFLINE",
        "HF_HUB_DISABLE_TELEMETRY",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    configure_cache(tmp_path / "cache")
    for key in keys[:-3]:
        assert Path(os.environ[key]).is_relative_to(tmp_path)
        assert Path(os.environ[key]).is_dir()
    assert os.environ["HF_HUB_OFFLINE"] == "1"
