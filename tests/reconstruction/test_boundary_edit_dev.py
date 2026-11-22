import pytest

from cptla.reconstruction.data import DATASET_REVISION
from scripts.evaluate_reconstruction_boundary_edit_dev import validate_selection


def fixtures():
    inputs = {
        f"group{i}": dict(
            document_id=f"doc{i}",
            cluster_id=f"cluster{i}",
            dataset_revision=DATASET_REVISION,
            split="train_dev",
            source_split="train",
            fragments=[{}] * (2 if i < 8 else 3),
        )
        for i in range(16)
    }
    overlay = {
        row["document_id"]: dict(
            effective_split="train_dev",
            observed_cluster=False,
            cluster_id=row["cluster_id"],
        )
        for row in inputs.values()
    }
    selection = [
        dict(
            group_id=key,
            document_id=row["document_id"],
            cluster_id=row["cluster_id"],
            fragments=len(row["fragments"]),
        )
        for key, row in inputs.items()
    ]
    return selection, inputs, overlay


def test_disjoint_16_group_scope():
    selection, inputs, overlay = fixtures()
    assert validate_selection(selection, inputs, overlay, {"other_doc"}, {"other_cluster"}) == list(
        inputs
    )


def test_reject_overlap_and_quarantine():
    selection, inputs, overlay = fixtures()
    with pytest.raises(ValueError, match="scope"):
        validate_selection(selection, inputs, overlay, set(), {"cluster0"})
    with pytest.raises(ValueError, match="scope"):
        validate_selection(selection, inputs, overlay, {"doc0"}, set())
    overlay["doc0"]["effective_split"] = "quarantine"
    with pytest.raises(ValueError, match="scope"):
        validate_selection(selection, inputs, overlay, set(), set())
