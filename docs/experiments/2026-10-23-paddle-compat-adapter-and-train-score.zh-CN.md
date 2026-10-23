# Paddle 三组后处理适配与 train 配对评分

日期：2026-10-23（Asia/Shanghai，日志时间 UTC）。状态：服务器来源页适配完成，评分待执行。用户已确认保留原版并单列字段兼容版；实施计划 `docs/2026-10-23-paddle-compat-adapter-implementation-plan.zh-CN.md`。

研究问题：修正已核验的 Continued 字段契约后，能否保持来源页可审计，并让同一组页面预测进入评分。仅验证流程与这两个 train 案例，不用结果宣称全量性能。

数据/模型沿用 smoke：PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，train 文档 PMC10235804、PMC10311686，共6页；image-only，不使用GT筛页或裁图；GPU预测 seed=0。PaddleOCR-VL-1.5 revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，PP-DocLayoutV3 revision `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`。本轮 CPU 后处理无随机算法、无GPU和训练、未下载数据/权重，原输入不变。

## 可验收阶段：适配完成

代码 commit `9e6c5fa`，本地和服务器 `codex/paddle-merge-compat` 分支；服务器没有改 main 或安装的 PaddleX 源码。新增 `src/cptla/evaluation/paddle_document.py` 和 `scripts/adapt_paddle_document_predictions.py`。原始预测路径 `outputs/baselines/paddleocr-vl-1.5/20261023T082900Z-paddle-train-smoke/`，输入 `artifacts/paddle-smoke/20261023T081900Z-train-inputs/`。

本地 26 测试通过、6 个真实官方函数集成测试因未提供服务器源码而跳过；服务器提供固定 SHA 的真实官方函数后，相关单元/集成/现有 cross_page/scoring **60 测试全部通过**。覆盖原版回放、续表正例、无关标题/正文负例、宽度拒绝、三页链、空尾来源页、缺页/重复/悬空引用和非表根拒绝。合成负例不是对完整数据误连率的估计。

服务器初次回归发现缺少 vendored grits 的 PYTHONPATH；补齐后确认 eval312 不含 bs4。未混装或修改旧环境：只在新 `artifacts/runtime-deps/20261023T100100Z-paddle-cpu/` 安装 beautifulsoup4==4.15.0、soupsieve==3.0.4（与 Paddle 环境同版），pip report/cache/TMP 位于 `logs/paddle-cpu-setup/20261023T100100Z/`。正式命令环境 `PYTHONPATH=src:third_party/grits-main:artifacts/runtime-deps/20261023T100100Z-paddle-cpu`，解释器 `.venvs/eval312/bin/python`。

CPU适配命令：

```bash
export PYTHONPATH=src:third_party/grits-main:artifacts/runtime-deps/20261023T100100Z-paddle-cpu
export PADDLE_MERGE_SOURCE=.venvs/paddle-v15-20261023T081029Z-paddle-v15/lib/python3.12/site-packages/paddlex/inference/pipelines/layout_parsing/merge_table.py
.venvs/eval312/bin/python scripts/adapt_paddle_document_predictions.py \
  --inputs artifacts/paddle-smoke/20261023T081900Z-train-inputs \
  --predictions outputs/baselines/paddleocr-vl-1.5/20261023T082900Z-paddle-train-smoke \
  --official-merge-source "$PADDLE_MERGE_SOURCE" \
  --output-dir artifacts/paddle-smoke/20261023T100500Z-three-condition-adapter
```

输出 `summary.json` 证实：6/6页、missing/extra/duplicate=0、`official_replay=identical`。无合并与官方原版均4个页面表、0个多页来源组；兼容版2个逻辑表候选、均保留[1,2]来源页。**候选合并成功不等于结构严格正确。**适配不清洗HTML；空尾仍保留来源证据。page-results 的 elapsed=0 仅是 schema 要求的未知占位并有 warning，不能报告为零耗时。

summary 记录每个输入和输出 SHA；原输入在适配前后核对不变。document-tables.jsonl 的 no_merge/official SHA `20fe76ca3c33ccf1a262968bb9a223c38fbfecd83400039dee8605ad7b42672c`，compat SHA `59eff469e1c1fa7fb91b9c5ace3874cf9ca8bd7aec7a7c547da53f75c0c71ebf`。所有正式指标、GT匹配与误连结论仍待评分，尚未启动 val 全量。

## 10:02 UTC（北京时间18:02）train三组评分完成

上段“待评分”保留为历史检查点。CPU任务 10:02:33–10:02:38 UTC 三组均 exit 0，运行状态 `completed`。评分新目录 `artifacts/paddle-smoke/20261023T100300Z-three-condition-train-scores/`，`run-summary.json` 保存完整命令、起止、commit、train truth 文件 SHA。任务已结束，没有后台GPU或评分任务继续运行。

评分前在内存读取两份 train `<doc>_tables.json`，遍历全部逻辑表，按 `sorted({p['page_num'] for p in table['parts']})` 筛选两页以上者；逐项生成 `document_id`、`table_index`、`table_id=f'{doc}-table-{index}'`、`source_split='train'`、`page_numbers`、原 `html`、`label_origin='derived_from_logical_table_parts'`，写到新目录 `gold-cross-page.jsonl`。两份文档各1张跨页真值，总计2；这是从官方逻辑表 parts 派生的子集，不是新增官方细粒度监督。GT仅用于评分，未提供给合并器/adapter。truth 输入前后SHA不变。

每组完整命令形如（`MODE` 依次取表中三个条件，变量只表示命令重复，不重新调参）：

```bash
PYTHONPATH=src:third_party/grits-main:artifacts/runtime-deps/20261023T100100Z-paddle-cpu \
.venvs/eval312/bin/python scripts/score_cross_page_predictions.py \
  --manifest artifacts/paddle-smoke/20261023T100500Z-three-condition-adapter/input-manifest.jsonl \
  --page-results artifacts/paddle-smoke/20261023T100500Z-three-condition-adapter/MODE/page-results.jsonl \
  --document-tables artifacts/paddle-smoke/20261023T100500Z-three-condition-adapter/MODE/document-tables.jsonl \
  --truth-dir 'data/pubtables-v2/extracted/Full Documents/train/tables' \
  --cross-page-gold artifacts/paddle-smoke/20261023T100300Z-three-condition-train-scores/gold-cross-page.jsonl \
  --output-dir artifacts/paddle-smoke/20261023T100300Z-three-condition-train-scores/MODE \
  --partial
```

此处 `scope=partial`，明确不是 full_validation。全表及跨页指标仍沿用既有 GriTS/内容网格 exact 定义；cross_page 是 GT子集诊断，不是检测precision，Top沿用Con匹配，内容网格exact本身不校验来源页（因此另读 matches）。两篇文档所有真值都跨页，但不意味着 cross_page/full_document 聚合在未合并组相同。

| 条件 MODE | 页表/逻辑候选数 | 全表 GriTS-Con | 跨页子集 GriTS-Con | 结构网格 exact | 内容网格 exact | 匹配的来源页完整数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_merge | 4 | 0.6438514128 | 0.7888948629 | 0/2 | 0/2 | 0/2 |
| native_merge_official | 4 | 0.6438514128 | 0.7888948629 | 0/2 | 0/2 | 0/2 |
| native_merge_content_compat | 2 | 0.9891834779 | 0.9891834779 | 2/2 | 0/2 | 2/2 |

三组6/6页覆盖均完整，无重复/缺失/额外页，inference_error_pages=0、invalid_table_html=0、failures.jsonl为空。compat 两个 `matches.jsonl` 的 `source_pages=[1,2]` 与 `truth_pages=[1,2]` 相同；原版均仅匹配到[1]，还有2个未匹配页表。compat GriTS-Top=1.0、内容单元格 exact=0.9318181818，但严格内容整网格 exact 仍0，内容差异的文字/格式来源尚未逐格分类。

**结论边界：**这两个有意选择的 train 正例只证明修复了确定的字段兼容问题、来源页和评分链路可用；不能宣称模型全量达到0.989，也不能声称真实负例误连率通过或形成论文算法贡献。全量val可恢复入口、更多train整文档正负例稳定性审计仍是下一阶段，当前不自动启动全量或改变官方baseline。

完成后再次核验 adapter 的全部 input_hashes/output_hashes 均一致。评分证据SHA：

- no_merge/official `metrics.json`：`fcca409f918efa6367dd87ec1ad5a81cc88e0e010771880c1a64e988b6a2665b`；两组完全相同。
- compat `metrics.json`：`e44ca5a58ebf686eb82308fccd96e88eaf351614ef0d51d618affa36c9510796`。
- compat `matches.jsonl`：`98c8816d7884bc3c11c03c7b43a58effcc24dac2fece8d9c07fa506710141fb8`。
- `run-summary.json`：`f09e40855715f56d71d5c691e15eade6086f8c0676b9c769bca795473fcfc8d1`。

## 新增要求与负例任务启动

用户要求持续推进到全量可启动。服务器追加CLI端到端/原版回放异常测试后，共62相关测试通过。独立只读代码审查无Critical/Important；未合并main，分支仍为codex/paddle-merge-compat。

只在train筛选完整2–4页文档，官方label=0的页面两侧均有表片段且逻辑表ID不重叠，选得PMC11626747（4页，负对[1,2]，positive_pair_count=0）。原选择脚本逐文档glob效率较低；另一次单次枚举images+Counter核验得到同一可用范围，未读val/test选案例。选择不是随机样本，不声称覆盖真实负例分布。

新输入 `artifacts/paddle-smoke/20261023T101200Z-negative-inputs/`，用原pack脚本全4页、空文字层及嵌入原JPEG审核。GPU0启动前空余39,607MiB且已有4进程，未终止任何已有GPU进程。`paper-paddle-negative-20261023T101200Z.service`初始PID1156473、active/running；入口与主模型/版面模型/环境/默认生成参数与原smoke相同，只换上述输入与run ID `20261023T101200Z-paddle-train-smoke`。输出/日志沿用标准时间戳目录，launcher `logs/paddle-launchers/20261023T101200Z/smoke.log`；命令为 `.venvs/paddle-v15-20261023T081029Z-paddle-v15/bin/python -u scripts/run_paddle_v15_smoke.py --inputs artifacts/paddle-smoke/20261023T101200Z-negative-inputs --vl-model models/20261023T064109Z-public-models/paddleocr-vl-1.5 --layout-model models/20261023T081029Z-paddle-layout/pp-doclayoutv3 --gpu 0 --run-id 20261023T101200Z-paddle-train-smoke`。完成与误连结果待核验。

### 负例完成核验

10:10:29–10:12:25 UTC，4页116.54秒，completed、unit inactive/dead、exit0；6个非空页面表。CPU adapter复用同入口，新输出 `artifacts/paddle-smoke/20261023T101400Z-negative-adapter/`，4/4页、missing/extra/duplicate=0、official_replay=identical；no_merge/official/content_compat全部6个表、0个跨页来源组。因此在选定官方负对[1,2]上没有错误合并，但只1个文档，不报告总体误连率。

原预测 `pages.jsonl` SHA `a11043b19e5eba33f7795456d0370ba2f93fb6ad6018733caaf90f8a8abd3475`；推理summary SHA `d2e94790d35f9fd8227a72787335395285f9ab1c7a31f834fceb2a6f6fe228ce`；三组document-tables SHA均为 `bcdaabce1a03135dac7b3ebf31628d6fc929fa01a7926c8ce2c03ac7c5c6040e`。已结束无GPU任务继续运行。另已确认并终止本轮低效只读选择脚本（自身PID1140572，命令与启动时间核对），未终止任何模型/其他用户进程，未删除任何文件；替代单次枚举选择已得到结果。
