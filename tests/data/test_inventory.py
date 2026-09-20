import importlib
import sys
from types import SimpleNamespace

from cptla.data import inventory
from cptla.data.inventory import summarize_files


def test_summarize_files_groups_extensions_and_sizes() -> None:
    summary = summarize_files(
        [("README.md", 100), ("full_documents/train/a.json", 300), ("images/a.png", 600)]
    )

    assert summary["file_count"] == 3
    assert summary["total_bytes"] == 1000
    assert summary["extensions"] == {".json": 1, ".md": 1, ".png": 1}


def test_fetch_inventory_resolves_revision_and_sorts_files(monkeypatch) -> None:
    class FakeApi:
        def dataset_info(self, *, repo_id: str, revision: str, files_metadata: bool):
            assert (repo_id, revision, files_metadata) == ("owner/data", "v1", True)
            return SimpleNamespace(
                sha="abc123",
                siblings=[
                    SimpleNamespace(rfilename="z.json", size=20),
                    SimpleNamespace(rfilename="README.md", size=None),
                ],
            )

    monkeypatch.setattr(inventory, "HfApi", FakeApi, raising=False)

    result = inventory.fetch_inventory("owner/data", "v1")

    assert result == {
        "repo_id": "owner/data",
        "requested_revision": "v1",
        "resolved_sha": "abc123",
        "files": [
            {"path": "README.md", "size": 0},
            {"path": "z.json", "size": 20},
        ],
        "summary": {"file_count": 2, "total_bytes": 20, "extensions": {".json": 1, ".md": 1}},
    }


def test_audit_script_writes_manifest_and_report(tmp_path, monkeypatch) -> None:
    audit = importlib.import_module("scripts.audit_pubtables_v2")
    manifest = tmp_path / "manifest.json"
    config = tmp_path / "config.yaml"
    report = tmp_path / "report.md"
    config.write_text(
        "repo_id: owner/data\n"
        "revision: v1\n"
        f"manifest_path: {manifest.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        audit,
        "fetch_inventory",
        lambda repo_id, revision: {
            "repo_id": repo_id,
            "requested_revision": revision,
            "resolved_sha": "abc123",
            "files": [{"path": "README.md", "size": 10}],
            "summary": {"file_count": 1, "total_bytes": 10, "extensions": {".md": 1}},
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["audit_pubtables_v2.py", "--config", str(config), "--report", str(report)],
    )

    assert audit.main() == 0
    assert '"resolved_sha": "abc123"' in manifest.read_text(encoding="utf-8")
    assert "- Files: 1" in report.read_text(encoding="utf-8")
