"""冻结视觉和片段预测节点的证据提取。"""

from cptla.reconstruction.grid import html_to_grid


def prediction_nodes(fragments):
    """Only predicted cell text/positions; deliberately no target parameter."""
    if not fragments:
        raise ValueError("empty predicted fragments")
    nodes = []
    for index, fragment in enumerate(fragments):
        if set(fragment) != {"image_path", "prediction_html"}:
            raise ValueError("unexpected feature input fields")
        grid = html_to_grid(fragment["prediction_html"])  # No repair or GT fallback.
        for cell in grid.cells:
            nodes.append(
                (
                    cell.text,
                    [
                        cell.row_start / grid.n_rows,
                        cell.row_end / grid.n_rows,
                        cell.col_start / grid.n_cols,
                        cell.col_end / grid.n_cols,
                        index / max(1, len(fragments) - 1),
                    ],
                )
            )
    return nodes


def structure_evidence(model, processor, batch, fragments):
    import torch

    records = prediction_nodes(fragments)
    embedding = model.get_input_embeddings()
    dim = embedding.weight.shape[1]
    with torch.no_grad():
        image_output = model.model.get_image_features(
            pixel_values=batch["pixel_values"], image_grid_thw=batch["image_grid_thw"]
        )
        if hasattr(image_output, "pooler_output"):
            image_parts = image_output.pooler_output
        elif isinstance(image_output, tuple) and len(image_output) == 2:
            image_parts = image_output[0]
        else:
            raise ValueError("unverified Qwen image feature return contract")
        if not isinstance(image_parts, (tuple, list)) or not image_parts:
            raise ValueError("expected per-image visual sequences")
        if any(part.ndim != 2 or part.shape[1] != dim for part in image_parts):
            raise ValueError("unexpected visual feature shape")
        if len(image_parts) != len(fragments):
            raise ValueError("visual/fragment coverage mismatch")
        visual_parts = [
            torch.cat(
                (
                    part.float(),
                    part.new_full((part.shape[0], 1), index / max(1, len(image_parts) - 1)).float(),
                ),
                dim=-1,
            )
            for index, part in enumerate(image_parts)
        ]
        visual = torch.cat(visual_parts, dim=0).unsqueeze(0).detach()
        node_values = []
        for text, positions in records:
            ids = processor.tokenizer.encode(text, add_special_tokens=False)
            # Empty predicted cells have a zero textual vector; never fill from GT.
            mean = (
                embedding(torch.tensor(ids, device="cuda")).float().mean(0)
                if ids
                else torch.zeros(dim, device="cuda")
            )
            node_values.append(torch.cat((mean, mean.new_tensor(positions))))
        nodes = torch.stack(node_values).unsqueeze(0).detach()
    return visual, nodes
