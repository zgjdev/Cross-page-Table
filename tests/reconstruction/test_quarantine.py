import pytest

from cptla.reconstruction.quarantine import quarantine_splits


def test_document_and_existing_cluster_scope_without_mutating_original():
    rows = [
        dict(document_id=x, cluster_id=c, split=s)
        for x, c, s in [
            ("a", "c1", "train_dev"),
            ("b", "c1", "train_dev"),
            ("c", "c2", "train_confirm"),
            ("d", "c3", "train_fit"),
        ]
    ]
    overlaps = dict(
        tables=[
            dict(
                members=[
                    dict(document_id="a", official_split="train"),
                    dict(document_id="v", official_split="val"),
                ]
            )
        ],
        documents=[],
    )
    result = quarantine_splits(rows, overlaps, {"d"})
    assert [x["effective_split"] for x in result] == [
        "quarantine",
        "quarantine",
        "train_confirm",
        "train_fit",
    ]
    assert all("effective_split" not in row for row in rows)
    assert result[1]["reason"] == "cluster_contains_known_official_overlap"


def test_observed_confirm_cluster_rejected():
    rows = [dict(document_id="a", cluster_id="x", split="train_confirm")]
    with pytest.raises(ValueError, match="observed"):
        quarantine_splits(rows, dict(tables=[], documents=[]), {"a"})


def test_unknown_document_and_duplicate_are_rejected():
    rows = [dict(document_id="a", cluster_id="a", split="train_fit")]
    with pytest.raises(ValueError):
        quarantine_splits(rows * 2, dict(tables=[], documents=[]), set())
    overlaps = dict(
        tables=[
            dict(
                members=[
                    dict(document_id="unknown", official_split="train"),
                    dict(document_id="v", official_split="val"),
                ]
            )
        ],
        documents=[],
    )
    with pytest.raises(ValueError):
        quarantine_splits(rows, overlaps, set())
