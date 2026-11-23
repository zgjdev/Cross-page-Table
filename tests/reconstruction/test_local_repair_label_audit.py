import importlib
import json
from pathlib import Path


def load_audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("audit_reconstruction_local_repair_labels")


def table(rows):
    return (
        "<table>"
        + "".join("<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>" for row in rows)
        + "</table>"
    )


def test_strict_anchors_and_target_boundary_witness(monkeypatch):
    audit = load_audit(monkeypatch)
    header = ["Headline", "Title"]
    alpha = ["Alpha unique", "item a"]
    beta = ["Beta unique", "item b"]
    gamma = ["Gamma unique", "item c"]
    truth = audit.html_to_grid(table([header, alpha, beta, gamma]))
    parts = [
        {"page_num": 1, "html": table([header, alpha])},
        {"page_num": 2, "html": table([["Beta unique", "missing", "extra"]])},
        {"page_num": 3, "html": table([header, gamma])},
    ]
    label, status, _ = audit.inspect_group(parts, truth)
    assert status == "accepted_weak_label"
    assert (label["truth_row_start"], label["truth_row_end"]) == (2, 3)
    assert label["anchors"] == [(0, 0, 0, 2), (2, 1, 3, 4)]
    parts[1]["html"] = table([["Wrong first/last", "missing", "extra"]])
    assert audit.inspect_group(parts, truth)[1] == (
        "target_boundary_missing_unique_text_or_split_row_suspected"
    )
    parts[0]["html"] = table([header, ["Alfa unique", "item a"]])
    assert audit.inspect_group(parts, truth)[1] == "anchor_rows_not_exact_and_contiguous"


def test_gt_boundaries_never_cut_span_and_excluded_rows_not_decoded(monkeypatch):
    audit = load_audit(monkeypatch)
    truth = audit.html_to_grid(
        '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'
    )
    assert audit.split_points(truth) == {0, 2}
    one = {"group_id": "allowed", "html": "line\u2028separator"}
    raw = json.dumps(one, ensure_ascii=False).encode("utf-8") + b"\nnot parsed"
    assert audit.records(raw, {"allowed"}) == {"allowed": one}


def test_character_relaxation_preserves_geometry_and_exact_boundary_evidence(monkeypatch):
    audit = load_audit(monkeypatch)
    left = (((1, 0, 1, "Unique anchor evidence"), (1, 1, 2, "One OCR character err0r")),)
    right = (((1, 0, 1, "Unique anchor evidence"), (1, 1, 2, "One OCR character error")),)
    counts = {"Unique anchor evidence": 1, "One OCR character error": 1}
    assert not audit.anchor_matches(left, right, counts, "strict")
    assert audit.anchor_matches(left, right, counts, "char95")
    assert not audit.anchor_matches(left, right, {}, "char95")
    wrong_extent = (((1, 0, 2, "Unique anchor evidence"), (1, 1, 2, "One OCR character error")),)
    assert not audit.anchor_matches(left, wrong_extent, counts, "char95")
