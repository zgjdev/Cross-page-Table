from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from cptla.evaluation.contracts import RunManifest


def credential_presence(names: list[str], environ: Mapping[str, str]) -> dict[str, bool]:
    return {name: bool(environ.get(name)) for name in names}


def build_run_manifest(
    spec: dict[str, object],
    *,
    git_commit: str,
    created_at: datetime,
    versions: dict[str, str],
    credentials: dict[str, bool],
) -> RunManifest:
    return RunManifest.model_validate(
        {
            **spec,
            "created_at_utc": created_at,
            "git_commit": git_commit,
            "python_version": versions["python"],
            "pytorch_version": versions["pytorch"],
            "transformers_version": versions["transformers"],
            "cuda_version": versions["cuda"],
            "credential_presence": credentials,
        }
    )
