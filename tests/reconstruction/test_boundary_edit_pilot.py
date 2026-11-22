import pytest

from cptla.reconstruction.boundary_edit import (
    apply_cuts,
    boundary_candidates,
    derive_weak_label,
    split_groups,
)
from cptla.reconstruction.grid import html_to_grid


def table(*rows):
    return html_to_grid(
        "<table>"
        + "".join(f"<tr><td>{left}</td><td>{right}</td></tr>" for left, right in rows)
        + "</table>"
    )


def test_exact_repeated_prefix_can_be_kept_or_dropped_depending_on_target():
    first = table(("Category", "Count"), ("Red", "1"))
    second = table(("Category", "Count"), ("Green", "2"))
    grids = [first, second]
    candidates = boundary_candidates(grids)
    assert [c.cut for c in candidates[0]] == [0, 1]
    kept = apply_cuts(grids, (0,))
    deleted = apply_cuts(grids, (1,))
    assert kept.n_rows == 4
    assert deleted.n_rows == 3
    assert derive_weak_label(grids, candidates, kept)["cuts"] == (0,)
    assert derive_weak_label(grids, candidates, deleted)["cuts"] == (1,)
    assert derive_weak_label(grids, candidates, table(("wrong", "target"))) is None


def test_no_whole_fragment_delete_or_rowspan_break():
    header = table(("Category", "Count"), ("Red", "1"))
    singleton = table(("Category", "Count"))
    crossing = html_to_grid(
        '<table><tr><td rowspan="2">Category</td><td>Count</td></tr><tr><td>4</td></tr></table>'
    )
    assert [c.cut for c in boundary_candidates([header, singleton])[0]] == [0]
    assert [c.cut for c in boundary_candidates([header, crossing])[0]] == [0]
    with pytest.raises(ValueError):
        apply_cuts([header, singleton], (1,))


def test_split_keeps_docs_and_clusters_together():
    rows = [
        dict(group_id="a", document_id="d1", cluster_id="c1"),
        dict(group_id="b", document_id="d1", cluster_id="c1"),
        dict(group_id="c", document_id="d2", cluster_id="c1"),
        dict(group_id="d", document_id="d3", cluster_id="c2"),
    ]
    fit, dev = split_groups(rows, seed=23)
    assert len(fit) + len(dev) == 4
    assert {"a", "b", "c"} <= set(fit) or {"a", "b", "c"} <= set(dev)
