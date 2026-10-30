"""CPU-only OCRFlux table reconstruction with element identity and provenance."""

from __future__ import annotations

import ast
import copy
import re


class ResourceSafetyStop(RuntimeError):
    """Resource failures must stop the run rather than become model errors."""


def parse_pairs(text, left_size, right_size):
    if not isinstance(text, str) or len(text) > 65536:
        raise ValueError("Invalid detection response size/type")
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError, RecursionError) as exc:
        raise ValueError("Invalid detection literal") from exc
    if not isinstance(value, (list, tuple)):
        raise ValueError("Expected pair list")
    pairs, left, right = [], set(), set()
    for pair in value:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("Expected two indices")
        a, b = pair
        if (
            type(a) is not int
            or type(b) is not int
            or not 0 <= a < left_size
            or not 0 <= b < right_size
            or a in left
            or b in right
        ):
            raise ValueError("Out-of-bounds, duplicate or conflicting indices")
        left.add(a)
        right.add(b)
        pairs.append((a, b))
    return pairs


def is_table(text):
    return isinstance(text, str) and text.startswith("<table>") and text.endswith("</table>")


def reconstruct(document_id, pages, detect, merge):
    """Callbacks call official prompts; no truth, HTML deduplication or repair."""
    if not re.fullmatch(r"PMC[0-9]+", document_id) or not pages:
        raise ValueError("Invalid document")
    if any(
        p is not None and (not isinstance(p, list) or any(not isinstance(s, str) for s in p))
        for p in pages
    ):
        raise ValueError("Invalid page elements")
    nodes = {
        (p, i): {"html": s, "source_pages": [p], "members": [[p, i]]}
        for p, elements in enumerate(pages)
        if elements is not None
        for i, s in enumerate(elements)
        if is_table(s)
    }

    def export(mapping):
        return [
            {
                "document_id": document_id,
                "table_id": f"{document_id}-p{p}-e{i}",
                "html": n["html"],
                "source_pages": sorted(n["source_pages"]),
            }
            for (p, i), n in sorted(mapping.items())
        ]

    original = export(nodes)
    edges, decisions = [], []
    for p in range(len(pages) - 1):
        if pages[p] is None or pages[p + 1] is None:
            continue
        event = {"stage": "detect", "pages": [p, p + 1]}
        try:
            text = detect(copy.deepcopy(pages[p]), copy.deepcopy(pages[p + 1]))
            pairs = parse_pairs(text, len(pages[p]), len(pages[p + 1]))
            event.update(status="ok", pairs=pairs)
            edges.extend(
                ((p, a), (p + 1, b)) for a, b in pairs if (p, a) in nodes and (p + 1, b) in nodes
            )
        except (RuntimeError, MemoryError):
            raise
        except Exception as exc:
            event.update(status="error", error=f"{type(exc).__name__}: {exc}")
        decisions.append(event)
    # Keep nodes until the reverse chain completes, then suppress consumed nodes.
    consumed = set()
    for a, b in sorted(edges, key=lambda pair: -pair[0][0]):
        event = {"stage": "merge", "left": a, "right": b}
        try:
            html = merge(nodes[a]["html"], nodes[b]["html"])
            if not is_table(html):
                raise ValueError("Reconstruction did not return one table envelope")
            nodes[a] = {
                "html": html,
                "source_pages": sorted(set(nodes[a]["source_pages"] + nodes[b]["source_pages"])),
                "members": nodes[a]["members"] + nodes[b]["members"],
            }
            consumed.add(b)
            event.update(
                status="ok", members=nodes[a]["members"], source_pages=nodes[a]["source_pages"]
            )
        except (RuntimeError, MemoryError):
            raise
        except Exception as exc:
            event.update(status="error", error=f"{type(exc).__name__}: {exc}")
        decisions.append(event)
    return {
        "no_merge": original,
        "merged": export({k: v for k, v in nodes.items() if k not in consumed}),
        "decisions": decisions,
    }
