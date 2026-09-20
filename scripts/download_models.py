"""Download pinned public model snapshots and write a reproducibility manifest."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

MODELS = {
    "tatr-v1.1-pub": "microsoft/table-transformer-structure-recognition-v1.1-pub",
    "dots-ocr": "rednote-hilab/dots.ocr",
    "qwen2.5-vl-3b": "Qwen/Qwen2.5-VL-3B-Instruct",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=[*MODELS, "all"], default=["all"])
    parser.add_argument("--root", type=Path, default=Path("checkpoints"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("artifacts/model-manifests"))
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--retries", type=int, default=5)
    args = parser.parse_args()
    names = list(MODELS) if "all" in args.models else args.models
    api = HfApi()
    args.root.mkdir(parents=True, exist_ok=True)
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        repo_id = MODELS[name]
        info = api.model_info(repo_id, files_metadata=True)
        for attempt in range(1, args.retries + 1):
            try:
                path = snapshot_download(
                    repo_id=repo_id,
                    revision=info.sha,
                    local_dir=args.root / name,
                    max_workers=args.max_workers,
                )
                break
            except Exception:
                if attempt == args.retries:
                    raise
                delay = min(60, 5 * 2 ** (attempt - 1))
                print(f"download attempt {attempt} failed; retrying in {delay}s", flush=True)
                time.sleep(delay)
        files = list((args.root / name).rglob("*"))
        manifest = {
            "model_name": name,
            "repo_id": repo_id,
            "resolved_revision": info.sha,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "local_path": str(path),
            "file_count": sum(p.is_file() for p in files),
            "total_bytes": sum(p.stat().st_size for p in files if p.is_file()),
            "smoke_test_status": "not_run",
        }
        (args.manifest_dir / f"{name}.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
