"""Embedding replacement adapter, not a verified Qwen integration.

Native input_ids remain available for image expansion and mRoPE. A later wrapper
must extract bidirectional evidence and compute the prefix without target access.
No tokenizer IDs are created here. This adapter is not safe for concurrent calls
on the same embedding module while its context is active.
"""

from contextlib import contextmanager

import torch


def prepend_prefix_inputs(batch, prefix_length, placeholder_token_id):
    """Prepare an unpadded, equal-length batch; native model recomputes positions."""
    if not isinstance(prefix_length, int) or isinstance(prefix_length, bool) or prefix_length < 1:
        raise ValueError("prefix_length must be a positive integer")
    if (
        not isinstance(placeholder_token_id, int)
        or isinstance(placeholder_token_id, bool)
        or placeholder_token_id < 0
    ):
        raise ValueError("placeholder_token_id must be an existing nonnegative ordinary token ID")
    for key in ("past_key_values", "cache_position", "position_ids", "inputs_embeds"):
        if key in batch:
            raise ValueError(f"{key} must be absent before preparing prefix inputs")
    ids = batch["input_ids"]
    if ids.ndim != 2 or min(ids.shape) < 1 or ids.dtype != torch.long:
        raise ValueError("input_ids must be a nonempty long [batch,length] tensor")
    mask = batch.get("attention_mask")
    if mask is None or mask.shape != ids.shape or mask.device != ids.device:
        raise ValueError("attention_mask must match input_ids shape and device")
    if not (mask == 1).all():
        raise ValueError("padding is unsupported; supply equal-length unpadded samples")
    result = dict(batch)
    shape = (ids.shape[0], prefix_length)
    result["input_ids"] = torch.cat((ids.new_full(shape, placeholder_token_id), ids), dim=1)
    result["attention_mask"] = torch.cat((mask.new_ones(shape), mask), dim=1)
    if "labels" in batch:
        labels = batch["labels"]
        if labels.shape != ids.shape or labels.device != ids.device or labels.dtype != torch.long:
            raise ValueError("labels must match input_ids shape, device and integer dtype")
        result["labels"] = torch.cat((labels.new_full(shape, -100), labels), dim=1)
    return result


@contextmanager
def inject_prefix_embeddings(embedding, prepared_ids, prefix):
    """Replace only an exact full-sequence embedding call; skip cached single tokens.

    The caller must retain this context for any checkpointed backward recomputation.
    Single-token calls are treated as cached decoding; this adapter cannot prove
    that a decoder actually uses its cache. Real cache/mRoPE acceptance is separate.
    """
    if (
        prepared_ids.ndim != 2
        or prepared_ids.dtype != torch.long
        or prefix.ndim != 3
        or prefix.shape[0] != prepared_ids.shape[0]
        or not 0 < prefix.shape[1] < prepared_ids.shape[1]
    ):
        raise ValueError("prefix and prepared_ids dimensions do not match")
    if (
        prefix.device != prepared_ids.device
        or prefix.device != embedding.weight.device
        or prefix.shape[2] != embedding.weight.shape[1]
        or prefix.dtype != embedding.weight.dtype
    ):
        raise ValueError("prefix device, dtype and embedding dimension must match")
    expected = prepared_ids.detach().clone()

    def hook(module, args, kwargs, output):
        ids = args[0] if args else kwargs.get("input")
        if ids is None or ids.ndim != 2 or ids.shape[0] != expected.shape[0]:
            raise ValueError("embedding input must match prepared batch")
        if ids.shape[1] == 1:
            return output
        if ids.shape != expected.shape or not torch.equal(ids, expected):
            raise ValueError("embedding input must exactly match prepared_ids")
        if output.device != prefix.device or output.dtype != prefix.dtype:
            raise ValueError("embedding output device and dtype must match prefix")
        return torch.cat((prefix, output[:, prefix.shape[1] :]), dim=1)

    handle = embedding.register_forward_hook(hook, with_kwargs=True)
    try:
        yield
    finally:
        handle.remove()
