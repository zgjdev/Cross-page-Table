from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionRecord(BaseModel):
    """One terminal inference result for one manifest image."""

    model_config = ConfigDict(extra="forbid")

    image_id: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    status: Literal["ok", "error"]
    tables_html: list[str]
    elapsed_sec: float = Field(ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def validate_error_state(self) -> Self:
        if self.status == "error" and not self.error:
            raise ValueError("error is required when status is error")
        if self.status == "ok" and self.error is not None:
            raise ValueError("error must be empty when status is ok")
        return self


class CoverageReport(BaseModel):
    """Set-level comparison between a frozen input manifest and predictions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    expected: int = Field(ge=0)
    seen: int = Field(ge=0)
    missing: list[str]
    extra: list[str]
    duplicates: list[str]

    @classmethod
    def from_ids(cls, expected_ids: list[str], seen_ids: list[str]) -> CoverageReport:
        expected_counts = Counter(expected_ids)
        seen_counts = Counter(seen_ids)
        duplicates = sorted(
            identifier
            for identifier in expected_counts.keys() | seen_counts.keys()
            if expected_counts[identifier] > 1 or seen_counts[identifier] > 1
        )
        expected_set = set(expected_counts)
        seen_set = set(seen_counts)
        return cls(
            expected=len(expected_set),
            seen=len(seen_set),
            missing=sorted(expected_set - seen_set),
            extra=sorted(seen_set - expected_set),
            duplicates=duplicates,
        )

    @property
    def is_complete(self) -> bool:
        return not (self.missing or self.extra or self.duplicates)


class RunCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected: int = Field(ge=0)
    seen: int = Field(ge=0)
    failed: int = Field(ge=0)


class RunManifest(BaseModel):
    """Minimum provenance required to reproduce and audit one evaluation run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    created_at_utc: datetime
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    dataset_name: str = Field(min_length=1)
    dataset_split: Literal["val"]
    dataset_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    input_manifest_path: Path
    input_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_name: str = Field(min_length=1)
    model_repo_id: str = Field(min_length=1)
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    input_track: Literal["pdf-text-assisted", "image-only"]
    python_version: str = Field(min_length=1)
    pytorch_version: str = Field(min_length=1)
    transformers_version: str = Field(min_length=1)
    cuda_version: str = Field(min_length=1)
    grits_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    gpu_model: str = Field(min_length=1)
    visible_devices: list[str] = Field(min_length=1)
    command: list[str] = Field(min_length=1)
    seed: int = Field(ge=0)
    predictions_path: Path
    logs_path: Path
    metrics_path: Path
    coverage: RunCoverage

    @model_validator(mode="after")
    def validate_utc_timestamp(self) -> Self:
        if self.created_at_utc.utcoffset() is None:
            raise ValueError("created_at_utc must be timezone-aware")
        if self.created_at_utc.utcoffset().total_seconds() != 0:
            raise ValueError("created_at_utc must use UTC")
        return self

    def validate_manifest_paths(self, base_dir: Path) -> list[Path]:
        paths = (
            self.input_manifest_path,
            self.metrics_path,
            self.predictions_path,
            self.logs_path,
        )
        resolved = [path if path.is_absolute() else base_dir / path for path in paths]
        return sorted((path for path in resolved if not path.exists()), key=lambda path: path.name)
