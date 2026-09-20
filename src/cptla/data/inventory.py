from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from huggingface_hub import HfApi


def summarize_files(files: Iterable[tuple[str, int]]) -> dict[str, object]:
    rows = list(files)
    extensions = Counter(Path(path).suffix.lower() or "<none>" for path, _ in rows)
    return {
        "file_count": len(rows),
        "total_bytes": sum(size for _, size in rows),
        "extensions": dict(sorted(extensions.items())),
    }


def fetch_inventory(repo_id: str, revision: str = "main") -> dict[str, object]:
    info = HfApi().dataset_info(repo_id=repo_id, revision=revision, files_metadata=True)
    files = sorted((item.rfilename, int(item.size or 0)) for item in info.siblings)
    return {
        "repo_id": repo_id,
        "requested_revision": revision,
        "resolved_sha": info.sha,
        "files": [{"path": path, "size": size} for path, size in files],
        "summary": summarize_files(files),
    }
