"""完整上下文的分块词表交叉熵；不分块或截断表格输入/目标。"""


def chunked_causal_loss(hidden_states, lm_head, labels, *, chunk_size=512):
    import torch
    from torch.nn import functional as F
    from torch.utils.checkpoint import checkpoint

    if (
        type(chunk_size) is not int
        or chunk_size <= 0
        or hidden_states.ndim != 3
        or hidden_states.shape[0] != 1
        or labels.shape != hidden_states.shape[:2]
        or not isinstance(lm_head, torch.nn.Linear)
    ):
        raise ValueError("expected single-example full labels/hidden states")
    positions = torch.nonzero(labels[0, 1:] != -100, as_tuple=False).flatten()
    if positions.numel() == 0:
        raise ValueError("no supervised causal targets")

    def block_loss(hidden, target):
        return F.cross_entropy(lm_head(hidden).float(), target, reduction="sum")

    total = None
    for start in range(0, positions.numel(), chunk_size):
        selected = positions[start : start + chunk_size]
        # Position i predicts label i+1, including the first assistant token.
        hidden = hidden_states[0, selected]
        target = labels[0, selected + 1]
        value = checkpoint(
            block_loss, hidden, target, use_reentrant=False, preserve_rng_state=False
        )
        total = value if total is None else total + value
    return total / positions.numel()
