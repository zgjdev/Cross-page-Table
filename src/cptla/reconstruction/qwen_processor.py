"""真实 Qwen processor 的单例适配；不加载模型或自动放行训练。"""

import hashlib
from copy import deepcopy
from pathlib import Path


class QwenProcessorAdapter:
    def __init__(self, processor, project_root, image_hashes):
        self.processor = processor
        self.root = Path(project_root).resolve()
        self.image_hashes = dict(image_hashes)

    def __call__(self, messages, *, add_generation_prompt, truncation):
        if truncation is not False:
            raise ValueError("target truncation forbidden")
        payload = deepcopy(messages)
        used = {}
        for message in payload:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if item.get("type") != "image":
                    continue
                name = item.get("image")
                if name not in self.image_hashes:
                    raise ValueError("unlisted image")
                path = (self.root / name).resolve()
                if not path.is_relative_to(self.root):
                    raise ValueError("image escapes project")
                if hashlib.sha256(path.read_bytes()).hexdigest() != self.image_hashes[name]:
                    raise ValueError("image SHA mismatch")
                used[path] = self.image_hashes[name]
                item["image"] = str(path)
        result = dict(
            self.processor.apply_chat_template(
                payload,
                tokenize=True,
                add_generation_prompt=add_generation_prompt,
                return_dict=True,
                return_tensors="pt",
                truncation=False,
            )
        )
        for key in ("input_ids", "attention_mask"):
            value = result[key]
            value = value.tolist() if hasattr(value, "tolist") else value
            if len(value) != 1 or not isinstance(value[0], list):
                raise ValueError("single example required")
            result[key] = value[0]
        for path, digest in used.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("image SHA changed during encoding")
        return result
