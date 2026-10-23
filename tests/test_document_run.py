import hashlib
import json

import pytest

from cptla.evaluation.document_run import read_frozen_manifest, run_batch


def document(name):
    return {"document_id": name, "pages": 2}


def worker(root, calls, fail=None):
    def run(doc):
        calls.append(doc["document_id"])
        if doc["document_id"] == fail:
            raise RuntimeError("simulated interruption")
        path = root / (doc["document_id"] + ".txt")
        path.write_text("complete")
        return {
            "document_id": doc["document_id"],
            "pages": doc["pages"],
            "files": {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()},
        }

    return run


def test_resume_skips_only_fully_verified_documents(tmp_path):
    docs = [document("PMC1"), document("PMC2")]
    calls = []
    protocol = {"fixed_manifest": "abc", "model": "pinned"}
    first = tmp_path / "first"
    with pytest.raises(RuntimeError):
        run_batch(docs, first, protocol, worker(tmp_path, calls, "PMC2"), project=tmp_path)
    assert (first / "checkpoints/PMC1.json").exists()
    assert not (first / "checkpoints/PMC2.json").exists()
    calls.clear()
    result = run_batch(
        docs,
        tmp_path / "second",
        protocol,
        worker(tmp_path, calls),
        project=tmp_path,
        resume=[first],
    )
    assert calls == ["PMC2"]
    assert result["status"] == "completed"
    assert result["pages"] == 4
    assert result["resumed_documents"] == 1


def test_changed_artifact_or_protocol_rejected_before_any_work(tmp_path):
    docs = [document("PMC1")]
    first = tmp_path / "first"
    run_batch(docs, first, {"model": "a"}, worker(tmp_path, []), project=tmp_path)
    with pytest.raises(ValueError, match="protocol"):
        run_batch(
            docs,
            tmp_path / "second",
            {"model": "b"},
            worker(tmp_path, []),
            project=tmp_path,
            resume=[first],
        )
    (tmp_path / "PMC1.txt").write_text("changed")
    with pytest.raises(ValueError, match="SHA"):
        run_batch(
            docs,
            tmp_path / "third",
            {"model": "a"},
            worker(tmp_path, []),
            project=tmp_path,
            resume=[first],
        )
    assert not (tmp_path / "second").exists()
    assert not (tmp_path / "third").exists()


def test_frozen_manifest_checks_counts_digest_and_non_table_pages(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    rows = []
    for i in range(2):
        filename = f"PMC1_page_{i}.jpg"
        (images / filename).write_bytes(b"\xff\xd8image")
        rows.append(
            {
                "document_id": "PMC1",
                "unit_id": "PMC1",
                "page_number": i,
                "image_id": filename,
                "relative_path": filename,
            }
        )
    path = tmp_path / "manifest.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert read_frozen_manifest(path, images, digest, 2, 1) == [document("PMC1")]
    with pytest.raises(ValueError):
        read_frozen_manifest(path, images, digest, 3, 1)
    with pytest.raises(ValueError):
        read_frozen_manifest(path, images, "bad", 2, 1)


def test_existing_batch_directory_is_never_overwritten(tmp_path):
    with pytest.raises(FileExistsError):
        run_batch([document("PMC1")], tmp_path, {}, worker(tmp_path, []), project=tmp_path)
