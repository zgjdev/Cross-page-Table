import hashlib

import pytest

from cptla.reconstruction.qwen_processor import QwenProcessorAdapter


class FakeProcessor:
    def apply_chat_template(self, messages, **kwargs):
        self.messages, self.kwargs = messages, kwargs
        return {
            "input_ids": [[1, 2]],
            "attention_mask": [[1, 1]],
            "pixel_values": "pixels",
            "image_grid_thw": "grid",
        }


def test_verified_images_and_visual_fields(tmp_path):
    image = tmp_path / "crop.png"
    image.write_bytes(b"fixture")
    proc = FakeProcessor()
    adapter = QwenProcessorAdapter(
        proc, tmp_path, {"crop.png": hashlib.sha256(b"fixture").hexdigest()}
    )
    messages = [{"role": "user", "content": [{"type": "image", "image": "crop.png"}]}]
    result = adapter(messages, add_generation_prompt=True, truncation=False)
    assert result["input_ids"] == [1, 2]
    assert result["pixel_values"] == "pixels"
    assert proc.messages[0]["content"][0]["image"] == str(image)
    assert messages[0]["content"][0]["image"] == "crop.png"
    assert proc.kwargs["truncation"] is False
    image.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA"):
        adapter(messages, add_generation_prompt=True, truncation=False)


def test_reject_unlisted_or_escape(tmp_path):
    adapter = QwenProcessorAdapter(FakeProcessor(), tmp_path, {})
    for path in ["../outside.png", "https://example.com/x", "unknown.png"]:
        with pytest.raises(ValueError):
            adapter(
                [{"role": "user", "content": [{"type": "image", "image": path}]}],
                add_generation_prompt=True,
                truncation=False,
            )
