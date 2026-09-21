"""Download fixed PubTables-v2 Cropped Tables val archives directly on the GPU server."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from huggingface_hub import HfApi, hf_hub_download

REPO_ID = "kensho/PubTables-v2"
REVISION = "aa575e798cb00a296925e2086addb3e3fd9a1903"
SERVER_PROJECT_ROOT = Path("/data01/public/zhengguojie/paper")
_CATEGORIES = ("images", "tables", "words", "xml-annotations")


def expected_archive_names() -> list[str]:
    return [f"PubTables-v2_Cropped-Tables_val_{category}.tar.gz" for category in _CATEGORIES]


def select_cropped_val_archives(files: list[str]) -> list[str]:
    expected = expected_archive_names()
    available = set(files)
    missing = [name for name in expected if name not in available]
    if missing:
        raise ValueError(f"missing Cropped Tables val archives: {missing}")
    return expected


def safe_extraction_targets(members: list[tarfile.TarInfo], target_root: Path) -> list[Path]:
    root = target_root.resolve()
    targets: list[Path] = []
    for member in members:
        member_path = PurePosixPath(member.name)
        unsafe = (
            member_path.is_absolute()
            or ".." in member_path.parts
            or member.issym()
            or member.islnk()
        )
        if unsafe:
            raise ValueError(f"unsafe tar member: {member.name}")
        target = (root / Path(*member_path.parts)).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"unsafe tar member: {member.name}")
        if target.exists() and not (member.isdir() and target.is_dir()):
            raise FileExistsError(f"refusing to overwrite existing path: {target}")
        targets.append(target)
    return targets


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cropped_extraction_root(dataset_root: Path) -> Path:
    """Return the root expected by the paths embedded in the official archives."""
    return dataset_root / "extracted"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    project_root = Path.cwd().resolve()
    if project_root.as_posix() != SERVER_PROJECT_ROOT.as_posix():
        parser.error(
            f"this downloader may run only from {SERVER_PROJECT_ROOT}; current={project_root}"
        )

    api = HfApi()
    info = api.dataset_info(REPO_ID, revision=REVISION, files_metadata=True)
    names = select_cropped_val_archives([sibling.rfilename for sibling in info.siblings])
    archives_dir = project_root / "data" / "pubtables-v2" / "archives" / args.run_id
    if archives_dir.exists():
        parser.error(f"run archive directory already exists: {archives_dir}")
    archives_dir.mkdir(parents=True)

    downloaded: list[Path] = []
    for name in names:
        downloaded.append(
            Path(
                hf_hub_download(
                    repo_id=REPO_ID,
                    repo_type="dataset",
                    revision=REVISION,
                    filename=name,
                    local_dir=archives_dir,
                )
            )
        )

    extracted_root = cropped_extraction_root(project_root / "data" / "pubtables-v2")
    archives: list[dict[str, object]] = []
    opened: list[tuple[tarfile.TarFile, Path, list[tarfile.TarInfo]]] = []
    try:
        for archive in downloaded:
            category_root = extracted_root
            tar = tarfile.open(archive, "r:gz")
            members = tar.getmembers()
            safe_extraction_targets(members, category_root)
            opened.append((tar, category_root, members))
            archives.append(
                {
                    "filename": archive.name,
                    "bytes": archive.stat().st_size,
                    "sha256": _sha256(archive),
                    "target": str(category_root),
                }
            )
        for tar, category_root, members in opened:
            category_root.mkdir(parents=True, exist_ok=True)
            tar.extractall(category_root, members=members, filter="data")
    finally:
        for tar, _, _ in opened:
            tar.close()

    manifest = {
        "repo_id": REPO_ID,
        "resolved_revision": info.sha,
        "requested_revision": REVISION,
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "server_project_root": str(project_root),
        "archives": archives,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
