import pytest

from cptla.reconstruction.supervised_logits import supervised_suffix


def test_keep_last_prompt_position_and_all_targets():
    row = dict(input_ids=[1, 2, 3, 4, 5], labels=[-100, -100, 3, 4, 5], pixel_values=object())
    result = supervised_suffix(row)
    assert result["labels"] == [-100, 3, 4, 5]
    assert result["logits_to_keep"] == 4
    assert result["input_ids"] is row["input_ids"]
    assert result["pixel_values"] is row["pixel_values"]
    assert row["labels"] == [-100, -100, 3, 4, 5]


@pytest.mark.parametrize("labels", [[], [-100, -100], [1, 2], [-100, 2, -100], [-100, -2]])
def test_reject_unsupported_mask(labels):
    with pytest.raises(ValueError):
        supervised_suffix(dict(input_ids=[1] * len(labels), labels=labels))


def test_loss_and_gradients_match_full_masked_sequence():
    torch = pytest.importorskip("torch")
    torch.manual_seed(7)
    hidden = torch.randn(1, 7, 4, dtype=torch.float64, requires_grad=True)
    weight = torch.randn(11, 4, dtype=torch.float64, requires_grad=True)
    labels = [-100, -100, -100, 3, 7, 2, 6]

    def loss(logits, targets):
        shifted = torch.tensor(targets[1:] + [-100])
        return torch.nn.functional.cross_entropy(logits.reshape(-1, 11), shifted)

    full = loss(hidden @ weight.T, labels)
    full.backward()
    original = (hidden.grad.clone(), weight.grad.clone())
    hidden.grad = weight.grad = None
    suffix = supervised_suffix(dict(input_ids=list(range(7)), labels=labels))
    reduced = loss(hidden[:, -suffix["logits_to_keep"] :] @ weight.T, suffix["labels"])
    reduced.backward()
    torch.testing.assert_close(full, reduced, rtol=1e-14, atol=1e-14)
    for actual, expected in zip((hidden.grad, weight.grad), original, strict=True):
        torch.testing.assert_close(actual, expected, rtol=1e-14, atol=1e-14)
