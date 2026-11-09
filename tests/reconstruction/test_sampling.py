def test_exact_normalization_does_not_merge_empty_documents():
    from cptla.reconstruction.sampling import group_and_split

    documents = [
        {"document_id": "a", "text": "<td> A &amp; B </td>"},
        {"document_id": "b", "text": "a & b"},
        {"document_id": "c", "text": "<td> </td>"},
        {"document_id": "d", "text": ""},
        {"document_id": "e", "text": "A & B and more"},
    ]
    result = group_and_split(documents)
    assert result == group_and_split(list(reversed(documents)))
    rows = {row["document_id"]: row for row in result["assignments"]}
    assert rows["a"]["cluster_id"] == rows["b"]["cluster_id"]
    assert rows["a"]["split"] == rows["b"]["split"]
    assert len({row["cluster_id"] for row in rows.values()}) == 4
    assert result["summary"]["split_status"] == "provisional_do_not_train"


def test_near_candidates_require_full_shingle_jaccard():
    from cptla.reconstruction.sampling import group_and_split

    original = " ".join(f"term{i}" for i in range(1024))
    documents = [
        {"document_id": "a", "text": original},
        {"document_id": "b", "text": original + " tail3 token"},
        {"document_id": "c", "text": " ".join(original.split()[:10])},
    ]
    result = group_and_split(documents)
    rows = {row["document_id"]: row for row in result["assignments"]}
    assert rows["a"]["cluster_id"] == rows["b"]["cluster_id"]
    assert rows["a"]["cluster_id"] != rows["c"]["cluster_id"]
    [candidate] = result["duplicate_candidates"]
    assert candidate["accepted"]
    assert candidate["hamming"] <= 3
    assert candidate["jaccard"] == 1020 / 1022


def test_sampling_balances_strata_and_reports_weights():
    from cptla.reconstruction.sampling import sample_audit_groups

    profiles = [
        {
            "document_id": "a",
            "group_id": f"g{i}",
            "page_count": 2,
            "cell_count": 10,
            "has_span": i == 0,
        }
        for i in range(6)
    ] + [
        {
            "document_id": "b",
            "group_id": "excluded",
            "page_count": 4,
            "cell_count": 10,
            "has_span": True,
        }
    ]
    assignments = [
        {"document_id": "a", "split": "train_fit"},
        {"document_id": "b", "split": "dev"},
    ]
    result = sample_audit_groups(profiles, assignments, sample_size=4, coordinate_size=2)
    assert result == sample_audit_groups(
        profiles[::-1], assignments[::-1], sample_size=4, coordinate_size=2
    )
    samples = {row["group_id"]: row for row in result["samples"]}
    assert len(samples) == 4
    assert "excluded" not in samples
    assert samples["g0"]["inclusion_probability"] == samples["g0"]["weight"] == 1
    for group_id in samples.keys() - {"g0"}:
        assert samples[group_id]["inclusion_probability"] == 3 / 5
        assert samples[group_id]["weight"] == 5 / 3
    assert len(set(result["coordinate_group_ids"])) == 2
    assert set(result["coordinate_group_ids"]) <= samples.keys()
    assert "g0" in result["coordinate_group_ids"]


def test_small_audit_population_reports_shortfall():
    from cptla.reconstruction.sampling import sample_audit_groups

    result = sample_audit_groups(
        [{"document_id": "a", "group_id": "x", "page_count": 4, "cell_count": 1, "has_span": True}],
        [{"document_id": "a", "split": "train_fit"}],
    )
    assert result["summary"]["sample_shortfall"] == 199
    assert result["summary"]["coordinate_shortfall"] == 19
    assert result["samples"][0]["weight"] == 1
    assert result["coordinate_group_ids"] == ["x"]
