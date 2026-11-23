import importlib
from pathlib import Path


def load_probe(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("probe_reconstruction_visual_repair")


def fragment(group, i, width):
    return dict(
        group_id=group,
        fragment_id=f"{group}-part-{i}",
        page_num=i + 1,
        part_index=i,
        status="completed",
        html="<table><tr>" + "<td>A</td>" * width + "</tr></table>",
    )


def test_probe_selection_is_seeded_and_prediction_only(monkeypatch):
    probe = load_probe(monkeypatch)
    rows = [
        dict(
            group_id=str(i),
            diagnostics=dict(
                failure_reasons=["column_mismatch"] if i < 30 else [],
                raw_predictions=[fragment(str(i), j, w) for j, w in enumerate([2, 1, 2])],
            ),
        )
        for i in range(200)
    ]
    cases, candidates = probe.select_cases(rows, 1)
    assert candidates == 30 and len(cases) == 3
    assert cases == probe.select_cases(list(reversed(rows)), 1)[0]
    assert all(case["target"] == 1 and case["context"] == 0 for case in cases)
    expanded, _ = probe.select_cases(rows, 1, case_count=8)
    assert expanded[:3] == cases
    assert len({case["group_id"] for case in expanded}) == 8


def test_repair_uses_shared_target_and_preserves_other_fragment(monkeypatch):
    probe = load_probe(monkeypatch)
    parts = [fragment("a", 0, 1), fragment("a", 1, 2)]
    case = dict(group_id="a", fragments=parts, target=0, context=1)
    content = [dict(type="text", text="previous template")]
    for i, part in enumerate(parts):
        content.extend([dict(type="image", image=f"{i}.png"), dict(type="text", text=part["html"])])
    example = dict(messages=[dict(role="user", content=content)])
    local, adjacent = [probe.arm_messages(example, case, mode)[0]["content"] for mode in probe.ARMS]
    assert local[-3:] == adjacent[-3:]
    assert [item["image"] for item in adjacent if item["type"] == "image"] == ["1.png", "0.png"]
    text_only = probe.arm_messages(example, case, "adjacent_html_only")[0]["content"]
    assert [item for item in adjacent if item.get("image") != "1.png"] == text_only

    good = probe.apply_repair(case, dict(status="completed", html=parts[1]["html"]))
    assert good["changed_dimensions"]["column_delta"] == 1
    assert good["merged"]["status"] == "completed"
    assert good["merged"]["diagnostics"]["raw_predictions"][1] == parts[1]
    assert probe.html_to_grid(parts[0]["html"]).n_cols == 1

    invalid = probe.apply_repair(case, dict(status="completed", html="not a table"))
    assert invalid["merged"]["status"] == "failed"
    assert invalid["raw_prediction"]["status"] == "invalid_html"
    truncated = probe.apply_repair(case, dict(status="truncated", html=parts[1]["html"]))
    assert truncated["merged"]["status"] == "failed"
