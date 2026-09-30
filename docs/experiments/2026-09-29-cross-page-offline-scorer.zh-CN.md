# 文档级跨页表离线评分器：实现与协议核验

日期：2026-09-29（UTC，核验截至 09:44:54 UTC）；状态：**评分器及单元测试已完成；四模型适配与正式评测未开始**。

## 范围与依据

- 研究问题：在不按真值筛选预测表的情况下，先对一篇文档内全部逻辑表做一对一匹配，再对跨不同页的真值表子集统计重建质量。
- 数据：PubTables-v2 Full Documents，固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；合成单元测试，以及 validation 单文档 `PMC12274235` 的**空预测协议核验**。没有读取 test 标签、模型预测或新下载数据。
- 输入：全页 manifest、每页终态（仅用于覆盖/失败统计）、文档级预测表 HTML 与来源页、原始文档真值和阶段 0 派生的跨页真值清单。固定审计清单见 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/`；页清单 SHA-256 为 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。
- 实现：`src/cptla/evaluation/cross_page.py`，CLI `scripts/score_cross_page_predictions.py`，测试 `tests/evaluation/test_cross_page.py`。基础代码 commit `e6154932b8efe43c98cee6e02f18ea017969aa41`；本轮修改未提交。三文件 SHA-256 依次为 `19e96672ab6a2b4776a95e285d05315171734f85a3f5fddc39ffdab0b7f968ff`、`d2f5a757ae617ee61951d8b2d726ed89f5419ba4085c842e8ffde18f829e7844`、`8b033fed31d278c6306f41456e8895bcb55fe2994fca2ba3fef4271cd6fc508a`。

## 固定评分口径

1. 要求 manifest 图片 ID 与逐页终态一一对应，包括无表页；`error` 页仍计覆盖，但单独计错误。最终表格只能放入文档级表清单，逐页终态的 `tables_html` 必须为空，避免重复计表。模型不得读取真值字段。
2. 校验文档预测表的唯一 `(document_id,table_id)`、可解析 HTML、非空且不重复的真实来源页；非法 HTML 单独列入 `failures.jsonl` 并作为漏表处理。跨页 GT 清单必须与原始 `parts.page_num` 推导出的全部跨页表一致；同页多片段不计跨页。
3. 每文档对**全部**真值和合法预测表，以 vendored 官方 GriTS 的内容网格 `hungarian_grits_con_matching` 一对一匹配；零内容相似度不算命中。只对已经匹配至跨页 GT 的预测表计 cross-page GriTS-Top/Con，未匹配的跨页 GT 计漏表。全表对照另外用 `GritsEvaluator.eval_htmls` 报告。跨页子集 GriTS 的预测单元格分母**不包括**未匹配到该子集的预测表，不能将其 precision 当成检测 precision。
4. 分开计来源页多于/少于跨页真值的匹配表、未匹配的预测表/多来源表、非法 HTML 和失败页。额外来源页只是**诊断线索**，不能仅凭来源页自动认定发生语义误合并；同页内不同表格的误合并目前无法可靠细分。非相邻片段保持真实页集合，不捏造中间页续接。

## 实际核验

环境：项目 `.venvs/eval312`，Python 3.12.7、pytest 8.4.2，`PYTHONPATH=src:third_party/grits-main`；CPU，GPU **未使用**。随机种子：不适用（确定性评分）。模型/权重 revision 与输入赛道：不适用（无推理）；正式运行时由四模型记录独立标记 `image-only` 或 `PDF-text-assisted`。没有新增模型输出或训练日志。

```bash
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -p no:cacheprovider --basetemp=artifacts/test-runs/20260929-cross-page-scorer-full-01 -q
.venvs/eval312/bin/ruff check src/cptla/evaluation/cross_page.py scripts/score_cross_page_predictions.py tests/evaluation/test_cross_page.py
.venvs/eval312/bin/ruff format --check src/cptla/evaluation/cross_page.py scripts/score_cross_page_predictions.py tests/evaluation/test_cross_page.py
git diff --check
```

结果：**129 passed**；Ruff check、format 和 diff check 通过。测试覆盖多表竞争、仅同页多片段、漏表、错误合并/拆分、来源页异常、非法 HTML、缺页、重复评分字节一致、输出目录不可覆盖及非相邻真值案例。测试临时目录为 `artifacts/test-runs/20260929-cross-page-scorer-full-01/`；未单独保存 stdout 日志。

另对 `PMC12274235` 用内存构造 16 条空结果页记录，以**空文档表预测**调用 `score_cross_page`（没有模型推理，也不将这次空预测的零分当性能指标）：原始真值 4 张，跨页 GT 清单 2 张，输出跨页 2/2 条，漏表 2 条、页覆盖完整、failure 0；其中 `PMC12274235-table-1` 来源真值页 `[4,5,7]`，未伪造 page 6。完整执行命令如下：

```bash
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -c 'import json; from pathlib import Path; from cptla.evaluation.pubtables_v2 import ImageManifestEntry; from cptla.evaluation.contracts import PredictionRecord; from cptla.evaluation.cross_page import score_cross_page; doc="PMC12274235"; root=Path("artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit"); m=[ImageManifestEntry.model_validate_json(line) for line in Path("artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl").open() if f"{doc}_page_" in line]; truth={doc:json.loads((Path("data/pubtables-v2/extracted/Full Documents/val/tables")/f"{doc}_tables.json").read_text())}; gold=[json.loads(line) for line in (root/"gold-cross-page.jsonl").open() if f"\"document_id\": \"{doc}\"" in line]; statuses=[PredictionRecord(image_id=e.image_id,unit_id=doc,status="ok",tables_html=[],elapsed_sec=0) for e in m]; metrics,matches,failures=score_cross_page(m,statuses,[],truth,gold); print(json.dumps({"check":"empty-input protocol only, no model inference", "document":doc,"pages":len(m),"truth_tables":len(truth[doc]),"cross_page_truth":len(gold),"scored_cross_page":metrics["cross_page_truth_tables"],"matched":metrics["cross_page_matched_tables"],"coverage":metrics["coverage"]["is_complete"],"nonadjacent_pages":[r["truth_pages"] for r in matches if r["truth_table_id"]==f"{doc}-table-1"],"failures":len(failures)},sort_keys=True))'
```

输出为 `{"coverage":true,"cross_page_truth":2,"document":"PMC12274235","failures":0,"matched":0,"nonadjacent_pages":[[4,5,7]],"pages":16,"scored_cross_page":2,"truth_tables":4}`（另有说明字段 `check`）。**该单文档真值筛选只用于评分器协议核验，不是模型输入/正式评测。**

CLI 形态：`--manifest ... --page-results ... --document-tables ... --truth-dir ... --cross-page-gold ... --output-dir NEW_DIR`；生成 `metrics.json`、`matches.jsonl`、`failures.jsonl`，已存在的输出目录会拒绝写入。正式全量运行需另存 prediction/model/环境/revision/哈希及运行日志，并由四模型 adapter 产生有来源页的文档级输出。

## 边界与下一步

**已提供**：固定原始真值、来源页派生、官方 GriTS 实现、单元与单文档核验输出。**推断/项目协议**：跨页子集、零重叠不认匹配、来源页诊断和匹配后的 micro GriTS。**待核验**：四模型是否能提供完整文档表 HTML 与可靠来源页；续接 P/R/F1、TEDS、语义层面误合并分层、模型真实预测与完整 val 离线复评。这些尚未实现，不报告为完成的评测阶段。

下一步先审查四模型官方接口、许可证及权重版本，设计 adapter 的统一预测 JSONL schema；等它们在 CPU mock 和真实小文档 smoke 里产出可审计来源页，再决定下载和 GPU 门禁。任何 GPU 工作前重新检查显存/进程。
