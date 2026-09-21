"""Combine a run specification with runtime provenance without exposing credentials."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from cptla.evaluation.provenance import build_run_manifest, credential_presence


def _version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credential-name", action="append", default=["HF_TOKEN"])
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    cuda_version = "not-installed"
    try:
        import torch

        cuda_version = torch.version.cuda or "not-available"
    except ImportError:
        pass
    manifest = build_run_manifest(
        spec,
        git_commit=git_commit,
        created_at=datetime.now(UTC),
        versions={
            "python": platform.python_version(),
            "pytorch": _version("torch"),
            "transformers": _version("transformers"),
            "cuda": cuda_version,
        },
        credentials=credential_presence(args.credential_name, os.environ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
