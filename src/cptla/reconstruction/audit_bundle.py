"""Server-side, read-only-source review images for oracle fragment audits."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) or value in {".", ".."}:
        raise ValueError(f"unsafe review identifier: {value!r}")
    return value


def _source(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        raise ValueError("image path must be project-relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("source image outside project")
    return path


def _save_png(image: Image.Image, path: Path) -> None:
    with path.open("xb") as stream:
        image.save(stream, format="PNG")


def _write_text(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def _html_document(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title>"
        "<style>body{font:16px sans-serif;max-width:1400px;margin:30px auto;padding:20px}"
        ".grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}"
        "img{max-width:100%;height:auto;border:1px solid #bbb}"
        "iframe{width:100%;height:650px;border:1px solid #999}"
        ".notice{padding:12px;background:#fff3d0}pre{white-space:pre-wrap}</style>"
        f"<body><h1>{html.escape(title)}</h1>{body}</body></html>\n"
    )


def write_audit_bundle(
    project_root: Path,
    output_dir: Path,
    inputs: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    sampling: dict[str, Any],
) -> dict[str, Any]:
    """Create review/ exactly once; supplied targets never become predictions."""
    root = project_root.resolve()
    output = output_dir.resolve()
    if not output.is_relative_to(root):
        raise ValueError("review output outside project")
    ids = [row["group_id"] for row in inputs]
    target_ids = [row["group_id"] for row in targets]
    if len(ids) != len(set(ids)) or len(target_ids) != len(set(target_ids)):
        raise ValueError("duplicate input or target group")
    input_by_id = dict(zip(ids, inputs, strict=True))
    target_by_id = dict(zip(target_ids, targets, strict=True))
    samples = sampling["samples"]
    sample_ids = [s["group_id"] for s in samples]
    coordinate_ids = sampling["coordinate_group_ids"]
    if len(sample_ids) != len(set(sample_ids)) or len(coordinate_ids) != len(set(coordinate_ids)):
        raise ValueError("duplicate audit group")
    if not set(coordinate_ids).issubset(sample_ids):
        raise ValueError("coordinate cases must belong to audit sample")
    for group_id in sample_ids:
        _safe_id(group_id)
        if group_id not in input_by_id or group_id not in target_by_id:
            raise ValueError(f"sample has no input/target: {group_id}")

    review = output / "review"
    review.mkdir(exist_ok=False)
    for name in ("images", "cases", "coordinates"):
        (review / name).mkdir()
    index_links: list[str] = []
    review_templates = []
    coordinate_set = set(coordinate_ids)
    for sample in samples:
        group_id = sample["group_id"]
        row, target = input_by_id[group_id], target_by_id[group_id]
        if not row["fragments"]:
            raise ValueError("review group has no fragments")
        fragments_html: list[str] = []
        tiles: list[Image.Image] = []
        for fragment in row["fragments"]:
            fragment_id = _safe_id(fragment["fragment_id"])
            source = _source(root, fragment["image_relpath"])
            if hashlib.sha256(source.read_bytes()).hexdigest() != fragment["image_sha256"]:
                raise ValueError(f"source hash mismatch: {fragment_id}")
            with Image.open(source) as original:
                image = original.convert("RGB")
            if list(image.size) != fragment["image_size"]:
                raise ValueError(f"source dimensions changed: {fragment_id}")
            box = fragment["crop_box"]
            if (
                len(box) != 4
                or any(type(v) is not int for v in box)
                or not (0 <= box[0] < box[2] <= image.width)
                or not (0 <= box[1] < box[3] <= image.height)
            ):
                raise ValueError(f"invalid crop box: {fragment_id}")
            crop = image.crop(tuple(box))
            crop_name = f"{fragment_id}-crop.png"
            _save_png(crop, review / "images" / crop_name)
            label = f"page {fragment['page_num']} / part {fragment['part_index']}"
            fragments_html.append(
                f"<section><h3>{html.escape(label)}</h3>"
                f'<a href="../images/{crop_name}"><img loading="lazy" '
                f'src="../images/{crop_name}" alt="{html.escape(label)}"></a>'
                f"<p>原图尺寸 {image.size}，crop_box {box}</p></section>"
            )
            if group_id in coordinate_set:
                overlay = image.copy()
                draw = ImageDraw.Draw(overlay)
                draw.rectangle(box, outline="red", width=max(3, image.width // 220))
                overlay.thumbnail((390, 340))
                small_crop = ImageOps.contain(crop, (390, 230))
                tile = Image.new("RGB", (410, 620), "#eeeeee")
                painter = ImageDraw.Draw(tile)
                painter.text((10, 5), label, fill="black")
                tile.paste(overlay, ((410 - overlay.width) // 2, 30))
                painter.text((10, 377), "CROP (no recognition)", fill="black")
                tile.paste(small_crop, ((410 - small_crop.width) // 2, 399))
                tiles.append(tile)

        coordinate_html = ""
        if tiles:
            columns = min(3, len(tiles))
            rows = (len(tiles) + columns - 1) // columns
            board = Image.new("RGB", (columns * 410, rows * 620 + 30), "white")
            ImageDraw.Draw(board).text((10, 8), group_id, fill="black")
            for number, tile in enumerate(tiles):
                board.paste(tile, ((number % columns) * 410, (number // columns) * 620 + 30))
            _save_png(board, review / "coordinates" / f"{group_id}.png")
            coordinate_html = (
                f'<p><a href="../coordinates/{group_id}.png">原页红框与裁剪坐标核验图</a></p>'
            )
        # Empty sandbox disables scripts/navigation; CSP also blocks all external resources.
        sandbox_content = (
            '<meta http-equiv="Content-Security-Policy" '
            "content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            "<style>table{border-collapse:collapse}td,th{border:1px solid #888;padding:5px}</style>"
            + target["html"]
        )
        body = (
            '<p><a href="../index.html">返回审计目录</a></p>'
            '<p class="notice">R0：真值提供片段框和同表分组。预测尚未生成；'
            "本页只供数据与坐标审计，不能当作模型效果。</p>"
            + coordinate_html
            + '<h2>原始片段图</h2><div class="grid">'
            + "".join(fragments_html)
            + "</div><h2>Ground Truth — 数据集整表目标</h2>"
            + f'<iframe sandbox="" srcdoc="{html.escape(sandbox_content, quote=True)}"></iframe>'
            + "<h2>审计状态</h2><p>pending，需填写独立审计记录。</p>"
        )
        _write_text(review / "cases" / f"{group_id}.html", _html_document(group_id, body))
        probability = sample.get("inclusion_probability")
        index_links.append(
            f'<li><a href="cases/{group_id}.html">{group_id}</a> '
            f"（抽样概率 {html.escape(str(probability))}）</li>"
        )
        review_templates.append(
            {
                "group_id": group_id,
                "coordinate_case": group_id in coordinate_set,
                "status": "pending",
                "reviewer": None,
                "coordinate_ok": None,
                "content_complete": None,
                "annotation_issue": None,
                "notes": "",
            }
        )
    _write_text(
        review / "index.html",
        _html_document(
            "跨页片段数据审计",
            '<p class="notice">暂定 train_fit 抽样。未完成泄漏校准、独立人审和模型预测，'
            "不能用于正式训练或报告模型分数。</p><ol>" + "".join(index_links) + "</ol>",
        ),
    )
    _write_text(
        output / "review-template.jsonl",
        "".join(json.dumps(v, ensure_ascii=False) + "\n" for v in review_templates),
    )
    return {
        "case_count": len(samples),
        "coordinate_case_count": len(coordinate_ids),
        "prediction_status": "not_generated",
        "review_status": "pending",
        "entrypoint": "review/index.html",
    }
