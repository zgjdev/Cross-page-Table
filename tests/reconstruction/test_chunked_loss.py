import pytest


def test_chunked_causal_loss_and_gradients_match_full():
    torch = pytest.importorskip("torch")
    from cptla.reconstruction.chunked_loss import chunked_causal_loss

    torch.manual_seed(11)
    hidden = torch.randn(1, 9, 4, requires_grad=True)
    head = torch.nn.Linear(4, 13, bias=False)
    labels = torch.tensor([[-100, -100, -100, 3, 8, 2, 7, 4, 1]])
    full = torch.nn.functional.cross_entropy(
        head(hidden[:, :-1]).reshape(-1, 13), labels[:, 1:].reshape(-1)
    )
    full.backward()
    expected = hidden.grad.clone(), head.weight.grad.clone()
    hidden.grad = head.weight.grad = None
    actual = chunked_causal_loss(hidden, head, labels, chunk_size=2)
    actual.backward()
    torch.testing.assert_close(full, actual)
    torch.testing.assert_close(hidden.grad, expected[0])
    torch.testing.assert_close(head.weight.grad, expected[1])
    assert torch.count_nonzero(hidden.grad[:, :2]) == 0
    assert torch.count_nonzero(hidden.grad[:, -1]) == 0


def test_reject_empty_or_incompatible_labels():
    torch = pytest.importorskip("torch")
    from cptla.reconstruction.chunked_loss import chunked_causal_loss

    hidden = torch.ones(1, 3, 2, requires_grad=True)
    head = torch.nn.Linear(2, 5)
    with pytest.raises(ValueError):
        chunked_causal_loss(hidden, head, torch.full((1, 3), -100), chunk_size=2)
    with pytest.raises(ValueError):
        chunked_causal_loss(hidden, head, torch.ones(1, 2, dtype=torch.long), chunk_size=2)
