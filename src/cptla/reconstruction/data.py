"""Read the fixed PubTables-v2 train split for the R0 oracle protocol."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from itertools import pairwise
from pathlib import Path

from PIL import Image

from cptla.evaluation.pubtables_v2 import parse_full_document_image_id

DATASET_REVISION = "aa575e798cb00a296925e2086addb3e3fd9a1903"
PROTOCOL = "R0_oracle_gt_parts_and_grouping"
TRAIN_RELATIVE_PATH = Path("data/pubtables-v2/extracted/Full Documents/train")
_TABLE_FILENAME = re.compile(r"(PMC[0-9]+)_tables\.json")


class _TableText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.chunks.append(data.strip())


def _check_source(path: Path, train_root: Path) -> None:
    if not path.resolve().is_relative_to(train_root):
        raise ValueError(f"source path resolves outside train: {path}")


def _read_tables(path: Path) -> tuple[list, str]:
    payload = path.read_bytes()
    try:
        tables = json.loads(payload)
    except (ValueError, UnicodeError) as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(tables, list):
        raise ValueError(f"expected a JSON list of tables: {path}")
    return tables, hashlib.sha256(payload).hexdigest()


def _cell_profile(table: dict, location: str) -> tuple[int, bool]:
    cells = table.get("cells")
    if not isinstance(cells, list):
        raise ValueError(f"invalid cells: {location}")
    has_span = False
    for index, cell in enumerate(cells):
        for field in ("row_nums", "column_nums"):
            indices = cell.get(field) if isinstance(cell, dict) else None
            if (
                not isinstance(indices, list)
                or not indices
                or any(type(value) is not int or value < 0 for value in indices)
                or len(indices) != len(set(indices))
            ):
                raise ValueError(f"invalid cell {field}: {location} cell {index}")
            has_span |= len(indices) > 1
    return len(cells), has_span


def _crop_box(part: dict, size: list[int], location: str) -> tuple[list[int], bool]:
    bbox = part.get("bbox")
    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or any(
            type(value) not in (int, float)
            or (isinstance(value, float) and not math.isfinite(value))
            for value in bbox
        )
        or bbox[0] >= bbox[2]
        or bbox[1] >= bbox[3]
    ):
        raise ValueError(f"invalid bbox: {location}")
    pixel_box = [math.floor(bbox[0]), math.floor(bbox[1]), math.ceil(bbox[2]), math.ceil(bbox[3])]
    crop_box = [min(max(value, 0), bound) for value, bound in zip(pixel_box, size * 2, strict=True)]
    if crop_box[0] >= crop_box[2] or crop_box[1] >= crop_box[3]:
        raise ValueError(f"empty crop after clamping: {location}")
    return crop_box, crop_box != pixel_box


def scan_training_data(project_root: Path, *, limit_documents: int | None = None) -> dict:
    """Scan train annotation files and keep targets separate from model inputs."""
    if limit_documents is not None and (type(limit_documents) is not int or limit_documents < 1):
        raise ValueError("limit_documents must be a positive integer")
    root = project_root.resolve()
    train = root / TRAIN_RELATIVE_PATH
    _check_source(train, train)
    tables_dir = train / "tables"
    images_dir = train / "images"
    for directory in (tables_dir, images_dir):
        _check_source(directory, train)
        if not directory.is_dir():
            raise NotADirectoryError(directory)

    table_paths: dict[str, Path] = {}
    for path in sorted(tables_dir.iterdir()):
        match = _TABLE_FILENAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"invalid table filename: {path}")
        table_paths[match[1]] = path
    if not table_paths:
        raise ValueError(f"no train table annotations: {tables_dir}")
    selected_ids = list(table_paths)[:limit_documents]
    selected = set(selected_ids)
    pages: dict[str, dict[int, Path]] = defaultdict(dict)
    image_documents = set()
    for path in images_dir.iterdir():
        document_id, page = parse_full_document_image_id(path.name)
        image_documents.add(document_id)
        if document_id not in selected:
            continue
        _check_source(path, train)
        if not path.is_file():
            raise ValueError(f"expected a page image file: {path}")
        if page in pages[document_id]:
            raise ValueError(f"duplicate page image: {document_id} page {page}")
        pages[document_id][page] = path

    inputs, targets, documents, profiles = [], [], [], []
    hashes: dict[str, str] = {}
    counts = Counter()
    for document_id in selected_ids:
        table_path = table_paths[document_id]
        _check_source(table_path, train)
        tables, table_sha = _read_tables(table_path)
        table_relpath = table_path.relative_to(root).as_posix()
        hashes[table_relpath] = table_sha
        image_sizes: dict[int, list[int]] = {}
        text = _TableText()
        document_groups = []
        for table_index, table in enumerate(tables):
            group_id = f"{document_id}-table-{table_index}"
            location = f"{table_relpath} table {table_index}"
            if not isinstance(table, dict) or not isinstance(table.get("html"), str):
                raise ValueError(f"invalid table html: {location}")
            cell_count, has_span = _cell_profile(table, location)
            text.feed(table["html"])
            parts = table.get("parts")
            if not isinstance(parts, list) or not parts:
                raise ValueError(f"expected a nonempty parts list: {location}")
            fragments = []
            for part_index, part in enumerate(parts):
                part_location = f"{location} part {part_index}"
                if (
                    not isinstance(part, dict)
                    or type(part.get("page_num")) is not int
                    or part["page_num"] < 0
                ):
                    raise ValueError(f"invalid page_num: {part_location}")
                page = part["page_num"]
                if page not in pages[document_id]:
                    raise ValueError(f"part page {page} without image: {part_location}")
                object_number = part.get("page_object_num")
                if type(object_number) is not int or object_number < 0:
                    raise ValueError(f"invalid page_object_num: {part_location}")
                image_path = pages[document_id][page]
                if page not in image_sizes:
                    try:
                        with Image.open(image_path) as image:
                            image_sizes[page] = list(image.size)
                    except OSError as exc:
                        raise ValueError(f"unable to read page image {image_path}: {exc}") from exc
                size = image_sizes[page]
                crop_box, clamped = _crop_box(part, size, part_location)
                counts["clamped_fragments"] += clamped
                fragments.append(
                    {
                        "fragment_id": f"{group_id}-part-{part_index}",
                        "part_index": part_index,
                        "page_num": page,
                        "page_object_num": object_number,
                        "image_relpath": image_path.relative_to(root).as_posix(),
                        "image_size": size,
                        "bbox": part["bbox"],
                        "crop_box": crop_box,
                        "clamped": clamped,
                    }
                )

            page_numbers = sorted({part["page_num"] for part in fragments})
            if len(page_numbers) == 1:
                counts["multi_part_single_page_tables"] += len(fragments) > 1
                continue
            counts["nonadjacent_part_page_gaps"] += sum(
                right > left + 1 for left, right in pairwise(page_numbers)
            )
            document_groups.append(group_id)
            fragments.sort(key=lambda part: (part["page_num"], part["part_index"]))
            for fragment in fragments:
                relpath = fragment["image_relpath"]
                if relpath not in hashes:
                    with (root / relpath).open("rb") as handle:
                        hashes[relpath] = hashlib.file_digest(handle, "sha256").hexdigest()
                fragment["image_sha256"] = hashes[relpath]
            ids = {"group_id": group_id, "document_id": document_id}
            inputs.append(
                {
                    **ids,
                    "source_split": "train",
                    "dataset_revision": DATASET_REVISION,
                    "protocol": PROTOCOL,
                    "page_numbers": page_numbers,
                    "fragments": fragments,
                }
            )
            targets.append(
                {
                    **ids,
                    "html": table["html"],
                    "source_pages": page_numbers,
                    "source_table_file": table_relpath,
                    "source_table_sha256": table_sha,
                }
            )
            profiles.append(
                {
                    **ids,
                    "page_count": len(page_numbers),
                    "cell_count": cell_count,
                    "has_span": has_span,
                }
            )
        text.close()
        documents.append(
            {
                "document_id": document_id,
                "text": " ".join(text.chunks),
                "cross_page_groups": document_groups,
                "table_count": len(tables),
            }
        )
    missing_images = selected - image_documents
    missing_tables = image_documents - table_paths.keys() if limit_documents is None else set()
    if missing_images or missing_tables:
        raise ValueError(
            "train document ID mismatch: "
            f"missing image documents={sorted(missing_images)[:5]}, "
            f"missing table documents={sorted(missing_tables)[:5]}"
        )

    return {
        "inputs": inputs,
        "targets": targets,
        "documents": documents,
        "audit": {
            "dataset_revision": DATASET_REVISION,
            "source_split": "train",
            "is_full_scan": limit_documents is None,
            "limit_documents": limit_documents,
            "available_documents": len(table_paths),
            "documents": len(documents),
            "image_pages": sum(map(len, pages.values())),
            "logical_tables": sum(document["table_count"] for document in documents),
            "cross_page_tables": len(inputs),
            "multi_part_single_page_tables": counts["multi_part_single_page_tables"],
            "nonadjacent_part_page_gaps": counts["nonadjacent_part_page_gaps"],
            "clamped_fragments": counts["clamped_fragments"],
            "profiles": profiles,
        },
        "source_hashes": [{"path": path, "sha256": hashes[path]} for path in sorted(hashes)],
    }
