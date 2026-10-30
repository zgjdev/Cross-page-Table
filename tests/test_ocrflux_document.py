import copy

import pytest

from cptla.evaluation.ocrflux_document import ResourceSafetyStop, parse_pairs, reconstruct

TABLE = "<table><tr><td>A</td></tr></table>"


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').getcwd()",
        "[(True,0)]",
        "[(0,-1)]",
        "[(1,0)]",
        "[(0,0),(0,1)]",
        "[(0,0),(0,0)]",
        "[0]",
        "None",
    ],
)
def test_reject_invalid_or_ambiguous_pairs(text):
    with pytest.raises(ValueError):
        parse_pairs(text, 1, 2)


def test_valid_pairs():
    assert parse_pairs("[(0, 1)]", 1, 2) == [(0, 1)]
    assert parse_pairs("[]", 0, 0) == []


def test_reverse_three_page_chain_and_duplicate_identity():
    pages = [[TABLE, TABLE], [TABLE], [TABLE]]
    before = copy.deepcopy(pages)
    calls = []

    def merge(a, b):
        calls.append((a, b))
        return "<table><tr><td>" + str(len(calls)) + "</td></tr></table>"

    result = reconstruct("PMC1", pages, lambda a, b: "[(0,0)]", merge)
    assert len(result["no_merge"]) == 4
    assert len(result["merged"]) == 2
    assert result["merged"][0]["source_pages"] == [0, 1, 2]
    assert result["merged"][1]["source_pages"] == [0]
    assert calls[1][1] == "<table><tr><td>1</td></tr></table>"
    assert pages == before


def test_failed_merge_keeps_fragments_and_logs_error():
    result = reconstruct("PMC1", [[TABLE], [TABLE]], lambda a, b: "[(0,0)]", lambda a, b: "broken")
    assert result["merged"] == result["no_merge"]
    assert result["decisions"][-1]["status"] == "error"


def test_missing_page_prevents_nonadjacent_merge():
    def forbidden(*args):
        raise AssertionError("must not query")

    result = reconstruct("PMC1", [[TABLE], None, [TABLE]], forbidden, forbidden)
    assert len(result["merged"]) == 2
    assert [x["source_pages"] for x in result["merged"]] == [[0], [2]]


def test_resource_stop_is_never_swallowed_as_model_failure():
    def fail(*args):
        raise ResourceSafetyStop("low memory")

    with pytest.raises(ResourceSafetyStop):
        reconstruct("PMC1", [[TABLE], [TABLE]], fail, fail)
    with pytest.raises(ResourceSafetyStop):
        reconstruct("PMC1", [[TABLE], [TABLE]], lambda a, b: "[(0,0)]", fail)


@pytest.mark.parametrize("stage", ["detect", "merge"])
def test_engine_runtime_failure_must_abort_checkpoint(stage):
    def fail(*args):
        raise RuntimeError("CUDA out of memory")

    detect = fail if stage == "detect" else lambda a, b: "[(0,0)]"
    with pytest.raises(RuntimeError, match="CUDA out of memory"):
        reconstruct("PMC1", [[TABLE], [TABLE]], detect, fail)
