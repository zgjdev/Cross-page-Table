import importlib.util
from pathlib import Path

import pytest

from cptla.reconstruction.grid import GridError
from cptla.reconstruction.structure_features import prediction_nodes

SPEC = importlib.util.spec_from_file_location(
    "paired", Path(__file__).parents[2] / "scripts/run_reconstruction_paired_pilot.py"
)
paired = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paired)


def test_scale_scope_validates_split_and_clusters():
    rows = [
        dict(group_id="train", document_id="a", cluster_id="x", split="train_fit"),
        dict(group_id="dev", document_id="b", cluster_id="y", split="train_dev"),
    ]
    overlay = [
        dict(document_id="a", cluster_id="x", effective_split="train_fit", observed_cluster=True),
        dict(document_id="b", cluster_id="y", effective_split="train_dev", observed_cluster=False),
    ]
    assert paired.document_split(rows, ["train"], ["dev"], overlay=overlay) == {
        "train": "a",
        "dev": "b",
    }
    overlay[1]["observed_cluster"] = True
    with pytest.raises(ValueError, match="overlay"):
        paired.document_split(rows, ["train"], ["dev"], overlay=overlay)
    overlay[1]["observed_cluster"] = False
    overlay[1]["cluster_id"] = rows[1]["cluster_id"] = "x"
    with pytest.raises(ValueError, match="cluster"):
        paired.document_split(rows, ["train"], ["dev"], overlay=overlay)


def test_parseable_nodes_survive_malformed_upstream_fragment():
    fragments = [
        dict(image_path="a", prediction_html="<table><tr><td>x</td></tr></table>"),
        dict(image_path="b", prediction_html="<table><tr><td>broken"),
    ]
    with pytest.raises(GridError):
        prediction_nodes(fragments)
    nodes = prediction_nodes(fragments, tolerate_invalid_html=True)
    assert [text for text, _ in nodes] == ["x"]
    assert prediction_nodes(fragments[1:], tolerate_invalid_html=True) == []


def test_trainables_only_resume_restores_slots_optimizer_and_order(tmp_path):
    torch = pytest.importorskip("torch")
    from cptla.reconstruction.checkpoint_state import load_state, save_state

    lora = torch.nn.Parameter(torch.tensor([1.0]))
    slots = torch.nn.Parameter(torch.tensor([2.0]))
    state = paired.TrainableState({"lora_B": lora, "structure.slot_queries": slots})
    optimizer = torch.optim.AdamW([lora, slots], lr=0.1)
    (lora.square() + slots.square()).sum().backward()
    optimizer.step()
    expected = {name: value.clone() for name, value in state.state_dict().items()}
    config = {"arm": "structure", "order": ["x", "y"]}
    save_state(tmp_path, "checkpoint", state, optimizer, step=7, cursor=7, config=config)
    other_lora = torch.nn.Parameter(torch.zeros_like(lora))
    other_slots = torch.nn.Parameter(torch.zeros_like(slots))
    other = paired.TrainableState({"lora_B": other_lora, "structure.slot_queries": other_slots})
    other_opt = torch.optim.AdamW([other_lora, other_slots], lr=0.1)
    assert load_state(tmp_path, "checkpoint", other, other_opt, config=config, trusted=True) == {
        "step": 7,
        "cursor": 7,
    }
    for name, value in other.state_dict().items():
        assert torch.equal(value, expected[name])
    assert torch.equal(other_opt.state[other_slots]["exp_avg"], optimizer.state[slots]["exp_avg"])
    with pytest.raises(ValueError, match="config mismatch"):
        load_state(
            tmp_path,
            "checkpoint",
            other,
            other_opt,
            config=config | {"order": ["y", "x"]},
            trusted=True,
        )
