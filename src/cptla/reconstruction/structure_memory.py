"""Standalone learned structural prefix; no decoder/cache integration or target inputs."""

import torch
from torch import nn


class _Block(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.read = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.interact = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.write = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.norms = nn.ModuleList([nn.LayerNorm(dim) for _ in range(3)])
        self.ff = nn.Sequential(nn.Linear(dim, dim * 4), nn.GELU(), nn.Linear(dim * 4, dim))

    def forward(self, slots, visual, nodes, valid, node_valid):
        evidence = torch.cat((visual, nodes), dim=1)
        slots = self.norms[0](
            slots
            + self.read(slots, evidence, evidence, key_padding_mask=~valid, need_weights=False)[0]
        )
        slots = self.norms[1](slots + self.interact(slots, slots, slots, need_weights=False)[0])
        slots = slots + self.ff(slots)
        nodes = self.norms[2](nodes + self.write(nodes, slots, slots, need_weights=False)[0])
        return slots, nodes.masked_fill(~node_valid.unsqueeze(-1), 0)


class StructureMemory(nn.Module):
    """Inputs include caller-provided fragment/position features, never GT features.

    Count classes are 1..num_slots; starts 0..K-1, exclusive ends 1..K.
    Padding logits must be ignored using node_valid. Boundary relations are not
    implemented: this interface has no row candidate edges or audited edge masks.
    """

    def __init__(
        self,
        visual_dim,
        node_dim,
        decoder_dim,
        hidden_dim=512,
        num_blocks=4,
        num_heads=8,
        num_slots=64,
        num_summary=16,
    ):
        super().__init__()
        if (
            min(
                visual_dim,
                node_dim,
                decoder_dim,
                hidden_dim,
                num_blocks,
                num_heads,
                num_slots,
                num_summary,
            )
            < 1
            or hidden_dim % num_heads
        ):
            raise ValueError("Dimensions must be positive and hidden_dim divisible by heads")
        self.visual_projection = nn.Linear(visual_dim, hidden_dim)
        self.node_projection = nn.Linear(node_dim, hidden_dim)
        self.slot_queries = nn.Parameter(torch.randn(num_slots, hidden_dim) * 0.02)
        self.summary_queries = nn.Parameter(torch.randn(num_summary, hidden_dim) * 0.02)
        self.blocks = nn.ModuleList([_Block(hidden_dim, num_heads) for _ in range(num_blocks)])
        self.count = nn.Linear(hidden_dim, num_slots)
        self.start = nn.Linear(hidden_dim, num_slots)
        self.end = nn.Linear(hidden_dim, num_slots)
        self.uncertain = nn.Linear(hidden_dim, 2)
        self.relation = nn.Linear(hidden_dim + 2 * num_slots + 2, hidden_dim)
        self.pool = nn.MultiheadAttention(hidden_dim, num_heads, batch_first=True)
        self.decoder_projection = nn.Linear(hidden_dim, decoder_dim)

    def forward(self, visual_tokens, node_features, visual_valid, node_valid):
        for features, mask, dim in (
            (visual_tokens, visual_valid, self.visual_projection.in_features),
            (node_features, node_valid, self.node_projection.in_features),
        ):
            if (
                features.ndim != 3
                or features.shape[-1] != dim
                or mask.shape != features.shape[:2]
                or mask.dtype != torch.bool
            ):
                raise ValueError("Expected [batch,length,dim] features and boolean valid masks")
            if not torch.isfinite(features[mask]).all():
                raise ValueError("Nonfinite valid evidence")
        if visual_tokens.shape[0] != node_features.shape[0]:
            raise ValueError("Batch sizes differ")
        valid = torch.cat((visual_valid, node_valid), dim=1)
        if not valid.any(dim=1).all():
            raise ValueError("Each sample requires evidence")
        visual = self.visual_projection(visual_tokens.masked_fill(~visual_valid[..., None], 0))
        nodes = self.node_projection(node_features.masked_fill(~node_valid[..., None], 0))
        slots = self.slot_queries.unsqueeze(0).expand(visual.shape[0], -1, -1)
        for block in self.blocks:
            slots, nodes = block(slots, visual, nodes, valid, node_valid)
        count_logits = self.count(slots.mean(dim=1))
        probabilities = count_logits.softmax(dim=-1)
        gates = probabilities.flip(-1).cumsum(-1).flip(-1)
        start, end, uncertain = self.start(nodes), self.end(nodes), self.uncertain(nodes)
        relations = self.relation(
            torch.cat((nodes, start.softmax(-1), end.softmax(-1), uncertain.softmax(-1)), dim=-1)
        )
        # Empty-node samples pool slots; otherwise only local relation vectors are visible.
        fallback = ~node_valid.any(dim=1, keepdim=True)
        pool_valid = torch.cat((node_valid, fallback.expand(-1, slots.shape[1])), dim=1)
        pool_values = torch.cat((relations, slots), dim=1)
        summary = self.pool(
            self.summary_queries.unsqueeze(0).expand(visual.shape[0], -1, -1),
            pool_values,
            pool_values,
            key_padding_mask=~pool_valid,
            need_weights=False,
        )[0]
        prefix = self.decoder_projection(torch.cat((slots * gates[..., None], summary), dim=1))
        return dict(
            prefix=prefix,
            count_logits=count_logits,
            slot_gates=gates,
            slots=slots,
            summary=summary,
            updated_nodes=nodes,
            col_start_logits=start,
            col_end_logits=end,
            uncertain_logits=uncertain,
            node_valid=node_valid,
        )
