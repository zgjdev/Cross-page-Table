# dots.ocr 文档表无合并适配器与真实三页 smoke 复评

日期与时区：2026-09-29 UTC，复核至 10:02:16 UTC。状态：**适配器及 CPU 小范围链路验收完成**；不是完整 validation 或四模型横向结果。

## 问题、版本和范围

- 研究问题：把已经保存的 dots.ocr 逐页输出转换为评分器要求的“每页终态 + 文档级表格 HTML + 可审计来源页”，先以 **`no_merge`** 对照核验真实输出能否离线评分；不使用真值决定模型输入或合并规则。
- 数据：`kensho/PubTables-v2` Full Documents/val revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；旧 smoke `PMC11977379` 的**完整 3 页**，其中第 0 页无表，第 1 页输出 1 张表，第 2 页未输出表。输入清单 SHA-256 `c4d22178526b59384a487bf0274e64c86b6d04312bb0c9fc4476dad7d6afb006`；原始保存预测 SHA-256 `8f3fc49e1eda6950512d28195fd6e73743dddbeb914e8ec4c4d68ce709a9d597`。
- 模型 `dots.ocr`、权重 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，输入赛道 **`image-only`**；原 GPU 推理的运行清单在 `artifacts/run-manifests/20260921T081448Z-dots-full-documents-smoke.json`（SHA-256 `81d139de544d65214906f1317aeeff1f6aa266bf424b2a0b30a39e1a68c288f3`），其环境/命令/原推理证据见 `docs/experiments/2026-09-21-two-baseline-smoke.zh-CN.md`。**本轮仅 CPU 转换和复评，没有 GPU、下载或训练。**
- 当前基础 commit `e6154932b8efe43c98cee6e02f18ea017969aa41`；本轮文件未提交。代码：`src/cptla/evaluation/dotsocr_document.py` SHA-256 `9694a42a5a48427b087991a114d84c6911513b872657c566097eeccc5aa15e5a`；`scripts/adapt_dotsocr_document_predictions.py` SHA-256 `0c03c31be4443669e6e9b44b459173b6fe7f70bf383aa27e8b34366fb764901c`；修订 `scripts/score_cross_page_predictions.py` SHA-256 `d95b347b02ee0ebd99c695cdd1a6ed98f5434d0003891b08da1b5577af170154`，使 `--partial` 从完整 GT 清单中只提取本次 manifest 的文档。

## 转换契约与执行

转换器检查页/文档 ID 唯一、实际页覆盖、预测所属文档、`run-manifest` 中的固定数据 revision/赛道/清单哈希/预测路径，逐页将保存的 `raw_output` 与 `tables_html`/warnings 重新解析比对；有表却无原始布局时拒绝生成来源证据。输出逐页结果仅保留终态，不重复携带表格；文档表按稳定 `document-page-table` ID 保存 HTML 和单一 `source_pages`；每张表另写原图 ID、原布局元素索引、原 bbox 和原输出哈希。该模式**不做任何续接、表头消重或跨页合并**。错误页和警告单独计数。对多分片输入没有运行清单可证实时，不借单个清单给全部分片背书。

两次独立输出分别在 `artifacts/cross-page-adapters/20260929T095939Z-dots-smoke-no-merge/`、`artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/`，对应评分输出在 `artifacts/cross-page-scores/` 下同名目录；**均保留、没有覆盖原始预测或旧产物**。首次适配发生在将计数字段 `documents_seen` 明确改名为 `documents_in_manifest` 前，其 `summary.json` 因此与第二次不同；两次的三个主要 JSONL 与三份评分文件逐项哈希完全一致。以下命令是第二次实际执行：

```bash
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/adapt_dotsocr_document_predictions.py \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl \
  --predictions outputs/baselines/dots-ocr/20260921T081448Z-dots-full-documents-smoke/predictions.jsonl \
  --run-manifest artifacts/run-manifests/20260921T081448Z-dots-full-documents-smoke.json \
  --output-dir artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/score_cross_page_predictions.py \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl \
  --page-results artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/page-results.jsonl \
  --document-tables artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/document-tables.jsonl \
  --truth-dir 'data/pubtables-v2/extracted/Full Documents/val/tables' \
  --cross-page-gold artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl \
  --output-dir artifacts/cross-page-scores/20260929T100115Z-dots-smoke-no-merge --partial
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -p no:cacheprovider \
  --basetemp=artifacts/test-runs/20260929-dots-adapter-suite-02 -q
.venvs/eval312/bin/ruff check src/cptla/evaluation/dotsocr_document.py scripts/adapt_dotsocr_document_predictions.py scripts/score_cross_page_predictions.py tests/evaluation/test_dotsocr_document.py tests/evaluation/test_cross_page.py
.venvs/eval312/bin/ruff format --check src/cptla/evaluation/dotsocr_document.py scripts/adapt_dotsocr_document_predictions.py scripts/score_cross_page_predictions.py tests/evaluation/test_dotsocr_document.py tests/evaluation/test_cross_page.py
git diff --check
```

环境：项目 `.venvs/eval312`、Python 3.12.7、GriTS vendored `third_party/grits-main`、pytest 8.4.2；命令无随机步骤，随机种子不适用；原推理种子 `20260724` 见旧 run manifest。无后台任务/PID，本轮 stdout 未另存日志；转换 summary、评分 metrics 和测试临时目录为保存证据。

## 验收、勘误及边界

- 覆盖 **3/3 页**，missing/extra/duplicate 均为 0，错误页 0，原 runner warning 0；生成 1 张文档表、1 条来源证据，来源 `PMC11977379_page_1.jpg`、布局元素索引 3、bbox `[128,155,956,1340]`。输出 `page-results.jsonl`、`document-tables.jsonl`、`table-evidence.jsonl` SHA-256 分别为 `8dfdc03d5ad51c0ec9a33ee53bd8c3ce4ff1b81cd2456d0217274d654031fedb`、`795cd6322c41672f1e6f95b2a9c23d80353214151c39b4408c164df2f63bbe24`、`10333fe5b9f9aff2d91247b516924a32f4f7887f648682c4d9b792a81a5b6e1e`。
- **重要更正：**开始本轮时曾口头误认为该 smoke 文档没有跨页真值；只读检查原始 `val/tables/PMC11977379_tables.json` 及阶段 0 清单后发现仅有的真值表 `PMC11977379-table-0` 的 `parts.page_num=[1,2]`。它是跨页表，旧 dots.ocr 仅输出来自第 1 页的单页表。此前错误判断并非已有的正式指标，不得延续该说法。
- 单文档 `partial/smoke` 复评：GT 跨页表 1，匹配预测 1，但来源真值页 `[1,2]` vs 预测 `[1]`；`matched_cross_page_missing_source_pages=1`；内容网格 exact match **0/1**。仅供检查评分通路：局部内容 `GriTS-Con≈0.8193` 不代表跨页整表恢复成功，更不是 val 全量性能、检测 precision 或四模型可比成绩。`metrics.json` SHA-256 `33925c8842cdfe5a5c0f2fa2629b251907b36c3ff4d8f7659aff04ab2e544444`；`matches.jsonl` `604fa5bc44d69cc5bb0a4d5f03833b951893ce3c0b19f872857930c7a882fcdb`；`failures.jsonl` 为空，SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。两次不同目录同输入复算的上述 6 个哈希完全一致。
- 全量测试 **135 passed**，Ruff 与 diff check 通过；新增测试覆盖多表同 HTML/不同布局索引、无表页、缺/重复/额外页、原始 HTML/警告冲突、缺来源、失败页、不可覆盖已存在目录，以及 `--partial` 真值文档过滤。最初单测曾因输入检查顺序错误，使重复文档页被误报为覆盖缺失；已经先验清单结构检查后重新运行通过。测试里未使用 test 标签。
- **已提供**：旧推理保存记录、模型 revision、原始真值、两次转换/复评产物。**推断/项目协议**：`no_merge` 来源页诊断和部分范围 GriTS。**待核验**：在新推理的全 935 篇/13,871 页上运行；跨页续接判断与真正合并；其余三模型 schema、许可及权重；TEDS/语义误合并率。没有下载、重新推理、运行 GPU 或更改原始数据。

下一步：先在 train/合成文档上设计非真值的续接与简单拼接对照（重复表头、列数变化及拆分行作为待审计难例），只在输出来源可追溯后进行完整文档 smoke；同时审查 OCRFlux/Popo/Paddle 的官方接口与许可。**不要**据本次单文档结果调规则；真实 val 全文档仍需独立全页推理和新的 GPU 资源核验。
