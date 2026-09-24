# ruff: noqa: E501
from __future__ import annotations

import html
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Literal

from grits import html_to_cell_list

from cptla.evaluation.case_analysis import CaseDiagnostic
from cptla.evaluation.contracts import PredictionRecord


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _cell_map(table_html: str):
    cells = html_to_cell_list(table_html)
    if cells is None:
        raise ValueError("table HTML could not be parsed")
    return {(min(cell.row_nums), min(cell.column_nums)): cell for cell in cells}


def _cell_class(cell, counterpart) -> str:
    if counterpart is None:
        return "cell-one-sided"
    if (
        cell.row_nums != counterpart.row_nums
        or cell.column_nums != counterpart.column_nums
        or cell.is_column_header != counterpart.is_column_header
    ):
        return "cell-structure-diff"
    if _normalize_text(cell.cell_text) != _normalize_text(counterpart.cell_text):
        return "cell-text-diff"
    return "cell-match"


def render_comparison_table(
    table_html: str,
    counterpart_html: str | None,
    *,
    side: Literal["truth", "prediction"],
) -> str:
    cells = _cell_map(table_html)
    counterpart = _cell_map(counterpart_html) if counterpart_html else {}
    if not cells:
        return '<p class="empty-table">空表</p>'
    row_count = max(max(cell.row_nums) for cell in cells.values()) + 1
    column_count = max(max(cell.column_nums) for cell in cells.values()) + 1
    occupied = {
        (row, column)
        for cell in cells.values()
        for row in cell.row_nums
        for column in cell.column_nums
    }
    rows: list[str] = []
    for row in range(row_count):
        rendered_cells: list[str] = []
        for column in range(column_count):
            cell = cells.get((row, column))
            if cell is None:
                if (row, column) not in occupied:
                    rendered_cells.append('<td class="cell-gap"></td>')
                continue
            tag = "th" if cell.is_column_header else "td"
            attributes = [f'class="{_cell_class(cell, counterpart.get((row, column)))}"']
            if len(cell.row_nums) > 1:
                attributes.append(f'rowspan="{len(cell.row_nums)}"')
            if len(cell.column_nums) > 1:
                attributes.append(f'colspan="{len(cell.column_nums)}"')
            rendered_cells.append(
                f"<{tag} {' '.join(attributes)}>{html.escape(cell.cell_text)}</{tag}>"
            )
        rows.append(f"<tr>{''.join(rendered_cells)}</tr>")
    return f'<table class="comparison-table {side}"><tbody>{"".join(rows)}</tbody></table>'


def _tag_list(values: list[str]) -> str:
    if not values:
        return '<span class="tag muted">none</span>'
    return "".join(f'<span class="tag">{html.escape(value)}</span>' for value in values)


def _profile_text(case: CaseDiagnostic) -> str:
    truth = case.truth_profile
    prediction = case.prediction_profile
    predicted = (
        "无"
        if prediction is None
        else f"{prediction.row_count}×{prediction.column_count} / {prediction.cell_count} cells"
    )
    return (
        f"GT {truth.row_count}×{truth.column_count} / {truth.cell_count} cells；"
        f"Prediction {predicted}"
    )


def _case_card(
    case: CaseDiagnostic,
    record: PredictionRecord,
    truth_html: str,
    image_name: str,
) -> str:
    predicted_html = record.tables_html[0] if record.status == "ok" and record.tables_html else None
    truth_table = render_comparison_table(truth_html, predicted_html, side="truth")
    prediction_table = (
        render_comparison_table(predicted_html, truth_html, side="prediction")
        if predicted_html
        else '<p class="empty-table">没有可渲染的预测表格</p>'
    )
    raw_prediction = predicted_html or record.error or ""
    return f"""
<article class="case-card" id="case-{html.escape(case.unit_id)}"
  data-score-stratum="{case.score_stratum}"
  data-error-tags="{' '.join(case.error_tags)}"
  data-complexity-tags="{' '.join(case.complexity_tags)}"
  data-search="{html.escape(case.unit_id.lower())}">
  <header>
    <div><h2>{html.escape(case.unit_id)}</h2><p>{html.escape(_profile_text(case))}</p></div>
    <div class="scores"><b>GriTS-Top {case.grits_top:.4f}</b><b>GriTS-Con {case.grits_con:.4f}</b></div>
  </header>
  <div class="tags">{_tag_list([case.score_stratum] + case.error_tags + case.complexity_tags)}</div>
  <div class="views">
    <section data-view="source-image"><h3>原始裁剪图</h3>
      <button class="image-button" type="button" data-image="assets/images/{html.escape(image_name)}">
        <img loading="lazy" src="assets/images/{html.escape(image_name)}" alt="{html.escape(case.unit_id)} 原图">
      </button>
    </section>
    <section data-view="ground-truth"><h3>Ground Truth</h3><div class="table-scroll">{truth_table}</div></section>
    <section data-view="prediction"><h3>Prediction</h3><div class="table-scroll">{prediction_table}</div></section>
  </div>
  <details><summary>查看原始 HTML / 错误信息</summary>
    <h4>Ground Truth</h4><pre>{html.escape(truth_html)}</pre>
    <h4>Prediction</h4><pre>{html.escape(raw_prediction)}</pre>
  </details>
</article>"""


def _select(name: str, label: str, values: list[str]) -> str:
    options = '<option value="">全部</option>' + "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in values
    )
    return f'<label>{label}<select id="{name}">{options}</select></label>'


def _counter_rows(title: str, counter: Counter[str]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(key)}</td><td>{value}</td></tr>"
        for key, value in sorted(counter.items())
    )
    return f"<section><h3>{title}</h3><table><tbody>{rows}</tbody></table></section>"


def _report_html(
    all_cases: list[CaseDiagnostic],
    selected_cases: list[CaseDiagnostic],
    cards: list[str],
    metadata: dict[str, object],
) -> str:
    strata = Counter(case.score_stratum for case in all_cases)
    errors = Counter(tag for case in all_cases for tag in case.error_tags)
    complexities = Counter(tag for case in all_cases for tag in case.complexity_tags)
    error_values = sorted(errors)
    complexity_values = sorted(complexities)
    filters = "".join(
        [
            _select("score-filter", "分数层", sorted(strata)),
            _select("error-filter", "错误线索", error_values),
            _select("complexity-filter", "复杂度", complexity_values),
        ]
    )
    metadata_json = html.escape(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>表格恢复案例分析</title>
<style>
:root{{--bg:#f4f6f8;--card:#fff;--ink:#1d2733;--line:#cbd5df;--accent:#2457d6}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,"Microsoft YaHei",sans-serif}}
main{{max-width:1800px;margin:auto;padding:24px}} h1,h2,h3{{margin:.2em 0}} .notice{{background:#fff7d6;border-left:5px solid #e2a600;padding:12px 16px}}
.metadata{{font-size:.82rem;word-break:break-all;color:#596675}} .summary{{display:flex;gap:16px;flex-wrap:wrap;margin:18px 0}}
.summary section{{background:var(--card);padding:12px 18px;border-radius:10px;box-shadow:0 1px 4px #0001}}
.summary table td{{padding:2px 10px}} .filters{{position:sticky;top:0;z-index:3;background:#eef2f6;padding:12px;display:flex;gap:14px;flex-wrap:wrap}}
.filters label{{display:grid;gap:4px;font-size:.84rem}} input,select{{min-width:180px;padding:7px;border:1px solid var(--line);border-radius:6px;background:white}}
.case-card{{background:var(--card);margin:18px 0;padding:18px;border-radius:12px;box-shadow:0 2px 8px #0002}}
.case-card>header{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}} .scores{{display:flex;gap:12px;flex-wrap:wrap}}
.tags{{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}} .tag{{background:#e8eefc;border-radius:999px;padding:3px 8px;font-size:.76rem}} .muted{{color:#687481}}
.views{{display:grid;grid-template-columns:minmax(280px,1fr) minmax(360px,1fr) minmax(360px,1fr);gap:14px}}
.views section{{min-width:0;border:1px solid var(--line);border-radius:8px;padding:10px}} .image-button{{border:0;background:none;padding:0;cursor:zoom-in;width:100%}}
.image-button img{{display:block;max-width:100%;max-height:72vh;margin:auto}} .table-scroll{{overflow:auto;max-height:72vh}}
.comparison-table{{border-collapse:collapse;font-size:.78rem;min-width:max-content}} .comparison-table td,.comparison-table th{{border:1px solid #8996a3;padding:4px 7px;max-width:280px}}
.cell-match{{background:#e5f6e8}} .cell-text-diff{{background:#fff3ad}} .cell-structure-diff{{background:#ffc9c9}} .cell-one-sided,.cell-gap{{background:#eadde1}}
pre{{white-space:pre-wrap;word-break:break-all;background:#f5f7f9;padding:10px;max-height:280px;overflow:auto}} dialog{{max-width:95vw;max-height:95vh;border:0;border-radius:10px}}
dialog img{{max-width:90vw;max-height:86vh}} @media(max-width:1100px){{.views{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>表格恢复案例分析</h1>
<p class="notice"><b>解释边界：</b>自动标签只是诊断线索，坐标偏移可能产生级联差异，不能替代人工核验。本报告是 Cropped Tables 页内单表结果，不代表跨页恢复能力。</p>
<p>全量诊断 {len(all_cases):,} 例；分层展示 {len(selected_cases):,} 例。</p>
<p class="metadata">运行元数据：{metadata_json}</p>
<div class="summary">{_counter_rows("分数层", strata)}{_counter_rows("错误线索", errors)}{_counter_rows("复杂度", complexities)}</div>
<div class="filters">{filters}<label>案例 ID<input id="search-filter" type="search" placeholder="输入 image/unit ID"></label><span id="visible-count"></span></div>
<div id="case-list">{"".join(cards)}</div>
<dialog id="image-dialog"><form method="dialog"><button>关闭</button></form><img alt="放大原图"></dialog>
</main><script>
const cards=[...document.querySelectorAll('.case-card')];
const score=document.querySelector('#score-filter'),error=document.querySelector('#error-filter'),complexity=document.querySelector('#complexity-filter'),search=document.querySelector('#search-filter'),count=document.querySelector('#visible-count');
function applyFilters(){{let visible=0;for(const card of cards){{const ok=(!score.value||card.dataset.scoreStratum===score.value)&&(!error.value||card.dataset.errorTags.split(' ').includes(error.value))&&(!complexity.value||card.dataset.complexityTags.split(' ').includes(complexity.value))&&(!search.value||card.dataset.search.includes(search.value.toLowerCase()));card.hidden=!ok;if(ok)visible++;}}count.textContent=`显示 ${{visible}} / ${{cards.length}}`;}}
[score,error,complexity,search].forEach(node=>node.addEventListener('input',applyFilters));applyFilters();
const dialog=document.querySelector('#image-dialog');document.querySelectorAll('.image-button').forEach(button=>button.addEventListener('click',()=>{{dialog.querySelector('img').src=button.dataset.image;dialog.showModal();}}));
</script></body></html>"""


def write_case_report(
    output_dir: Path,
    *,
    all_cases: list[CaseDiagnostic],
    selected_cases: list[CaseDiagnostic],
    records_by_id: dict[str, PredictionRecord],
    truth_by_id: dict[str, str],
    images_dir: Path,
    metadata: dict[str, object],
) -> Path:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    selected_ids = [case.unit_id for case in selected_cases]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected cases contain duplicate unit IDs")
    missing_records = sorted(set(selected_ids) - records_by_id.keys())
    missing_truth = sorted(set(selected_ids) - truth_by_id.keys())
    if missing_records or missing_truth:
        raise ValueError(
            f"missing report inputs: predictions={missing_records}, truth={missing_truth}"
        )
    image_paths = {case.unit_id: images_dir / case.relative_path for case in selected_cases}
    missing_images = sorted(str(path) for path in image_paths.values() if not path.is_file())
    if missing_images:
        raise FileNotFoundError(f"missing report images: {missing_images[:3]}")

    images_output = output_dir / "assets" / "images"
    images_output.mkdir(parents=True)
    cards: list[str] = []
    for case in selected_cases:
        destination = images_output / case.image_id
        shutil.copy2(image_paths[case.unit_id], destination)
        cards.append(
            _case_card(
                case,
                records_by_id[case.unit_id],
                truth_by_id[case.unit_id],
                destination.name,
            )
        )

    payload = {
        "metadata": metadata,
        "selected_ids": selected_ids,
        "cases": [
            {**case.model_dump(mode="json"), "selected": case.unit_id in set(selected_ids)}
            for case in all_cases
        ],
    }
    (output_dir / "cases.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    index = output_dir / "index.html"
    index.write_text(
        _report_html(all_cases, selected_cases, cards, metadata),
        encoding="utf-8",
    )
    return index
