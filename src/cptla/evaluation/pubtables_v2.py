from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Collection = Literal["cropped_tables", "full_documents"]

_FULL_DOCUMENT_IMAGE = re.compile(r"^(?P<document>PMC\d+)_page_(?P<page>\d+)\.jpg$")
_CROPPED_TABLE_IMAGE = re.compile(r"^(?P<document>PMC\d+)_table_(?P<table>\d+)\.jpg$")


class ImageManifestEntry(BaseModel):
    """One deterministic image input without a machine-specific absolute path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    image_id: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=0)


def parse_full_document_image_id(name: str) -> tuple[str, int]:
    match = _FULL_DOCUMENT_IMAGE.fullmatch(name)
    if match is None:
        raise ValueError(f"invalid Full Documents image name: {name}")
    return match.group("document"), int(match.group("page"))


def parse_cropped_table_id(name: str) -> str:
    match = _CROPPED_TABLE_IMAGE.fullmatch(name)
    if match is None:
        raise ValueError(f"invalid Cropped Tables image name: {name}")
    return Path(name).stem


def build_image_manifest(images_dir: Path, collection: Collection) -> list[ImageManifestEntry]:
    if not images_dir.is_dir():
        raise NotADirectoryError(images_dir)

    records: list[ImageManifestEntry] = []
    image_paths = sorted(
        (path for path in images_dir.iterdir() if path.is_file() and path.suffix == ".jpg"),
        key=lambda path: path.name,
    )
    for image_path in image_paths:
        if collection == "full_documents":
            document_id, page_number = parse_full_document_image_id(image_path.name)
            unit_id = document_id
        else:
            unit_id = parse_cropped_table_id(image_path.name)
            document_id = unit_id.rsplit("_table_", maxsplit=1)[0]
            page_number = None
        records.append(
            ImageManifestEntry(
                image_id=image_path.name,
                relative_path=image_path.relative_to(images_dir).as_posix(),
                unit_id=unit_id,
                document_id=document_id,
                page_number=page_number,
            )
        )
    return records


def _manifest_bytes(records: list[ImageManifestEntry]) -> bytes:
    lines = [
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for record in records
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode()


def manifest_sha256(records: list[ImageManifestEntry]) -> str:
    return hashlib.sha256(_manifest_bytes(records)).hexdigest()


def write_image_manifest(records: list[ImageManifestEntry], output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = _manifest_bytes(records)
    output.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()
