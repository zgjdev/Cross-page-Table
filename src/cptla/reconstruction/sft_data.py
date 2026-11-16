"""B3 CPU 数据接口；processor 适配器与真正训练循环尚未实现。"""

from collections import Counter
from pathlib import PurePosixPath

from cptla.reconstruction.grid import GRID_VERSION, html_to_grid


def output_instruction(output_format):
    if output_format == "html":
        return "根据按顺序提供的表格片段图像及局部预测，恢复完整表格。只输出完整 HTML table。"
    if output_format == "grid":
        return (
            "根据按顺序提供的表格片段图像及局部预测，恢复完整表格。只输出global-grid-v1 JSON："
            "schema_version,num_rows,num_cols,cells；每个cell包含r0,r1,c0,c1,text,role。"
            "坐标为零起点半开区间，role为header或data；完整覆盖网格，无重叠，不输出代码围栏。"
        )
    raise ValueError("unsupported_output_format")


def build_messages(inputs, target, *, output_format="html"):
    """严格白名单隔离输入/标签；只接受显式 train_fit/image-only。"""
    if set(inputs) != {"group_id", "split", "track", "fragments"}:
        raise ValueError("unexpected_input_fields")
    if inputs["split"] != "train_fit" or inputs["track"] != "image-only":
        raise ValueError("training_split_or_track_forbidden")
    if set(target) != {"group_id", "grid_version", "html"}:
        raise ValueError("unexpected_target_fields")
    if not inputs["group_id"] or target["group_id"] != inputs["group_id"]:
        raise ValueError("target_identity_mismatch")
    if target["grid_version"] != GRID_VERSION:
        raise ValueError("grid_version_mismatch")
    html_to_grid(target["html"])  # 仅验证；标签原文不改写。
    instruction = output_instruction(output_format)
    target_text = target["html"]
    if output_format == "grid":
        from cptla.reconstruction.grid_sequence import html_to_sequence

        target_text = html_to_sequence(target_text)
    fragments = inputs["fragments"]
    if not isinstance(fragments, list) or not fragments:
        raise ValueError("empty_fragments")
    content = [
        {
            "type": "text",
            "text": instruction,
        }
    ]
    for f in fragments:
        if set(f) != {"image_path", "prediction_html"}:
            raise ValueError("unexpected_fragment_fields")
        path = f["image_path"]
        if (
            not isinstance(path, str)
            or not path
            or "\\" in path
            or ":" in path
            or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts
        ):
            raise ValueError("invalid_relative_image_path")
        if not isinstance(f["prediction_html"], str):
            raise ValueError("invalid_prediction_text")
        content.extend(
            [{"type": "image", "image": path}, {"type": "text", "text": f["prediction_html"]}]
        )
    return [{"role": "user", "content": content}, {"role": "assistant", "content": target_text}]


class SFTCollator:
    """返回未padding的逐例encoding，非HF Trainer可直接使用的tensor collator。

    注入适配器接收 messages/add_generation_prompt/truncation=False，返回单例
    list[int] input_ids/attention_mask 及其他视觉字段。必须完整编码且不得截断。
    prompt编码含assistant生成前缀，full编码必须以其开头；不满足则拒绝。
    """

    def __init__(self, processor, max_tokens, *, output_format="html"):
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("invalid_token_budget")
        self.processor, self.max_tokens = processor, max_tokens
        output_instruction(output_format)
        self.output_format = output_format
        self.counts = Counter()

    def __call__(self, examples):
        batch = []
        for inputs, target in examples:
            self.counts["seen"] += 1
            try:
                messages = build_messages(inputs, target, output_format=self.output_format)
                prefix = self.processor(messages[:-1], add_generation_prompt=True, truncation=False)
                full = self.processor(messages, add_generation_prompt=False, truncation=False)
                ids, pids = full["input_ids"], prefix["input_ids"]
                if any(
                    not isinstance(x, list) or not x or any(type(t) is not int for t in x)
                    for x in (ids, pids)
                ):
                    raise ValueError("invalid_processor_token_ids")
                if len(ids) > self.max_tokens:
                    raise ValueError("token_budget_exceeded")
                if ids[: len(pids)] != pids or len(ids) <= len(pids):
                    raise ValueError("assistant_boundary_not_verified")
                if full.get("attention_mask") != [1] * len(ids):
                    raise ValueError("requires_unpadded_single_example")
                row = dict(full)
                row["labels"] = [-100] * len(pids) + ids[len(pids) :]
                batch.append(row)
                self.counts["encoded"] += 1
            except ValueError as error:
                self.counts[str(error)] += 1
                self.counts["rejected"] += 1
                raise
        self.counts["returned"] += len(batch)
        return batch
