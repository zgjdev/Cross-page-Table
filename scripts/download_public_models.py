"""Download fixed public model files directly on the server with hash verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def validate_manifest(manifest):
    names = set()
    for model in manifest["models"]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", model["name"]) or model["name"] in names:
            raise ValueError("invalid or duplicate model name")
        names.add(model["name"])
        if not re.fullmatch(r"[0-9a-f]{40}", model["revision"]):
            raise ValueError("revision must be a fixed SHA")
        files = set()
        for file in model["files"]:
            name = file["path"]
            if not name or name in (".", "..") or "/" in name or "\\" in name or ":" in name:
                raise ValueError("only root-level model files allowed")
            if name in files or file["size"] < 0:
                raise ValueError("duplicate file or invalid size")
            files.add(name)
            if not (
                re.fullmatch(r"[0-9a-f]{64}", file.get("sha256") or "")
                or re.fullmatch(r"[0-9a-f]{40}", file.get("git_blob_id") or "")
            ):
                raise ValueError("authoritative checksum required")


def verify_file(path, expected):
    if path.stat().st_size != expected["size"]:
        raise ValueError("downloaded size mismatch")
    checksum = hashlib.sha256()
    blob = hashlib.sha1(f"blob {expected['size']}\0".encode())
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            checksum.update(chunk)
            blob.update(chunk)
    actual = checksum.hexdigest()
    if expected.get("sha256"):
        if actual != expected["sha256"]:
            raise ValueError("LFS checksum mismatch")
    elif blob.hexdigest() != expected["git_blob_id"]:
        raise ValueError("git blob checksum mismatch")
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("invalid run ID")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    if args.dry_run:
        print(
            json.dumps({m["name"]: sum(f["size"] for f in m["files"]) for m in manifest["models"]})
        )
        return 0
    root = Path.cwd().resolve()
    model_root = root / "models" / args.run_id
    log_root = root / "logs" / "model-downloads" / args.run_id
    if model_root.exists() or log_root.exists():
        raise FileExistsError("run directories already exist; preserve and use a new run ID")
    model_root.mkdir(parents=True, exist_ok=False)
    log_root.mkdir(parents=True, exist_ok=False)
    for key, value in {
        "HF_HOME": log_root / "hf-home",
        "XDG_CACHE_HOME": log_root / "xdg-cache",
        "TMPDIR": log_root / "tmp",
    }.items():
        value.mkdir()
        os.environ[key] = str(value)
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"
    from huggingface_hub import hf_hub_download

    with (log_root / "events.jsonl").open("x", encoding="utf-8") as events:

        def emit(event, **fields):
            row = {"utc": datetime.now(UTC).isoformat(), "event": event, **fields}
            events.write(json.dumps(row) + "\n")
            events.flush()
            print(json.dumps(row), flush=True)

        emit(
            "start",
            pid=os.getpid(),
            command=sys.argv,
            manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        )
        results = []
        for model in manifest["models"]:
            destination = model_root / model["name"]
            destination.mkdir(exist_ok=False)
            result = {
                "name": model["name"],
                "repo": model["repo"],
                "revision": model["revision"],
                "path": str(destination),
                "verified": [],
                "status": "downloading",
            }
            try:
                for file in model["files"]:
                    emit("file_start", model=model["name"], file=file["path"], size=file["size"])
                    started = time.monotonic()
                    path = hf_hub_download(
                        model["repo"],
                        filename=file["path"],
                        revision=model["revision"],
                        local_dir=destination,
                        endpoint="https://hf-mirror.com",
                        token=False,
                    )
                    checksum = verify_file(Path(path), file)
                    result["verified"].append(
                        {"file": file["path"], "sha256": checksum, "size": file["size"]}
                    )
                    emit(
                        "file_verified",
                        model=model["name"],
                        file=file["path"],
                        sha256=checksum,
                        seconds=round(time.monotonic() - started, 2),
                    )
                result["status"] = "complete"
                with (destination / "download-manifest.json").open("x", encoding="utf-8") as out:
                    json.dump(result, out, indent=2)
                emit("model_complete", model=model["name"], files=len(result["verified"]))
            except Exception as error:
                result["status"] = "failed"
                result["error_type"] = type(error).__name__
                emit("model_failed", model=model["name"], error_type=type(error).__name__)
            results.append(result)
        status = 0 if all(r["status"] == "complete" for r in results) else 1
        with (log_root / "summary.json").open("x", encoding="utf-8") as out:
            json.dump({"models": results, "status": status}, out, indent=2)
        emit("end", status=status)
        return status


if __name__ == "__main__":
    raise SystemExit(main())
