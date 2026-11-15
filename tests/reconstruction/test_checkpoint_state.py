import random

import pytest

torch = pytest.importorskip("torch")
from cptla.reconstruction.checkpoint_state import load_state, save_state  # noqa: E402


def model():
    return torch.nn.Sequential(torch.nn.Linear(3, 4), torch.nn.Dropout(0.3), torch.nn.Linear(4, 1))


def step(network, optimizer):
    optimizer.zero_grad()
    loss = network(torch.ones(2, 3)).square().mean()
    loss.backward()
    optimizer.step()


def test_exact_optimizer_rng_resume(tmp_path):
    torch.manual_seed(73)
    random.seed(73)
    first = model()
    optimizer = torch.optim.AdamW(first.parameters(), lr=0.01)
    step(first, optimizer)
    save_state(tmp_path, "checkpoint", first, optimizer, step=1, cursor=1, config={"lr": 0.01})
    expected_random = random.random()
    step(first, optimizer)
    restored = model()
    resumed_optimizer = torch.optim.AdamW(restored.parameters(), lr=0.01)
    state = load_state(
        tmp_path, "checkpoint", restored, resumed_optimizer, config={"lr": 0.01}, trusted=True
    )
    assert state == {"step": 1, "cursor": 1}
    assert random.random() == expected_random
    step(restored, resumed_optimizer)
    assert all(
        torch.equal(a, b) for a, b in zip(first.parameters(), restored.parameters(), strict=True)
    )


def test_reject_config_tamper_and_overwrite(tmp_path):
    network = model()
    optimizer = torch.optim.AdamW(network.parameters())
    save_state(tmp_path, "checkpoint", network, optimizer, step=1, cursor=0, config={"x": 1})
    with pytest.raises(FileExistsError):
        save_state(tmp_path, "checkpoint", network, optimizer, step=1, cursor=0, config={"x": 1})
    with pytest.raises(ValueError, match="config"):
        load_state(tmp_path, "checkpoint", network, optimizer, config={"x": 2}, trusted=True)
    (tmp_path / "checkpoint/state.pt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA"):
        load_state(tmp_path, "checkpoint", network, optimizer, config={"x": 1}, trusted=True)
