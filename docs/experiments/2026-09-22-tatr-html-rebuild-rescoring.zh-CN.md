# TATR HTML 序列化修复与全量重新评分记录

日期：2026-09-22

## 1. 结论摘要

TATR-v1.1-Pub 在 PubTables-v2 `Cropped Tables/val` 上原报告的 `Acc-Con=0.0069` 不是可信的模型能力结果。模型后处理保存的 cell 中有一部分是正确的，但项目的 `cells_to_html()` 将表头写成 `<thead><th>...</th></thead>`，缺少标准 `<tr>`。固定版本 GriTS 解析器只在 `<tr>` 处推进网格行，因而错误解释表头行号并扰乱行列和 span。

修复序列化并从原始 `raw_output.cells` 重建全部预测后，正式结果为：

| 指标 | 原错误 HTML 评分 | 修正 HTML 评分 |
| --- | ---: | ---: |
| GriTS-Top | 0.7429088739 | 0.8848063827 |
| GriTS-Con | 0.7167619958 | 0.8703867933 |
| Acc-Top | 0.0163628213 | 0.3897190675 |
| Acc-Con | 0.0068738793 | 0.3826957561 |

旧指标保留用于审计实现缺陷，不再作为 TATR-v1.1-Pub 的正式结果。

## 2. 问题发现与证据

24 张固定分层样本包含长表、宽表、同时长且宽的表，以及复杂 span/多层表头。实际预测 HTML 中可见：

```html
<table><thead><th>Country</th>...</thead><tr>...</tr></table>
```

正确层级应为：

```html
<table><thead><tr><th>Country</th>...</tr></thead><tbody>...</tbody></table>
```

只在内存中补齐 `<tr>` 后，同一批样本的结果由 `0/24` exact 变为 `9/24` exact，平均 `GriTS-Top` 从 `0.7838` 提升到 `0.9212`，平均 `GriTS-Con` 从 `0.7506` 提升到 `0.9047`。这证明分数异常不是单纯由模型预测误差造成。

## 3. 修复范围

- 修正 `src/cptla/evaluation/tatr.py` 中 `cells_to_html()` 的 `thead/tbody/tr/th/td` 层级。
- 新增 `src/cptla/evaluation/tatr_rebuild.py`，从已有预测的 `raw_output.cells` 重建 HTML。
- 新增 `scripts/rebuild_tatr_predictions.py`，流式写出轻量预测 JSONL，不复制约 1.2 GB 的原始 raw payload。
- 保持官方 GriTS 评分实现不变；没有重新定义指标。
- 没有重新运行 GPU 推理，也没有修改旧预测、旧指标或原始数据。

本地实现提交：`bc7be0d`。服务器应用提交：`8f3e453497389c70909ecb742fc4c7a566b578e6`。

## 4. 测试与小样本验收

采用测试驱动流程：

1. 先增加单层表头、多层表头、`rowspan/colspan`、正文层级和重建记录保持测试；
2. 修复前测试按预期失败；
3. 修复后本地相关 28 项测试通过，本地除缺失 GriTS 依赖模块外的测试套件通过；
4. 服务器固定 `PYTHONPATH=src:third_party/grits-main` 环境中，TATR、重建和评分相关 36 项测试通过；
5. Ruff 检查通过。

固定 24 样本重复评分结果完全一致：

| 指标 | 结果 |
| --- | ---: |
| coverage | 24/24 |
| invalid table HTML | 0 |
| GriTS-Top | 0.9095907242 |
| GriTS-Con | 0.8863298067 |
| Acc-Top | 0.375 |
| Acc-Con | 0.375 |

验收目录：

```text
outputs/baselines/tatr-v1.1-pub/20260922T094741Z-tatr-html-rebuild-smoke/
```

## 5. 全量重新评分

### 5.1 固定输入

- 原始推理 run：`20260921T082639Z-tatr-cropped-val-full`
- 原始 predictions SHA-256：`f8536fc30456a7b24440c9a391629182de4e8b60b4c37bc186507a3c6cdac379`
- validation manifest：`artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/tatr-cropped-val-full.jsonl`
- collection：`cropped_tables`
- 输入赛道：`PDF-text-assisted`
- 预期记录：13,384
- GPU：未使用

### 5.2 运行状态

- run ID：`20260922T095039Z-tatr-cropped-val-rebuilt-score`
- 开始：`2026-09-22T09:51:49Z`
- 完成：`2026-09-22T11:08:29Z`
- 退出码：0
- 重建耗时：31.90 秒
- 全量评分耗时：4561.11 秒
- coverage：13,384/13,384
- missing / extra / duplicate：0 / 0 / 0
- inference errors：65
- predicted tables：13,317
- invalid table HTML：0

### 5.3 正式指标

| 指标 | 结果 |
| --- | ---: |
| GriTS-Top | 0.8848063827 |
| GriTS-Con | 0.8703867933 |
| Acc-Top | 0.3897190675 |
| Acc-Con | 0.3826957561 |
| Topology precision | 0.8406092444 |
| Topology recall | 0.9339089889 |
| Topology cell exact accuracy | 0.9065820148 |
| Content precision | 0.8269099308 |
| Content recall | 0.9186891800 |
| Content cell exact accuracy | 0.8997900978 |

### 5.4 产物与校验

```text
outputs/baselines/tatr-v1.1-pub/20260922T095039Z-tatr-cropped-val-rebuilt-score/
├── predictions.jsonl
├── metrics.json
├── failures.jsonl
├── checksums.sha256
├── run-metadata.json
├── git-commit.txt
└── COMPLETE

logs/baselines/tatr-v1.1-pub/20260922T095039Z-tatr-cropped-val-rebuilt-score/
├── run.sh
├── runner.pid
├── started-at.txt
├── finished-at.txt
├── exit-code.txt
├── rebuild.log
└── score.log
```

校验和：

- rebuilt predictions：`f762d8017637f4f77e43a7f8f54edeb07630df7186fc1e6513e13577a9e83f2f`
- metrics：`b089d5fd59f4445d41b2348cfccdd5510826a6c73df1e31e8e47c873338b58d0`
- failures：`8db22441ba3f0d7d088931ceb3270b010c3a2e160ee93b330c12bd07b05f15a7`

`sha256sum -c` 对上述文件全部返回 `OK`。

## 6. 科研解释与边界

### 已观察事实

1. 序列化缺陷使旧 `Acc-Con` 被严重低估；修复后提高约 37.58 个百分点。
2. 修正后的 `Acc-Top` 与 `Acc-Con` 仅相差约 0.70 个百分点。在 PDF Direct Text 条件下，额外的内容错误不是 strict exact failure 的首要来源。
3. topology 和 content 的 recall 均高于 precision，说明模型覆盖多数真实结构的同时，仍存在额外或错误结构。
4. 65 个推理失败占约 0.49%，已经作为空预测计入，不能解释其余大多数非 exact 样本。

### 合理推断，仍需分层误差分析验证

- 剩余主要瓶颈更可能集中于额外行列、列过分割、复杂表头和 `rowspan/colspan`。
- 同时长且宽、并含复杂 span 的表可能比单纯长表或宽表更困难。
- 约束化结构修复比继续优化 PDF 文字识别更值得优先验证。

### 尚不能声称

- 不能把 Cropped Tables 的结果写成跨页表格恢复结果。
- 不能声称 TATR-v1.1 已达到 TATR-v1.2 的论文结果。
- 不能根据24张样本直接断言某一种结构错误是全量数据的唯一主因。

## 7. 下一步

1. 从修正后的失败样本中分层抽取 60–80 张，建立可复核错误分类。
2. 做 oracle 行数、列数、表头、span 和文字归属消融。
3. 优先验证列合并、表头层级和 span 一致性约束。
4. 将单页结构修复结果作为后续 continuation、跨页列对应、重复表头和拆分行重建的上游输入。
