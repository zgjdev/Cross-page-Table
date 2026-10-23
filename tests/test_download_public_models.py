import hashlib
from pathlib import Path

import pytest

from scripts.download_public_models import validate_manifest, verify_file


def spec(payload=b"abc"):
    return {
        "path": "config.json",
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "git_blob_id": None,
    }


def test_checksum_and_size_must_both_match(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes(b"abc")
    assert verify_file(path, spec()) == hashlib.sha256(b"abc").hexdigest()
    with pytest.raises(ValueError):
        verify_file(path, spec(b"abd"))
    with pytest.raises(ValueError):
        verify_file(path, spec(b"ab"))


def test_git_blob_checksum_for_small_files(tmp_path):
    path = tmp_path / "config.json"
    path.write_bytes(b"abc")
    file = spec()
    file["sha256"] = None
    file["git_blob_id"] = hashlib.sha1(b"blob 3\0abc").hexdigest()
    verify_file(path, file)
    file["git_blob_id"] = "0" * 40
    with pytest.raises(ValueError):
        verify_file(path, file)


@pytest.mark.parametrize("name", ["../escape", "/tmp/escape", "a/b", "a\\b"])
def test_manifest_rejects_unsafe_paths(name):
    file = spec()
    file["path"] = name
    manifest = {
        "models": [{"name": "model", "repo": "org/repo", "revision": "a" * 40, "files": [file]}]
    }
    with pytest.raises(ValueError):
        validate_manifest(manifest)


def test_real_manifest_has_fixed_versions_and_authoritative_hashes():
    import json

    manifest = json.loads(Path("configs/public-model-downloads-2026-10-23.json").read_text())
    validate_manifest(manifest)
    assert len(manifest["models"]) == 3
