"""Build a deterministic static case-analysis report for Cropped Tables predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for dependency_path in (REPOSITORY_ROOT / "src", REPOSITORY_ROOT / "third_party/grits-main"):
    if str(dependency_path) not in sys.path:
        sys.path.insert(0, str(dependency_path))

from cptla.evaluation.case_analysis import (  # noqa: E402
    add_complexity_tags,
    analyze_cropped_case,
    stratified_sample,
)
from cptla.evaluation.case_report import write_case_report  # noqa: E402
from cptla.evaluation.contracts import CoverageReport, PredictionRecord  # noqa: E402
from cptla.evaluation.pubtables_v2 import ImageManifestEntry  # noqa: E402
from cptla.evaluation.scoring import load_truth_directory  # noqa: E402


class CaseReportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: Path
    predictions: list[Path] = Field(min_length=1)
    truth_dir: Path
    images_dir: Path
    collection: Literal["cropped_tables"]
    output_root: Path
    run_name: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    sample_size: int = Field(default=60, ge=1)
    seed: int = Field(default=20260924, ge=0)
    include_ids: list[str] = Field(default_factory=list)


def _resolve(path: Path, base: Path) -> Path:
    return path if path.is_absolute() else base / path


def load_config(path: Path, *, project_root: Path | None = None) -> CaseReportConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("case report config must be a YAML mapping")
    config = CaseReportConfig.model_validate(raw)
    base = (project_root or Path.cwd()).resolve()
    return config.model_copy(
        update={
            "manifest": _resolve(config.manifest, base),
            "predictions": [_resolve(item, base) for item in config.predictions],
            "truth_dir": _resolve(config.truth_dir, base),
            "images_dir": _resolve(config.images_dir, base),
            "output_root": _resolve(config.output_root, base),
        }
    )


def utc_run_id(name: str) -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> list[ImageManifestEntry]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [
        ImageManifestEntry.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_predictions(paths: list[Path]) -> list[PredictionRecord]:
    records: list[PredictionRecord] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(PredictionRecord.model_validate_json(line))
            except ValueError as error:
                raise ValueError(f"invalid prediction at {path}:{line_number}: {error}") from error
    return records


def _validate_inputs(
    config: CaseReportConfig,
    manifest: list[ImageManifestEntry],
    predictions: list[PredictionRecord],
) -> None:
    coverage = CoverageReport.from_ids(
        [entry.image_id for entry in manifest],
        [record.image_id for record in predictions],
    )
    if not coverage.is_complete:
        raise ValueError(
            "case report requires exact prediction coverage: "
            f"missing={len(coverage.missing)}, extra={len(coverage.extra)}, "
            f"duplicates={len(coverage.duplicates)}"
        )
    if not config.truth_dir.is_dir():
        raise NotADirectoryError(config.truth_dir)
    if not config.images_dir.is_dir():
        raise NotADirectoryError(config.images_dir)
    missing_images = [
        entry.relative_path
        for entry in manifest
        if not (config.images_dir / entry.relative_path).is_file()
    ]
    if missing_images:
        raise FileNotFoundError(f"missing {len(missing_images)} images; first={missing_images[0]}")


def run(config: CaseReportConfig) -> int:
    run_id = utc_run_id(config.run_name)
    output_dir = config.output_root / run_id
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest = _load_manifest(config.manifest)
    predictions = _load_predictions(config.predictions)
    _validate_inputs(config, manifest, predictions)
    truth_by_unit = load_truth_directory(config.truth_dir, config.collection)
    prediction_by_image = {record.image_id: record for record in predictions}
    missing_truth = sorted({entry.unit_id for entry in manifest} - truth_by_unit.keys())
    if missing_truth:
        raise ValueError(f"missing truth for {len(missing_truth)} units; first={missing_truth[0]}")
    multi_truth = sorted(
        entry.unit_id for entry in manifest if len(truth_by_unit[entry.unit_id]) != 1
    )
    if multi_truth:
        raise ValueError(f"cropped table units require one truth table; first={multi_truth[0]}")

    cases = []
    for index, entry in enumerate(manifest, start=1):
        cases.append(
            analyze_cropped_case(
                entry,
                prediction_by_image[entry.image_id],
                truth_by_unit[entry.unit_id][0],
            )
        )
        if index % 100 == 0 or index == len(manifest):
            print(
                json.dumps(
                    {"stage": "analyze", "completed": index, "total": len(manifest)},
                    ensure_ascii=False,
                ),
                flush=True,
            )
    cases, thresholds = add_complexity_tags(cases)
    selected = stratified_sample(
        cases,
        sample_size=config.sample_size,
        seed=config.seed,
        include_ids=config.include_ids,
    )
    records_by_unit = {record.unit_id: record for record in predictions}
    metadata: dict[str, object] = {
        "run_id": run_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "collection": config.collection,
        "coverage": len(manifest),
        "sample_size": len(selected),
        "seed": config.seed,
        "row_p90": thresholds.row_p90,
        "column_p90": thresholds.column_p90,
        "manifest": str(config.manifest),
        "manifest_sha256": _sha256(config.manifest),
        "predictions": [str(path) for path in config.predictions],
        "predictions_sha256": [_sha256(path) for path in config.predictions],
        "truth_dir": str(config.truth_dir),
        "images_dir": str(config.images_dir),
        "input_track": "pdf-text-assisted",
        "gpu_used": False,
    }
    index = write_case_report(
        output_dir,
        all_cases=cases,
        selected_cases=selected,
        records_by_id=records_by_unit,
        truth_by_id={unit_id: tables[0] for unit_id, tables in truth_by_unit.items()},
        images_dir=config.images_dir,
        metadata=metadata,
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "cases": len(cases),
                "selected": len(selected),
                "index": str(index),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    return run(load_config(args.config))


if __name__ == "__main__":
    raise SystemExit(main())
