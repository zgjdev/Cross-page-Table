# Table Case Analysis Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为完整的 PubTables-v2 Cropped Tables 预测生成全量样本诊断和约 60 例原图/真值/预测三栏静态 HTML 报告。

**Architecture:** 将纯分析逻辑与 HTML 产物生成分开：`case_analysis.py` 负责解析表格、逐样本 GriTS、错误/复杂度标签和确定性分层抽样，`case_report.py` 负责安全重建表格与静态报告，单一 CLI 从 YAML 配置装配输入。当前 TATR 配置只引用服务器项目根目录内的已有只读数据和结果，输出自动使用新 UTC run 目录。

**Tech Stack:** Python 3.11、Pydantic 2、PyYAML、vendored GriTS、标准库 HTML/XML/JSON/shutil、pytest、Ruff。

## Global Constraints

- 服务器只允许访问 `/data01/public/zhengguojie/paper`，所有输入只读，不得删除、移动、截断或覆盖已有数据和结果。
- 第一版只支持 `cropped_tables`，不得将报告解释为跨页恢复效果。
- 不使用 GPU，不重新推理；输出目录已存在时必须失败。
- 自动错误标签是诊断线索，不能替代典型案例人工核验。
- 本地不下载 PubTables-v2 数据；服务器数据路径通过项目内只读检查确认。

---

### Task 1: 样本级诊断与确定性分层抽样

**Files:**
- Create: `src/cptla/evaluation/case_analysis.py`
- Test: `tests/evaluation/test_case_analysis.py`

**Interfaces:**
- Consumes: `PredictionRecord`、`ImageManifestEntry`、`grits.html_to_cell_list`、`GritsEvaluator`
- Produces: `TableProfile`、`CaseDiagnostic`、`profile_html(html) -> TableProfile`、`analyze_cropped_case(entry, prediction, truth_html) -> CaseDiagnostic`、`add_complexity_tags(cases) -> list[CaseDiagnostic]`、`stratified_sample(cases, sample_size, seed, include_ids) -> list[CaseDiagnostic]`

- [ ] **Step 1: 写失败测试覆盖表格结构描述和错误标签**

```python
def test_analyze_case_separates_span_header_and_text_mismatch() -> None:
    truth = "<table><thead><tr><th colspan='2'>H</th></tr></thead><tbody><tr><td>A</td><td>B</td></tr></tbody></table>"
    pred = "<table><thead><tr><th>H</th><th></th></tr></thead><tbody><tr><td>A</td><td>X</td></tr></tbody></table>"
    case = analyze_cropped_case(_entry("x"), _prediction("x", pred), truth)
    assert case.truth_profile.column_count == 2
    assert case.truth_profile.header_row_count == 1
    assert {"span_mismatch", "text_mismatch"} <= set(case.error_tags)
    assert case.grits_top < 1
    assert case.grits_con < 1
```

- [ ] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `pytest tests/evaluation/test_case_analysis.py -q`
Expected: FAIL，`ModuleNotFoundError: cptla.evaluation.case_analysis`

- [ ] **Step 3: 实现最小结构描述、逐样本 GriTS 和标签逻辑**

实现不可变 Pydantic 模型；由 `TableCell.row_nums/column_nums` 推导行列、header 和 span，使用单样本 `GritsEvaluator(metrics=["top", "con"])` 计算公开指标。错误或空预测按空表集合评分，不能丢弃。

- [ ] **Step 4: 写失败测试覆盖五个分数层、复杂度覆盖、强制 ID、去重和确定性**

```python
def test_stratified_sample_is_deterministic_and_honors_includes() -> None:
    cases = [_case(index) for index in range(100)]
    first = stratified_sample(cases, sample_size=20, seed=17, include_ids=["case-99"])
    second = stratified_sample(list(reversed(cases)), sample_size=20, seed=17, include_ids=["case-99"])
    assert [item.unit_id for item in first] == [item.unit_id for item in second]
    assert len(first) == 20
    assert "case-99" in {item.unit_id for item in first}
    assert len({item.unit_id for item in first}) == 20
```

- [ ] **Step 5: 实现 90% 分位复杂度标签和稳定哈希分层抽样**

五层为 `exact`、`high_non_exact`、`medium`、`low`、`zero_or_empty`。先轮转选择不同复杂度/错误标签，再按 `sha256(f"{seed}:{unit_id}")` 排序补足；输入顺序不得影响结果。

- [ ] **Step 6: 运行目标测试与 Ruff**

Run: `pytest tests/evaluation/test_case_analysis.py -q && ruff check src/cptla/evaluation/case_analysis.py tests/evaluation/test_case_analysis.py`
Expected: 全部通过，exit code 0。

- [ ] **Step 7: 提交分析核心**

```bash
git add src/cptla/evaluation/case_analysis.py tests/evaluation/test_case_analysis.py
git commit -m "feat: add table case diagnostics and sampling"
```

### Task 2: 安全三栏静态 HTML 报告

**Files:**
- Create: `src/cptla/evaluation/case_report.py`
- Test: `tests/evaluation/test_case_report.py`

**Interfaces:**
- Consumes: `CaseDiagnostic` 和抽样案例对应的 truth/prediction HTML、manifest 图像路径
- Produces: `render_comparison_table(html, counterpart_html, side) -> str`、`write_case_report(output_dir, all_cases, selected_cases, records_by_id, truth_by_id, images_dir, metadata) -> Path`

- [ ] **Step 1: 写失败测试验证表格重建转义脚本和三栏内容**

```python
def test_rendered_report_escapes_scripts_and_contains_three_views(tmp_path: Path) -> None:
    index = _write_report(tmp_path, cell_text="<script>alert(1)</script>")
    html = index.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'data-view="source-image"' in html
    assert 'data-view="ground-truth"' in html
    assert 'data-view="prediction"' in html
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `pytest tests/evaluation/test_case_report.py -q`
Expected: FAIL，报告模块尚不存在。

- [ ] **Step 3: 实现白名单表格重建和差异颜色**

只从 `html_to_cell_list` 的 `TableCell` 重建 `<table>/<tr>/<th>/<td>`，文本统一 `html.escape`；只生成计算得到的 `rowspan/colspan/class`。以锚点坐标比较 counterpart 的 span 和规范化文本，生成 `cell-match`、`cell-text-diff`、`cell-structure-diff` 和 `cell-one-sided`。

- [ ] **Step 4: 写失败测试验证相对图片、筛选元数据、JSON 全量记录和拒绝覆盖**

```python
def test_report_is_portable_and_refuses_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "report"
    index = _write_report(output)
    assert (output / "cases.json").is_file()
    assert (output / "assets" / "images" / "x.jpg").is_file()
    assert "assets/images/x.jpg" in index.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        _write_report(output)
```

- [ ] **Step 5: 实现静态 CSS/JS、图像复制、摘要和筛选**

报告不引用 CDN。JS 只读取生成时写入案例卡片的 `data-score-stratum/data-error-tags/data-complexity-tags` 属性进行筛选；原图点击使用原生 `<dialog>` 放大。`cases.json` 保存全量诊断和选择状态，不保存任意可执行 HTML。

- [ ] **Step 6: 运行目标测试与 Ruff**

Run: `pytest tests/evaluation/test_case_report.py -q && ruff check src/cptla/evaluation/case_report.py tests/evaluation/test_case_report.py`
Expected: 全部通过，exit code 0。

- [ ] **Step 7: 提交报告生成器**

```bash
git add src/cptla/evaluation/case_report.py tests/evaluation/test_case_report.py
git commit -m "feat: generate static table case reports"
```

### Task 3: 一条命令入口与当前 TATR 配置

**Files:**
- Create: `scripts/build_table_case_report.py`
- Create: `configs/evaluation/tatr-cropped-val-case-report.yaml`
- Test: `tests/evaluation/test_case_report_cli.py`

**Interfaces:**
- Consumes: YAML 中的项目相对输入路径、`load_truth_directory`、Task 1/2 接口
- Produces: `python scripts/build_table_case_report.py --config <yaml>`，自动创建 `<output_root>/<UTC>-<run_name>/index.html`

- [ ] **Step 1: 写失败测试验证配置、精确覆盖门禁与自动 run 目录**

```python
def test_cli_builds_timestamped_report_from_config(tmp_path: Path, monkeypatch) -> None:
    config = _fixture_config(tmp_path)
    monkeypatch.setattr(script, "utc_run_id", lambda name: f"20260924T120000Z-{name}")
    assert script.run(config) == 0
    assert (tmp_path / "reports/20260924T120000Z-tatr-cropped-case-report/index.html").is_file()
```

另写缺失 prediction、重复 prediction、manifest 图片不存在、`collection != cropped_tables` 和现有输出目录的失败测试。

- [ ] **Step 2: 运行测试并确认失败**

Run: `pytest tests/evaluation/test_case_report_cli.py -q`
Expected: FAIL，CLI 模块尚不存在。

- [ ] **Step 3: 实现配置模型、加载器、覆盖门禁和进度输出**

CLI 先完整验证 manifest/prediction/truth/image 对应关系，再创建输出目录。逐样本计算时每 100 个样本输出一次进度；最终打印 JSON，包含 run ID、总数、抽样数、标签计数和 `index.html` 路径。

- [ ] **Step 4: 只读确认服务器真实叶子目录并填写当前配置**

在 `/data01/public/zhengguojie/paper` 内只读检查当前 manifest、rebuilt predictions、Cropped Tables `images` 和 `tables` 叶子目录。配置使用项目相对路径，固定 `sample_size: 60`、`seed: 20260924` 和 `output_root: outputs/analysis/table-case-reports`。

- [ ] **Step 5: 运行 CLI 测试、相关回归和 Ruff**

Run: `pytest tests/evaluation/test_case_analysis.py tests/evaluation/test_case_report.py tests/evaluation/test_case_report_cli.py tests/evaluation/test_scoring.py -q && ruff check src scripts tests`
Expected: 全部通过，exit code 0。

- [ ] **Step 6: 提交 CLI 和配置**

```bash
git add scripts/build_table_case_report.py configs/evaluation/tatr-cropped-val-case-report.yaml tests/evaluation/test_case_report_cli.py
git commit -m "feat: add one-command table case report"
```

### Task 4: 文档、完整验证与双远程同步

**Files:**
- Create: `docs/experiments/2026-09-24-tatr-case-analysis-visualization.zh-CN.md`
- Modify: `docs/2026-09-22-research-progress.zh-CN.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: 已验证 CLI、服务器路径和测试输出
- Produces: 启动说明、科研边界、进度索引和可复现命令

- [ ] **Step 1: 写中文实验文档和 README 命令**

记录状态为“工具已实现、服务器报告待运行”，包括固定 dataset revision、输入 run、配置、命令、CPU-only、输出规则和人工复核要求；未实际生成报告前不得填写案例结论。

- [ ] **Step 2: 运行完整本地验证**

Run: `pytest -q`
Expected: 0 failures。

Run: `ruff check src scripts tests`
Expected: `All checks passed!`

Run: `git diff --check`
Expected: 无输出，exit code 0。

- [ ] **Step 3: 提交文档并确认只包含本功能修改**

```bash
git add README.md docs/2026-09-22-research-progress.zh-CN.md docs/experiments/2026-09-24-tatr-case-analysis-visualization.zh-CN.md docs/superpowers/plans/2026-09-24-table-case-analysis-report.md
git commit -m "docs: document table case report workflow"
git status --short --branch
```

- [ ] **Step 4: 推送相同分支到两个远程并核验远端 commit**

```bash
git push origin codex/two-baseline-validation-local
git push gpu codex/two-baseline-validation-local
git ls-remote origin refs/heads/codex/two-baseline-validation-local
git ls-remote gpu refs/heads/codex/two-baseline-validation-local
```

两端 SHA 必须等于本地 `git rev-parse HEAD`。服务器工作树若不是自动更新，不执行会覆盖数据目录的同步；只向用户提供在服务器项目根目录拉取代码及启动报告的安全命令。
