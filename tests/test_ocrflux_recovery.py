import pytest

from cptla.evaluation.ocrflux_recovery import initialization_retry_allowed, recovery_next

ERROR = (
    "AssertionError: Error in memory profiling. Initial used memory 33, currently used memory 32."
)


def test_only_initialization_profiling_failure_can_retry():
    assert initialization_retry_allowed(
        dict(status="failed", pages=0, documents=[], error=ERROR), 0
    )
    assert not initialization_retry_allowed(
        dict(status="failed", pages=0, documents=[], error="CUDA out of memory"), 0
    )
    assert not initialization_retry_allowed(
        dict(status="failed", pages=0, documents=[], error=ERROR), 1
    )
    assert not initialization_retry_allowed(
        dict(status="failed", pages=1, documents=[], error=ERROR), 0
    )


def test_retries_bounded_per_document_and_in_total():
    state = {}
    for _ in range(3):
        state = recovery_next(state, "PMC1")
    with pytest.raises(RuntimeError, match="limit"):
        recovery_next(state, "PMC1")
    assert recovery_next(state, "PMC2")["PMC2"] == 1
    with pytest.raises(RuntimeError, match="limit"):
        recovery_next({"PMC1": 20}, "PMC2")


@pytest.mark.parametrize("known", [True, False])
def test_supervisor_only_launches_for_known_failure(tmp_path, monkeypatch, known):
    import importlib.util
    import json
    import subprocess
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "recovery_cli", Path("scripts/run_ocrflux_recovery.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prep = tmp_path / "artifacts/ocrflux-prep/20261030T015400Z/acceptance"
    prep.mkdir(parents=True)
    (prep / "final-full-preflight-v3.json").write_text(json.dumps({"protocol": {"source_sha": {}}}))
    old = tmp_path / "artifacts/ocrflux-document-runs/20261030T032500Z-ocrflux-val-full"
    child = old / "documents/PMC1/predictions"
    (child / "raw").mkdir(parents=True)
    (child / "summary.json").write_text(
        json.dumps(
            dict(
                status="failed",
                pages=0,
                documents=[],
                error=ERROR if known else "CUDA out of memory",
            )
        )
    )
    (old / "summary.json").write_text(json.dumps({"results": {}}))
    (old / "run-manifest.json").write_text(
        json.dumps({"documents": [{"document_id": "PMC1", "pages": 1}]})
    )
    monkeypatch.setattr(
        sys, "argv", ["recovery", "--project", str(tmp_path), "--supervisor-id", "test"]
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: "40000")
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    calls = []

    def fake(command, **kwargs):
        calls.append(command)
        output = tmp_path / "artifacts/ocrflux-document-runs/test-a001"
        output.mkdir()
        (output / "export-complete.json").write_text("{}")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake)
    if known:
        module.main()
        assert len(calls) == 1 and "--resume" in calls[0]
    else:
        with pytest.raises(RuntimeError, match="not a pre-generation"):
            module.main()
        assert not calls
