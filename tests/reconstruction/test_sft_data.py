import pytest

from cptla.reconstruction.grid import GRID_VERSION
from cptla.reconstruction.sft_data import SFTCollator, build_messages


def sample(split="train_fit"):
    inputs = dict(
        group_id="g",
        split=split,
        track="image-only",
        fragments=[
            dict(image_path="crops/a.png", prediction_html="<table><tr><td>p</td></tr></table>")
        ],
    )
    target = dict(
        group_id="g", grid_version=GRID_VERSION, html="<table><tr><td>SECRET</td></tr></table>"
    )
    return inputs, target


class MockProcessor:
    def __call__(self, messages, *, add_generation_prompt, truncation):
        assert truncation is False
        if add_generation_prompt:
            return dict(input_ids=[1, 2, 3], attention_mask=[1] * 3)
        return dict(input_ids=[1, 2, 3, 40, 41], attention_mask=[1] * 5, pixels="kept")


def test_target_only_in_assistant_and_mask():
    inputs, target = sample()
    messages = build_messages(inputs, target)
    assert "SECRET" not in str(messages[:-1])
    assert messages[-1]["content"] == target["html"]
    collator = SFTCollator(MockProcessor(), max_tokens=5)
    out = collator([(inputs, target)])
    assert out[0]["labels"] == [-100, -100, -100, 40, 41]
    assert out[0]["pixels"] == "kept"


def test_grid_target_isolated_and_canonical():
    import json

    inputs, target = sample()
    messages = build_messages(inputs, target, output_format="grid")
    assert "SECRET" not in str(messages[:-1])
    payload = json.loads(messages[-1]["content"])
    assert payload["schema_version"] == "global-grid-v1"
    assert payload["cells"][0]["text"] == "SECRET"
    assert "global-grid-v1" in messages[0]["content"][0]["text"]
    output = SFTCollator(MockProcessor(), 5, output_format="grid")([(inputs, target)])
    assert output[0]["labels"] == [-100, -100, -100, 40, 41]


@pytest.mark.parametrize("split", ["test", "train_confirm", "train_dev", "validation"])
def test_nonfit_forbidden(split):
    with pytest.raises(ValueError):
        build_messages(*sample(split))


def test_overflow_rejected_and_counted():
    c = SFTCollator(MockProcessor(), max_tokens=4)
    with pytest.raises(ValueError, match="token_budget_exceeded"):
        c([sample()])
    assert c.counts["token_budget_exceeded"] == 1


def test_target_in_input_and_wrong_identity_rejected():
    i, t = sample()
    i["target_html"] = t["html"]
    with pytest.raises(ValueError):
        build_messages(i, t)
    i, t = sample()
    t["group_id"] = "other"
    with pytest.raises(ValueError):
        build_messages(i, t)


def test_multimage_order_and_no_target_rewrite():
    i, t = sample()
    i["fragments"].append(dict(image_path="crops/b.png", prediction_html="raw broken HTML"))
    m = build_messages(i, t)
    images = [c["image"] for c in m[0]["content"] if c["type"] == "image"]
    assert images == ["crops/a.png", "crops/b.png"]
    assert m[-1]["content"] == t["html"]


def test_nonprefix_tokenization_rejected():
    class BadProcessor(MockProcessor):
        def __call__(self, messages, *, add_generation_prompt, truncation):
            row = super().__call__(
                messages, add_generation_prompt=add_generation_prompt, truncation=truncation
            )
            if not add_generation_prompt:
                row["input_ids"][0] = 99
            return row

    c = SFTCollator(BadProcessor(), 10)
    with pytest.raises(ValueError, match="assistant_boundary_not_verified"):
        c([sample()])
    assert c.counts["rejected"] == 1
