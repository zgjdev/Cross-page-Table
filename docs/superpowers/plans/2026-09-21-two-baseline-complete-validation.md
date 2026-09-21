# 两个基线模型完整验证实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 PubTables-v2 固定 revision 上完成 TATR-v1.1-Pub 的 `Cropped Tables/val` PDF-text-assisted 评测，以及 dots.ocr 的 `Cropped Tables/val` 和 `Full Documents/val` image-only 评测，并保存可离线复算的完整证据链。

**Architecture:** 将数据清单、覆盖率审计、模型推理和 GriTS 评分拆成四个边界。两个模型都写入统一 JSONL 预测协议，评分器只读预测、真值和输入清单，因此可以不重跑 GPU 离线复算。先在合成 fixture 上执行 TDD，再做服务器数据审计、smoke 和全量 validation。

**Tech Stack:** Python 3.12，Pydantic 2，PyTorch/Transformers，项目固定的 `third_party/grits-main`，Microsoft Table Transformer 官方 post-processing，dots.ocr/Qwen-VL 推理栈，pytest。

## Global Constraints

- 主数据集固定为 `kensho/PubTables-v2@aa575e798cb00a296925e2086addb3e3fd9a1903`。
- 仅使用 validation；test split 不得参与调试、阈值、规则、提示词或模型选择。
- `TATR-v1.1-Pub + Direct Text` 必须标为 PDF-text-assisted；dots.ocr 必须标为 image-only，不得合并排名。
- 服务器只访问 `/data01/public/zhengguojie/paper`，不删除、移动、截断或覆盖已有数据和结果。
- 新数据、新日志和新输出使用新的 UTC 时间戳目录；同步排除 `data/`、`artifacts/`、`outputs/`、`logs/`、`checkpoints/` 和 `.venvs/`。
- GPU 任务前必须检查显存和进程，不终止任何其他用户进程。
- Full Documents 必须覆盖 val 全部 13,871 页，不得使用真值预筛选含表页。
- 不把 TATR-v1.1-Pub 写成 TATR-v1.2-Pub，不把未合并页级结果写成跨页恢复结果。

---

## 文件边界

- `src/cptla/evaluation/contracts.py`：预测记录、覆盖率报告和 run manifest 的 Pydantic 协议。
- `src/cptla/evaluation/pubtables_v2.py`：稳定 ID 解析、输入清单生成、真值加载和覆盖率核对。
- `src/cptla/evaluation/dotsocr.py`：dots.ocr layout JSON 解析和 table HTML 提取，不加载模型。
- `src/cptla/evaluation/scoring.py`：使用固定 GriTS 实现的集合评分与失败索引。
- `scripts/build_validation_manifest.py`：从文件系统生成确定性输入清单，不读真值来筛页。
- `scripts/download_pubtables_v2_cropped_val.py`：固定 revision 下载并记录 Cropped Tables val 归档清单。
- `scripts/evaluate_dotsocr_pubtables_v2.py`：可恢复 dots.ocr 推理，每个输入恰好一条终态记录。
- `scripts/evaluate_tatr_pubtables_v2.py`：TATR-v1.1-Pub + Direct Text 推理和官方 post-processing。
- `scripts/score_pubtables_v2_predictions.py`：统一离线评分 CLI。
- `scripts/write_baseline_run_manifest.py`：采集 Git、Python、CUDA、模型、数据和路径信息。
- `tests/evaluation/`：全部新协议、解析、覆盖和评分行为的合成测试。

### Task 1: 统一预测与运行协议

**Files:**
- Create: `src/cptla/evaluation/__init__.py`
- Create: `src/cptla/evaluation/contracts.py`
- Create: `tests/evaluation/test_contracts.py`

**Interfaces:**
- Produces: `PredictionRecord(image_id: str, unit_id: str, status: Literal["ok", "error"], tables_html: list[str], elapsed_sec: float, error: str | None)`
- Produces: `CoverageReport(expected, seen, missing, extra, duplicates)` 和 `is_complete`
- Produces: `RunManifest` 及 `validate_manifest_paths()`

- [ ] **Step 1: 写失败测试**

```python
def test_coverage_is_incomplete_when_prediction_is_missing() -> None:
    report = CoverageReport.from_ids(["a", "b"], ["a"])
    assert report.missing == ["b"]
    assert report.is_complete is False

def test_prediction_requires_error_message_for_error_status() -> None:
    with pytest.raises(ValidationError):
        PredictionRecord(image_id="a.jpg", unit_id="a", status="error", tables_html=[], elapsed_sec=1)
```

- [ ] **Step 2: 运行 `pytest tests/evaluation/test_contracts.py -v`，确认因 `cptla.evaluation` 不存在而失败**
- [ ] **Step 3: 用 Pydantic 实现上述类，`CoverageReport.from_ids()` 对 ID 排序并显式记录重复项**
- [ ] **Step 4: 运行 `pytest tests/evaluation/test_contracts.py -v`，预期全部 PASS**
- [ ] **Step 5: 提交 `git commit -m "feat: define baseline evaluation contracts"`**

### Task 2: 确定性输入清单与稳定 ID

**Files:**
- Create: `src/cptla/evaluation/pubtables_v2.py`
- Create: `scripts/build_validation_manifest.py`
- Create: `tests/evaluation/test_pubtables_v2_manifest.py`

**Interfaces:**
- Consumes: `CoverageReport`
- Produces: `parse_full_document_image_id(name) -> tuple[document_id, page_number]`
- Produces: `parse_cropped_table_id(name) -> str`
- Produces: `build_image_manifest(images_dir, collection) -> list[str]`

- [ ] **Step 1: 写测试，要求 `PMC123_page_7.jpg` 解析为 `("PMC123", 7)`，非 JPG、负页号和不合法命名拒绝**
- [ ] **Step 2: 写测试，在临时 `images/` 中创建乱序文件，确认 manifest 仅包含所有 `.jpg`、字典序稳定、SHA-256 在重跑时不变**
- [ ] **Step 3: 运行 `pytest tests/evaluation/test_pubtables_v2_manifest.py -v`，确认因函数缺失而失败**
- [ ] **Step 4: 实现库函数和 CLI；CLI 输出 JSONL，字段固定为 `image_id`、`relative_path`、`unit_id`、`document_id`、`page_number`**
- [ ] **Step 5: 运行 `pytest tests/evaluation/test_pubtables_v2_manifest.py -v`，预期全部 PASS**
- [ ] **Step 6: 提交 `git commit -m "feat: build deterministic validation manifests"`**

### Task 3: dots.ocr 解析与可恢复推理协议

**Files:**
- Create: `src/cptla/evaluation/dotsocr.py`
- Modify: `scripts/evaluate_dotsocr_pubtables_v2.py`
- Create: `tests/evaluation/test_dotsocr.py`
- Create: `tests/evaluation/test_dotsocr_runner.py`

**Interfaces:**
- Produces: `parse_layout(raw: str) -> list[dict[str, object]]`
- Produces: `extract_table_html(raw: str) -> tuple[list[str], list[str]]`，第二项为解析警告
- Consumes: Task 2 JSONL manifest
- Produces: `PredictionRecord` JSONL，记录 `image_id` 而非绝对路径

- [ ] **Step 1: 写测试覆盖直接 JSON、Markdown fence、`json_repair`、合法 table HTML、非 table 元素和非法 HTML**
- [ ] **Step 2: 写 runner 测试，向已有 JSONL 放入一条成功、一条重复和一条损坏尾行，确认只恢复未完成的输入且不覆盖原文件**
- [ ] **Step 3: 运行 `pytest tests/evaluation/test_dotsocr.py tests/evaluation/test_dotsocr_runner.py -v`，确认按预期失败**
- [ ] **Step 4: 抽取解析库，改造 runner 使用清单、原子级单行 append/flush，对每个输入只保留一个终态记录**
- [ ] **Step 5: 运行上述测试和 `ruff check src/cptla/evaluation scripts/evaluate_dotsocr_pubtables_v2.py tests/evaluation`，预期 PASS**
- [ ] **Step 6: 提交 `git commit -m "feat: harden resumable dots ocr evaluation"`**

### Task 4: 覆盖率强制与统一 GriTS 评分

**Files:**
- Create: `src/cptla/evaluation/scoring.py`
- Create: `scripts/score_pubtables_v2_predictions.py`
- Replace: `scripts/score_dotsocr_pubtables_v2.py` 为兼容转发层
- Create: `tests/evaluation/test_scoring.py`
- Create: `tests/fixtures/evaluation/truth.json`

**Interfaces:**
- Consumes: `PredictionRecord` JSONL、Task 2 manifest、PubTables-v2 `tables/*.json`
- Produces: `score_predictions(..., require_complete: bool) -> tuple[dict, list[dict]]`
- Produces: metrics JSON 和 failures JSONL

- [ ] **Step 1: 写测试覆盖完全正确、空预测、额外假阳性、多表匈牙匹配、缺失页、重复页、额外页和非法 HTML**
- [ ] **Step 2: 写测试要求 `require_complete=True` 在任何 missing/extra/duplicate 时抛出 `IncompleteCoverageError`，且不能写出 `scope=full_validation`**
- [ ] **Step 3: 以 `PYTHONPATH=third_party/grits-main` 运行 `pytest tests/evaluation/test_scoring.py -v`，确认函数缺失导致失败**
- [ ] **Step 4: 实现文档级/表格级聚合，所有缺失预测以空列表评分，额外预测保留为 false positive，输出覆盖计数和失败索引**
- [ ] **Step 5: 连续运行两次相同 fixture 离线评分，对两份 metrics JSON 做字节级比较，预期完全一致**
- [ ] **Step 6: 运行全部 evaluation tests 和 Ruff，预期 PASS**
- [ ] **Step 7: 提交 `git commit -m "feat: enforce complete offline grits scoring"`**

### Task 5: TATR-v1.1-Pub + Direct Text 推理入口

**Files:**
- Create: `src/cptla/evaluation/tatr.py`
- Create: `scripts/evaluate_tatr_pubtables_v2.py`
- Create: `tests/evaluation/test_tatr.py`
- Create: `configs/baselines/tatr-v1.1-pub-direct-text.yaml`

**Interfaces:**
- Produces: `load_pdf_words(path) -> list[dict]`
- Produces: `scale_words_to_image(words, pdf_bbox, image_size) -> list[dict]`
- Produces: `tatr_objects_to_prediction(outputs, words, thresholds) -> PredictionRecord`
- Consumes: Cropped Tables JSONL manifest，对应 words/XML，`checkpoints/tatr-v1.1-pub`

- [ ] **Step 1: 写 bbox 测试，使用已知 PDF 尺寸和图像尺寸确认 x/y 独立缩放、边界裁剪和非法 bbox 拒绝**
- [ ] **Step 2: 写 ID/真值关联测试，确保每张 cropped image 恰好匹配一个 words 和一个 table annotation**
- [ ] **Step 3: 写合成结构输出测试，确认行、列、表头、spanning cell 和 Direct Text 被传给官方 `objects_to_cells`/post-processing 适配层**
- [ ] **Step 4: 运行 `pytest tests/evaluation/test_tatr.py -v`，确认按预期失败**
- [ ] **Step 5: 用 Hugging Face 模型加载和项目固定的 Microsoft post-processing 实现 runner；配置显式保存模型 revision、类别阈值、随机种子和 input track**
- [ ] **Step 6: 运行 TATR 单元测试、全部 evaluation tests 和 Ruff，预期 PASS**
- [ ] **Step 7: 提交 `git commit -m "feat: add tatr direct text validation runner"`**

### Task 6: Cropped Tables val 安全下载与 run manifest

**Files:**
- Create: `scripts/download_pubtables_v2_cropped_val.py`
- Create: `scripts/write_baseline_run_manifest.py`
- Create: `tests/evaluation/test_download_selection.py`
- Create: `tests/evaluation/test_run_manifest.py`
- Modify: `configs/data/pubtables_v2.yaml`

**Interfaces:**
- Produces: 只包含 Cropped Tables val `images/tables/words/xml_annotations` 的下载选择列表
- Produces: `artifacts/run-manifests/<run-id>.json`

- [ ] **Step 1: 写测试，向伪造的 Hugging Face 文件列表混入 train/test/Single Pages，确认选择器只返回 Cropped Tables val 四类归档**
- [ ] **Step 2: 写 run manifest 测试，确保缺少 Git commit、dataset/model revision、input hash、command、seed、GPU、路径或覆盖计数任一字段都无法通过验证**
- [ ] **Step 3: 运行两个测试文件，确认按预期失败**
- [ ] **Step 4: 实现只新增归档和解压目录的下载器，已有目标拒绝覆盖；在 manifest 中保存官方路径、字节数、resolved SHA 和本地目标**
- [ ] **Step 5: 实现 run manifest 采集，敏感环境变量仅记录变量名是否存在，绝不记录值**
- [ ] **Step 6: 运行新测试、全部 pytest 和 Ruff，预期 PASS**
- [ ] **Step 7: 提交 `git commit -m "feat: pin cropped validation data and run manifests"`**

### Task 7: 服务器同步、数据审计与三条 smoke

**Files:**
- Create: `docs/experiments/<run-date>-two-baseline-smoke.zh-CN.md`
- Generated only: `artifacts/input-manifests/`、`artifacts/run-manifests/`、`outputs/baselines/`、`logs/baselines/`

**Interfaces:**
- Consumes: Tasks 1–6 的已提交代码
- Produces: TATR cropped、dots cropped、dots full-doc 的 smoke 预测、指标、失败索引和运行清单

- [ ] **Step 1: 本地运行 `pytest -v`、`ruff check .` 和 `git diff --check`，全部通过后记录 commit SHA**
- [ ] **Step 2: 只读检查 `ssh 172.17.60.82 'cd /data01/public/zhengguojie/paper && git status --short --branch && nvidia-smi'`，记录 GPU 型号、显存、进程和项目状态**
- [ ] **Step 3: 用不带 `--delete` 的增量同步更新代码，显式排除 `data/ artifacts/ outputs/ logs/ checkpoints/ .venvs/`；同步后确认服务器已有数据和输出目录仍在**
- [ ] **Step 4: 运行下载器将四个 Cropped Tables val 归档新增到 `data/pubtables-v2/archives/<timestamp>/`，解压到 `data/pubtables-v2/extracted/Cropped Tables/val/`，核对数量、大小、压缩包可读性和四类 ID 关联率**
- [ ] **Step 5: 生成三份全量输入清单和三份 smoke 子清单；Full Documents 全量清单必须恰好 13,871 条**
- [ ] **Step 6: 选择显存充足且无冲突的 GPU，运行 TATR smoke；检查 100% 真值关联、覆盖、HTML 可解析率、峰值显存和离线复评一致性**
- [ ] **Step 7: 运行 dots cropped smoke 和一篇完整跨页文档 smoke；后者必须包含该文档的无表页**
- [ ] **Step 8: 将命令、commit、环境、样本、覆盖、指标、错误和资源记录写入中文 smoke 报告；任一停止条件命中时不启动全量运行**
- [ ] **Step 9: 提交报告 `git commit -m "docs: record two baseline smoke validation"`**

### Task 8: 三条完整 validation 与导师汇报摘要

**Files:**
- Create: `docs/experiments/<run-date>-two-baseline-validation.zh-CN.md`
- Modify: `docs/research-handoff-2026-08-26.zh-CN.md`
- Generated only: timestamped run directories under ignored artifact/output/log roots

**Interfaces:**
- Consumes: 通过 Task 7 的三条 smoke 和冻结配置
- Produces: 三条完整 validation 结果、离线复评结果和中文汇报表

- [ ] **Step 1: 在新 UTC run ID 下启动 TATR Cropped Tables val，完成后要求清单、预测、真值三方 ID 关联为 100%**
- [ ] **Step 2: 在新 UTC run ID 下启动 dots.ocr Cropped Tables val，按互斥分片运行并可恢复，合并时拒绝重复 ID**
- [ ] **Step 3: 在新 UTC run ID 下启动 dots.ocr Full Documents val 全部 13,871 页，不读取 tables/XML 生成推理清单**
- [ ] **Step 4: 对三条预测各自独立离线评分两次，确认指标 JSON 完全一致，且完整运行没有 missing/extra/duplicate**
- [ ] **Step 5: 生成阶段结果表，分开 PDF-text-assisted 与 image-only，列出样本数、覆盖率、Acc-Top/Con、GriTS-Top/Con、解析率、非法 HTML、推理失败、总时间和单样本时间分布**
- [ ] **Step 6: 文档显式区分“项目实测”、“论文报告”和“待核验”，说明 TATR-v1.1 不等于 v1.2，Full Documents 结果未做跨页合并**
- [ ] **Step 7: 更新 research handoff，引用精确的 run manifest、metrics 和 failures 路径**
- [ ] **Step 8: 重跑 `pytest -v`、`ruff check .`、`git diff --check`，确认全部通过**
- [ ] **Step 9: 提交 `git commit -m "docs: report complete two baseline validation"`**

## 计划自审

- 覆盖了设计中的三条评测、两种输入赛道、全页覆盖、离线复评、manifest、失败索引、GPU 安全和中文报告。
- 每个生产代码任务都是先写失败测试，再写最小实现，然后运行定向和全量验证。
- 稳定 ID、`PredictionRecord`、`CoverageReport`、`RunManifest` 和评分接口在前置任务定义，后续任务名称一致。
- 未包含 test split 运行、模型训练、continuation oracle、跨页合并或未公开权重的替代实现。

