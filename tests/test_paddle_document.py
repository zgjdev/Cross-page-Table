import copy
import os
from pathlib import Path

import pytest

from cptla.evaluation.paddle_document import (
    adapt_document,
    load_official_merger,
    remerge_document,
)

HTML = "<table><tr><td>H</td></tr><tr><td>data</td></tr></table>"


def block(index, label="table", content=HTML, group=None, width=100):
    return {
        "block_label": label,
        "block_content": content,
        "block_bbox": [0, 0, width, 100],
        "global_block_id": index,
        "global_group_id": index if group is None else group,
    }


def pages(*blocks):
    return [
        {"res": {"page_index": i, "page_count": len(blocks), "parsing_res_list": b}}
        for i, b in enumerate(blocks)
    ]


def test_empty_tail_members_keep_all_source_pages_and_original_html():
    data = pages([block(0)], [block(1, content="", group=0)], [block(2, content="", group=0)])
    original = copy.deepcopy(data)
    tables, evidence = adapt_document(data, "PMC1", 3)
    assert tables == [
        {"document_id": "PMC1", "table_id": "PMC1-group-0", "html": HTML, "source_pages": [0, 1, 2]}
    ]
    assert evidence[0]["global_block_ids"] == [0, 1, 2]
    assert data == original


def test_non_table_pages_are_not_dropped():
    tables, _ = adapt_document(pages([], [block(0)]), "PMC1", 2)
    assert tables[0]["source_pages"] == [1]


@pytest.mark.parametrize(
    "data,count",
    [
        (pages([block(0)]), 2),
        (pages([block(0)], [block(0)]), 2),
        (pages([block(0, group=9)]), 1),
        (pages([block(0, label="text", content="x"), block(1, group=0)]), 1),
        (pages([block(0), block(1, group=0)]), 1),
        (pages([block(0, content="")]), 1),
        (pages([block(0, group=1), block(1, group=0)]), 1),
    ],
)
def test_ambiguous_or_incomplete_results_rejected(data, count):
    with pytest.raises(ValueError):
        adapt_document(data, "PMC1", count)


def test_compatibility_only_exposes_content_without_mutating_inputs():
    data = pages([block(0)], [block(1, label="figure_title", content="Continued"), block(2)])
    original = copy.deepcopy(data)

    def merger(items):
        assert items[1][0].text == "Continued"
        items[0][0].content = HTML + "merged"
        items[1][1].content = ""
        items[1][1].global_group_id = 0
        return items

    merged = remerge_document(data, merger, content_compat=True)
    assert data == original
    assert adapt_document(merged, "PMC1", 2)[0][0]["source_pages"] == [0, 1]


def test_source_hash_required_before_execution(tmp_path):
    source = tmp_path / "source.py"
    source.write_text('raise RuntimeError("must not execute")')
    with pytest.raises(ValueError, match="SHA"):
        load_official_merger(source)


@pytest.fixture
def official():
    path = os.environ.get("PADDLE_MERGE_SOURCE")
    if path is None:
        pytest.skip("Official pinned source supplied by server integration test")
    return load_official_merger(Path(path))


@pytest.mark.parametrize(
    "caption,width,expected",
    [
        ("Table 1. Continued", 100, True),
        ("Table 1. (Continued)", 100, True),
        ("Table 2. Another table", 100, False),
        ("Unrelated paragraph", 100, False),
        ("Continued", 120, False),
    ],
)
def test_real_official_positive_and_negative_contracts(official, caption, width, expected):
    data = pages(
        [block(0)], [block(1, label="figure_title", content=caption), block(2, width=width)]
    )
    baseline = remerge_document(data, official, content_compat=False)
    assert baseline == data
    merged = remerge_document(data, official, content_compat=True)
    tables, _ = adapt_document(merged, "PMC1", 2)
    assert len(tables) == (1 if expected else 2)


def test_real_official_three_page_chain_keeps_empty_middle_and_tail(official):
    data = pages([block(0)], [block(1)], [block(2)])
    merged = remerge_document(data, official, content_compat=True)
    tables, _ = adapt_document(merged, "PMC1", 3)
    assert len(tables) == 1
    assert tables[0]["source_pages"] == [0, 1, 2]
