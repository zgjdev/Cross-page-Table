import importlib.util

import pytest


def test_module_exists():
    assert importlib.util.find_spec("cptla.reconstruction.structure_memory") is not None


@pytest.mark.parametrize("batch", [1, 2])
def test_memory_contract(batch, tmp_path):
    torch = pytest.importorskip("torch")
    from cptla.reconstruction.structure_memory import StructureMemory

    torch.manual_seed(17)
    kwargs = dict(
        visual_dim=6,
        node_dim=5,
        decoder_dim=12,
        hidden_dim=16,
        num_blocks=2,
        num_heads=4,
        num_slots=4,
        num_summary=2,
    )
    model = StructureMemory(**kwargs).eval()
    visual, nodes = torch.randn(batch, 5, 6), torch.randn(batch, 3, 5)
    vm = torch.tensor([[True, True, True, False, False]]).expand(batch, -1)
    nm = torch.tensor([[True, True, False]]).expand(batch, -1)
    out = model(visual, nodes, vm, nm)
    assert out["prefix"].shape == (batch, 6, 12)
    assert out["count_logits"].shape == (batch, 4)
    assert out["col_end_logits"].shape == (batch, 3, 4)
    assert torch.all(out["slot_gates"][:, :-1] >= out["slot_gates"][:, 1:])
    altered_v, altered_n = visual.clone(), nodes.clone()
    altered_v[~vm], altered_n[~nm] = float("nan"), float("nan")
    torch.testing.assert_close(out["prefix"], model(altered_v, altered_n, vm, nm)["prefix"])
    altered_v[:, 2] += 3
    assert not torch.allclose(out["prefix"], model(altered_v, altered_n, vm, nm)["prefix"])
    with pytest.raises(ValueError, match="evidence"):
        model(visual, nodes, torch.zeros_like(vm), torch.zeros_like(nm))
    assert torch.isfinite(model(visual, nodes, vm, torch.zeros_like(nm))["prefix"]).all()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    before = model.slot_queries.detach().clone()
    loss = out["prefix"].square().mean() + out["count_logits"].square().mean()
    loss.backward()
    assert model.slot_queries.grad.abs().sum() > 0
    assert model.visual_projection.weight.grad.abs().sum() > 0
    optimizer.step()
    assert not torch.equal(before, model.slot_queries)
    path = tmp_path / "weights.pt"
    torch.save(model.state_dict(), path)
    restored = StructureMemory(**kwargs).eval()
    restored.load_state_dict(torch.load(path, weights_only=True))
    torch.testing.assert_close(
        model(visual, nodes, vm, nm)["prefix"], restored(visual, nodes, vm, nm)["prefix"]
    )
