from __future__ import annotations

import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cptla.evaluation.case_analysis import analyze_cropped_case
from cptla.evaluation.case_report import render_comparison_table
from cptla.evaluation.contracts import CoverageReport, PredictionRecord
from cptla.evaluation.pubtables_v2 import ImageManifestEntry


@dataclass(frozen=True)
class PredictionLocation:
    path: Path
    offset: int
    unit_id: str


class LiveCaseBrowser:
    """Lazy, read-only access to one Cropped Tables experiment."""

    def __init__(
        self,
        *,
        manifest_path: Path,
        prediction_paths: list[Path],
        truth_dir: Path,
        images_dir: Path,
        session_dir: Path,
        cache_size: int = 128,
    ) -> None:
        if cache_size < 1:
            raise ValueError("cache_size must be positive")
        self.manifest_path = manifest_path
        self.prediction_paths = prediction_paths
        self.truth_dir = truth_dir
        self.images_dir = images_dir
        self.session_dir = session_dir
        self.cache_size = cache_size
        self.entries = self._load_manifest(manifest_path)
        self._index_by_unit = {entry.unit_id: index for index, entry in enumerate(self.entries)}
        if len(self._index_by_unit) != len(self.entries):
            raise ValueError("manifest contains duplicate unit IDs")
        self._predictions = self._index_predictions(prediction_paths)
        coverage = CoverageReport.from_ids(
            [entry.image_id for entry in self.entries], list(self._predictions)
        )
        if not coverage.is_complete:
            raise ValueError(
                "live browser requires exact prediction coverage: "
                f"missing={len(coverage.missing)}, extra={len(coverage.extra)}, "
                f"duplicates={len(coverage.duplicates)}"
            )
        if not truth_dir.is_dir():
            raise NotADirectoryError(truth_dir)
        if not images_dir.is_dir():
            raise NotADirectoryError(images_dir)
        if session_dir.exists():
            raise FileExistsError(session_dir)
        session_dir.mkdir(parents=True)
        self._cache: OrderedDict[int, dict[str, object]] = OrderedDict()
        self._lock = threading.Lock()
        (session_dir / "session.json").write_text(
            json.dumps(
                {
                    "created_at_utc": datetime.now(UTC).isoformat(),
                    "manifest": str(manifest_path),
                    "predictions": [str(path) for path in prediction_paths],
                    "truth_dir": str(truth_dir),
                    "images_dir": str(images_dir),
                    "total": len(self.entries),
                    "mode": "lazy_live_browser",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _load_manifest(path: Path) -> list[ImageManifestEntry]:
        if not path.is_file():
            raise FileNotFoundError(path)
        return [
            ImageManifestEntry.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @staticmethod
    def _index_predictions(paths: list[Path]) -> dict[str, PredictionLocation]:
        locations: dict[str, PredictionLocation] = {}
        duplicates: list[str] = []
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(path)
            with path.open("rb") as stream:
                while True:
                    offset = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    if not line.strip():
                        continue
                    value = json.loads(line)
                    image_id = value.get("image_id")
                    unit_id = value.get("unit_id")
                    if not isinstance(image_id, str) or not isinstance(unit_id, str):
                        raise ValueError(f"prediction identity missing at {path}:{offset}")
                    if image_id in locations:
                        duplicates.append(image_id)
                    locations[image_id] = PredictionLocation(path, offset, unit_id)
        if duplicates:
            raise ValueError(f"duplicate prediction image IDs: {sorted(set(duplicates))[:3]}")
        return locations

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def cache_entries(self) -> int:
        return len(self._cache)

    def resolve_index(self, value: str) -> int:
        stripped = value.strip()
        if stripped.isdecimal():
            index = int(stripped) - 1
            if 0 <= index < self.total:
                return index
            raise IndexError(value)
        try:
            return self._index_by_unit[stripped]
        except KeyError as error:
            raise KeyError(f"unknown unit_id: {stripped}") from error

    def _load_prediction(self, entry: ImageManifestEntry) -> PredictionRecord:
        location = self._predictions[entry.image_id]
        if location.unit_id != entry.unit_id:
            raise ValueError(f"prediction unit mismatch for {entry.image_id}")
        with location.path.open("rb") as stream:
            stream.seek(location.offset)
            return PredictionRecord.model_validate_json(stream.readline())

    def _load_truth(self, unit_id: str) -> str:
        path = self.truth_dir / f"{unit_id}.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        value = json.loads(path.read_text(encoding="utf-8"))
        tables = value if isinstance(value, list) else [value]
        matches = [
            table
            for table in tables
            if isinstance(table, dict)
            and (table.get("id") in (None, unit_id) or table.get("table_id") == unit_id)
        ]
        if len(matches) != 1 or not isinstance(matches[0].get("html"), str):
            raise ValueError(f"expected one truth HTML for {unit_id} in {path}")
        return matches[0]["html"]

    def image_path(self, index: int) -> Path:
        entry = self._entry(index)
        path = self.images_dir / entry.relative_path
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _entry(self, index: int) -> ImageManifestEntry:
        if index < 0 or index >= self.total:
            raise IndexError(index)
        return self.entries[index]

    def get_case(self, index: int) -> dict[str, object]:
        self._entry(index)
        with self._lock:
            cached = self._cache.get(index)
            if cached is not None:
                self._cache.move_to_end(index)
                return cached
        entry = self.entries[index]
        prediction = self._load_prediction(entry)
        truth_html = self._load_truth(entry.unit_id)
        diagnostic = analyze_cropped_case(entry, prediction, truth_html)
        predicted_html = (
            prediction.tables_html[0]
            if prediction.status == "ok" and len(prediction.tables_html) == 1
            else None
        )
        result: dict[str, object] = {
            "index": index,
            "position": index + 1,
            "total": self.total,
            "image_id": entry.image_id,
            "unit_id": entry.unit_id,
            "status": prediction.status,
            "error": prediction.error,
            "grits_top": diagnostic.grits_top,
            "grits_con": diagnostic.grits_con,
            "acc_top": diagnostic.acc_top,
            "acc_con": diagnostic.acc_con,
            "score_stratum": diagnostic.score_stratum,
            "error_tags": diagnostic.error_tags,
            "truth_profile": diagnostic.truth_profile.model_dump(mode="json"),
            "prediction_profile": (
                diagnostic.prediction_profile.model_dump(mode="json")
                if diagnostic.prediction_profile
                else None
            ),
            "truth_table_html": render_comparison_table(
                truth_html, predicted_html, side="truth"
            ),
            "prediction_table_html": (
                render_comparison_table(predicted_html, truth_html, side="prediction")
                if predicted_html
                else '<p class="empty-table">没有可渲染的预测表格</p>'
            ),
            "truth_html": truth_html,
            "prediction_html": predicted_html or "",
            "image_url": f"/api/image?index={index}",
        }
        with self._lock:
            self._cache[index] = result
            self._cache.move_to_end(index)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
        return result

    def record_view(self, case: dict[str, object]) -> None:
        event = {
            "viewed_at_utc": datetime.now(UTC).isoformat(),
            "index": case["index"],
            "position": case["position"],
            "unit_id": case["unit_id"],
            "image_id": case["image_id"],
            "grits_top": case["grits_top"],
            "grits_con": case["grits_con"],
            "error_tags": case["error_tags"],
        }
        with self._lock, (self.session_dir / "viewed-cases.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
