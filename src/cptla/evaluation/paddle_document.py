"""Lossless PaddleX 3.4.1 group provenance and isolated content-field compatibility."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

OFFICIAL_MERGE_SHA256 = "95a9fe523b4e226c8a2a7af70d770993b7ccb772afb6fc10dbe079f6083a19e0"


def _index(pages, expected_pages):
    if type(expected_pages) is not int or expected_pages < 1 or len(pages) != expected_pages:
        raise ValueError("Incomplete document page coverage")
    result = {}
    for number, page in enumerate(pages):
        data = page["res"]
        if (
            type(data["page_index"]) is not int
            or data["page_index"] != number
            or type(data["page_count"]) is not int
            or data["page_count"] != expected_pages
        ):
            raise ValueError("Page order/coverage mismatch")
        for block in data["parsing_res_list"]:
            identifier = block["global_block_id"]
            group = block["global_group_id"]
            if (
                type(identifier) is not int
                or identifier < 0
                or identifier in result
                or type(group) is not int
                or group < 0
            ):
                raise ValueError("Duplicate or invalid global block/group ID")
            if not isinstance(block["block_content"], str):
                raise ValueError("Expected literal block content")
            result[identifier] = (number, block)
    return result


def adapt_document(pages, document_id, expected_pages):
    """Return document tables + evidence; never infer provenance from HTML or GT."""
    index = _index(pages, expected_pages)
    groups = defaultdict(list)
    for identifier, (number, block) in index.items():
        if block["block_label"] != "table":
            continue
        group = block["global_group_id"]
        if group not in index:
            raise ValueError("Dangling table group reference")
        _, root = index[group]
        if root["block_label"] != "table" or root["global_group_id"] != group:
            raise ValueError("Group root must be a self-rooted table")
        groups[group].append((identifier, number, block))
    tables, evidence = [], []
    for group, members in sorted(groups.items()):
        nonempty = [b for _, _, b in members if b["block_content"].strip()]
        if len(nonempty) != 1 or nonempty[0]["global_block_id"] != group:
            raise ValueError("Expected exactly one nonempty HTML at table group root")
        source = sorted({number for _, number, _ in members})
        root_page = index[group][0]
        if root_page != min(source) or source != list(range(min(source), max(source) + 1)):
            raise ValueError("Noncontiguous or backward table source pages")
        identifier = f"{document_id}-group-{group}"
        tables.append(
            {
                "document_id": document_id,
                "table_id": identifier,
                "html": nonempty[0]["block_content"],
                "source_pages": source,
            }
        )
        evidence.append(
            {
                "document_id": document_id,
                "table_id": identifier,
                "global_group_id": group,
                "global_block_ids": [i for i, _, _ in members],
                "source_pages": source,
            }
        )
    return tables, evidence


def load_official_merger(path: Path):
    """Execute only the audited, hash-pinned official pure-Python merger."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != OFFICIAL_MERGE_SHA256:
        raise ValueError("Official merge source SHA mismatch")
    spec = importlib.util.spec_from_file_location("_pinned_paddlex_merge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.merge_tables_across_pages


def remerge_document(pages, merge_function, *, content_compat=False):
    """Replay official merging; compatibility adds only the expected text attribute.

    Input must be already restructured no_merge JSON (all global IDs assigned).
    We mirror PaddleOCRVLBlock fields used by the pinned pure merger, not the VLM.
    """
    index = _index(pages, len(pages))
    if list(index) != list(range(len(index))):
        raise ValueError("Official merging requires canonical sequential global IDs")
    if any(b["global_group_id"] != i for i, (_, b) in index.items()):
        raise ValueError("Expected unmerged input; refusing to merge twice")
    output = copy.deepcopy(pages)
    blocks = []
    for page in output:
        current = []
        for block in page["res"]["parsing_res_list"]:
            obj = SimpleNamespace(
                label=block["block_label"],
                bbox=list(map(int, block["block_bbox"])),
                content=block["block_content"],
                global_block_id=block["global_block_id"],
                global_group_id=block["global_group_id"],
            )
            if content_compat:
                obj.text = obj.content
            current.append(obj)
        blocks.append(current)
    merged = merge_function(blocks)
    if len(merged) != len(output):
        raise ValueError("Official merger changed page coverage")
    for page, objects in zip(output, merged, strict=True):
        original_blocks = page["res"]["parsing_res_list"]
        if len(original_blocks) != len(objects):
            raise ValueError("Official merger changed block coverage")
        for block, obj in zip(original_blocks, objects, strict=True):
            if block["global_block_id"] != obj.global_block_id:
                raise ValueError("Official merger reordered blocks")
            block["block_content"] = obj.content
            block["global_group_id"] = obj.global_group_id
    return output
