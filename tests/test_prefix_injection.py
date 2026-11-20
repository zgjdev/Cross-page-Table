import importlib.util

import pytest


def test_prefix_adapter_exists():
    assert importlib.util.find_spec("cptla.reconstruction.prefix_injection") is not None


def test_injection_contract():
    torch = pytest.importorskip("torch")
    from cptla.reconstruction.prefix_injection import (
        inject_prefix_embeddings,
        prepend_prefix_inputs,
    )

    for batch_size in (1, 2):
        ids = torch.tensor([[3, 4, 5]]).expand(batch_size, -1)
        pixels = torch.randn(2, 8)
        batch = dict(
            input_ids=ids,
            attention_mask=torch.ones_like(ids),
            labels=ids.clone(),
            pixel_values=pixels,
        )
        prepared = prepend_prefix_inputs(batch, 2, 1)
        assert prepared["pixel_values"] is pixels
        assert prepared["input_ids"].shape == (batch_size, 5)
        assert (prepared["labels"][:, :2] == -100).all()
        assert prepared["attention_mask"].sum() == batch_size * 5
        embedding = torch.nn.Embedding(10, 6)
        prefix = torch.randn(batch_size, 2, 6, requires_grad=True)
        original = embedding(prepared["input_ids"]).detach()
        with inject_prefix_embeddings(embedding, prepared["input_ids"], prefix):
            output = embedding(prepared["input_ids"])
            torch.testing.assert_close(output[:, :2], prefix)
            torch.testing.assert_close(output[:, 2:], original[:, 2:])
            output.sum().backward()
            assert prefix.grad.abs().sum() > 0
            single = ids[:, :1]
            torch.testing.assert_close(embedding(single), embedding.weight[single])
            with pytest.raises(ValueError, match="match"):
                embedding(torch.zeros_like(prepared["input_ids"]))
        torch.testing.assert_close(embedding(prepared["input_ids"]), original)
        with pytest.raises(RuntimeError):
            with inject_prefix_embeddings(embedding, prepared["input_ids"], prefix):
                raise RuntimeError("abort")
        assert not embedding._forward_hooks
        for key, value in [("position_ids", ids), ("past_key_values", ())]:
            with pytest.raises(ValueError):
                prepend_prefix_inputs(dict(batch, **{key: value}), 2, 1)
        with pytest.raises(ValueError, match="padding"):
            prepend_prefix_inputs(dict(batch, attention_mask=torch.zeros_like(ids)), 2, 1)
