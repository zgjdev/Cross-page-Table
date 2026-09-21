import tarfile
from pathlib import Path

import pytest

from scripts.download_pubtables_v2_cropped_val import (
    expected_archive_names,
    safe_extraction_targets,
    select_cropped_val_archives,
)


def test_selects_only_four_cropped_validation_archives() -> None:
    files = [
        "README.md",
        "PubTables-v2_Cropped-Tables_train_images.tar.gz",
        "PubTables-v2_Cropped-Tables_val_words.tar.gz",
        "PubTables-v2_Single-Pages_val_images.tar.gz",
        "PubTables-v2_Cropped-Tables_val_images.tar.gz",
        "PubTables-v2_Cropped-Tables_val_xml-annotations.tar.gz",
        "PubTables-v2_Cropped-Tables_test_tables.tar.gz",
        "PubTables-v2_Cropped-Tables_val_tables.tar.gz",
    ]

    assert select_cropped_val_archives(files) == expected_archive_names()


def test_selection_rejects_missing_archive() -> None:
    with pytest.raises(ValueError, match="missing"):
        select_cropped_val_archives(expected_archive_names()[:-1])


def test_safe_extraction_targets_reject_path_traversal(tmp_path: Path) -> None:
    member = tarfile.TarInfo("../../outside.txt")

    with pytest.raises(ValueError, match="unsafe tar member"):
        safe_extraction_targets([member], tmp_path)


def test_safe_extraction_targets_reject_existing_file(tmp_path: Path) -> None:
    existing = tmp_path / "Cropped Tables" / "val" / "images" / "a.jpg"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        safe_extraction_targets([tarfile.TarInfo("Cropped Tables/val/images/a.jpg")], tmp_path)
