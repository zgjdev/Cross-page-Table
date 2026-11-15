"""只为监督后缀计算词表logits，完整输入/图像/attention保持不变。"""


def supervised_suffix(encoded):
    """Qwen3-VL/Transformers 4.57.1 causal loss适配，限单例连续监督后缀。

    保留最后一个prompt位置的logit以预测首个target token。labels同步截取，
    causal shift后监督集合与完整mask loss完全一致；这不是截断输入或目标。
    """
    labels = encoded.get("labels")
    if (
        not isinstance(labels, list)
        or len(labels) != len(encoded.get("input_ids", []))
        or not labels
        or labels[0] != -100
        or any(type(x) is not int or (x < 0 and x != -100) for x in labels)
    ):
        raise ValueError("expected full single-example labels with masked prompt")
    first = next((i for i, value in enumerate(labels) if value != -100), None)
    if first is None or any(value == -100 for value in labels[first:]):
        raise ValueError("expected nonempty contiguous supervised suffix")
    keep = len(labels) - first + 1
    return dict(encoded, labels=labels[-keep:], logits_to_keep=keep)
