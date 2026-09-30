# dots.ocr 重复表头简单拼接基线：结构测试与旧 smoke 核验

日期与时区：2026-09-29 UTC（核验至 10:14:57 UTC）。状态：**保守 CPU 基线的实现和接口测试已完成；真实 train/val 全文档质量评估未完成**。

## 研究问题和固定输入

在不读取 GT 页面对关系作为**推理输入**的前提下，能否建立一个可重复评分、不会凭“列数相同”直接拼接的明确对照？实现位于 `src/cptla/evaluation/simple_merge.py`、`scripts/merge_dotsocr_repeated_header.py`；新增 `tests/evaluation/test_simple_merge.py`。基础 HEAD `e6154932b8efe43c98cee6e02f18ea017969aa41`，上述三文件 SHA-256 分别为 `b6cd4e1c681dae0ae7b3b5dca4a8766e9d7a45c1cc7e9781f7ba50af021bc413`、`ce82e8e7125292fddfbbdc6b3c43736865b00c704739de501328c648ac1867c6`、`03e42af10cd2ab2ee21e42ef6ea0b6d14761804b2e96b7fe33717341f3679688`；这些新增文件尚未提交。

- 数据集固定 PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；数据用途严格隔离：train 文档 `PMC10158982` 的**完整 GT HTML 仅用于解析器的人工行切分单测**，不冒充真实逐页模型输出；另用纯合成正负例测试规则。validation `PMC11977379` 使用之前保存的 dots.ocr 3 页预测，**冻结规则后才运行**一次接口/负向 smoke；不根据它调整门槛。
- 输入赛道 `image-only`；旧 dots.ocr 权重 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，原推理及运行环境见 `artifacts/run-manifests/20260921T081448Z-dots-full-documents-smoke.json` 和 `docs/experiments/2026-09-29-dotsocr-no-merge-document-adapter-smoke.zh-CN.md`。本轮**没有模型推理、下载、训练或使用 GPU**；CPU 使用项目 `.venvs/eval312`，Python 3.12.7、vendored GriTS、pytest 8.4.2；随机种子不适用（无随机步骤）。

## 冻结的非真值规则

只考虑同一文档的**相邻两页**，“前页最后一张预测表/后页第一张预测表”。检查全部输入页终态、表/原页证据一一对应、文档 ID 与图像尺寸一致；用源 JPG 宽高归一化模型 bbox。须同时满足：两页均无推理错误；前表下边缘处在图片高度的最后 20%（`y2/H >= 0.8`）；后表上边缘处在前 25%（`y1/H <= 0.25`）；HTML 能用固定的 GriTS XML 路径解析、两表列数相同、**表头文本完全相同且是显式 `<thead>`/`<th>`**，后表至少还有一行正文。布局次序/bbox 无法确定或存在跨拼接边界的 rowspan 时拒绝。只删掉后表的重复表头，追加其正文行；保留首表 HTML 网格和两表来源页。三页链按顺序拼接，绝不从 GT 推测缺失页。每个实际候选边界的接受/拒绝原因写入 `decisions.jsonl`。上述 0.8/0.25 与 exact-header 门槛是预先定义的保守**项目基线常量**，尚未做真实 train 统计校准，不能声称最优。

## 实际执行和结果

输入：三页 smoke manifest `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl`（SHA-256 `c4d22178526b59384a487bf0274e64c86b6d04312bb0c9fc4476dad7d6afb006`）；已核验 adapter `artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/`（`summary.json` SHA-256 `5671ed79af51f7d6ab2fc8ac7a06d206f90ed5b82fd8e5b247012db9090b69c2`）。CLI 在处理前重新核对上游清单和三个 JSONL 哈希，已存在的输出目录拒绝写入；原始图像、预测、GT 与上游 adapter 均保持只读。

```bash
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/merge_dotsocr_repeated_header.py \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl \
  --adapter-dir artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge \
  --images 'data/pubtables-v2/extracted/Full Documents/val/images' \
  --output-dir artifacts/cross-page-merges/20260929T101235Z-dots-val-smoke-simple-merge
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/score_cross_page_predictions.py \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl \
  --page-results artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/page-results.jsonl \
  --document-tables artifacts/cross-page-merges/20260929T101235Z-dots-val-smoke-simple-merge/document-tables.jsonl \
  --truth-dir 'data/pubtables-v2/extracted/Full Documents/val/tables' \
  --cross-page-gold artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl \
  --output-dir artifacts/cross-page-scores/20260929T101235Z-dots-val-smoke-simple-merge --partial
PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -p no:cacheprovider \
  --basetemp=artifacts/test-runs/20260929-simple-merge-full-01 -q
.venvs/eval312/bin/ruff check src/cptla/evaluation/simple_merge.py scripts/merge_dotsocr_repeated_header.py tests/evaluation/test_simple_merge.py
.venvs/eval312/bin/ruff format --check src/cptla/evaluation/simple_merge.py scripts/merge_dotsocr_repeated_header.py tests/evaluation/test_simple_merge.py
git diff --check
```

- 单测：人工 XML 行切分了真实 train `PMC10158982` 的跨页**整表**（真实 `parts.page_num=[12,13]`，切分点只为单测安全选定，并非真正页分界），重复表头合并后 GriTS-Con grid exact = 1，**不是模型性能**。合成 2 页、3 页、无表头/异表头/异列数、版面不在页边、无效 bbox、缺页及终态错误均覆盖；CPU CLI 端到端通过。**重要负例：**完全无关的两张合成表若页边位置、列数、表头恰好一致，该规则会错误接受；因此当前规则仍可能误连，不可称为可靠续表器。
- validation 冻结检查：仅 3/3 页、原预测表 1 张，后页没有预测表；本基线 `candidate_boundaries=0`、`accepted_boundaries=0`、输出表 1 张。`document-tables.jsonl` SHA-256 `795cd6322c41672f1e6f95b2a9c23d80353214151c39b4408c164df2f63bbe24`，与 `no_merge` 完全相同；`decisions.jsonl` 为空 SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；`summary.json` SHA-256 `77bb7b6c000cb8c54ca2af196394533ff369ffb30ba5fa9fe703237956adf52f`。保存的评分 `metrics.json` SHA-256 `33925c8842cdfe5a5c0f2fa2629b251907b36c3ff4d8f7659aff04ab2e544444`，与旧 `no_merge` 一致；**不是全量 validation 分数**。真值表跨 `[1,2]` 页，而预测来源仅 `[1]`，grid exact 0/1；不能凭 GT 为模型补缺页。
- 全套回归 **149 passed**，Ruff、format 与 diff check 通过；测试临时输出 `artifacts/test-runs/20260929-simple-merge-full-01/`；没有后台任务或另存 stdout 日志。一个只读 train 探查曾误把所有 rowspan 都视为不支持，之后将拒绝条件改为仅跨越片段末尾的 rowspan，再次核验可解析 41 行；未用 validation 调整规则。

## 证据边界与下一步

**已提供：**train 原始逻辑表 HTML 与部分页号、合成用例、保存的 dots smoke、输出/哈希及测试结果。**推断/项目定义：**固定版面门槛、重复表头合并、人工行切分。**待核验：**真实 train 页级模型预测在官方相邻页正/负例上的续接误连率；更复杂的省略/变体表头、拆分行、跨页单元格和 TEDS。train 原始 GT 没有现成页级片段 HTML；不能拿本轮人工片段取代真实预测，亦不能拿该 val smoke 调门槛。

下一步优先获得**完整文档的 train 页级预测**并在 train 官方相邻页正负例上审计本基线的候选覆盖/误连，或确认是否先审查 OCRFlux/MinerU-Popo/PaddleOCR-VL 的官方接口与许可；任何新 GPU 推理前重新核查显存及现有进程，并另存运行清单。未满足资源/输入门槛前不报告简单拼接的正式端到端成绩。
