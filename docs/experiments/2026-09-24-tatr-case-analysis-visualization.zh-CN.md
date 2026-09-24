# TATR Cropped Tables 案例分析可视化工具记录

## 1. 状态摘要

- 日期与时区：2026-09-24，Asia/Shanghai
- 当前状态：工具已实现并通过本地测试；服务器全量报告尚未启动
- 研究问题：解释 TATR-v1.1-Pub 在困难裁剪单表上的非完全匹配主要与哪些结构特征相关，并为后续结构修复与 oracle 消融选择可复核案例
- 输入赛道：`PDF-text-assisted`
- GPU：不使用
- 原始数据：只读，不移动、不覆盖、不下载到本地

本工具不是固定案例库。每次运行读取一次完整实验的 manifest、predictions、truth 和 images，对全量样本生成逐样本诊断，再以固定 seed 分层选择约 60 例，输出原图、Ground Truth 和预测结果三栏静态 HTML。

## 2. 固定输入

- 数据集：PubTables-v2 `Cropped Tables/val`
- dataset revision：`aa575e798cb00a296925e2086addb3e3fd9a1903`
- 样本数：13,384
- 输入 manifest：`artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/tatr-cropped-val-full.jsonl`
- 修正后 predictions：`outputs/baselines/tatr-v1.1-pub/20260922T095039Z-tatr-cropped-val-rebuilt-score/predictions.jsonl`
- truth：`data/pubtables-v2/extracted/Cropped Tables/val/tables/Cropped Tables/val/tables`
- images：`data/pubtables-v2/extracted/Cropped Tables/val/images/Cropped Tables/val/images`
- 配置：`configs/evaluation/tatr-cropped-val-case-report.yaml`
- 实现分支：`codex/table-case-analysis-report`
- 已实现代码提交：`c38a0a3`、`1b47e0a`、`46edf0a`

上述两个嵌套数据叶子目录来自 2026-09-24 的服务器只读检查：外层目录文件数为 0，内层 images/tables 均为 13,384，manifest 首条 `relative_path` 为平面文件名。没有为修正路径而移动服务器数据。

## 3. 工具行为

### 3.1 全量诊断

每个 manifest 单元计算：

- `GriTS-Top`、`GriTS-Con`、`Acc-Top`、`Acc-Con`；
- GT/预测的行数、列数、单元格数、表头行和 span 统计；
- 推理错误、空预测、行列不一致、表头不一致、span 不一致和文本不一致等候选标签；
- 长表、宽表、多级表头和 spanning cell 等复杂度标签。

长表和宽表阈值由当前实验 GT 行列数的 90% 分位数确定，并写入 `cases.json` 元数据。自动标签是坐标启发式诊断线索，行列整体偏移可能造成级联差异，不能替代人工核验。

### 3.2 分层抽样

默认 `sample_size=60`、`seed=20260924`，覆盖 `exact`、`high_non_exact`、`medium`、`low` 和 `zero_or_empty` 五个分数层；层内优先覆盖不同复杂度/错误标签。相同输入、配置和代码得到相同案例顺序，`include_ids` 可强制纳入指定案例并去重。

### 3.3 可视化

每个案例同时展示：

1. 原始裁剪表格图片；
2. Ground Truth 渲染表格；
3. TATR 预测恢复表格；
4. 样本指标、结构统计和候选错误标签；
5. 经转义的 GT/预测原始 HTML。

单元格颜色表示锚点坐标下的启发式比较：完全一致、仅文本不同、结构/span 不同或单侧存在。报告支持按分数层、错误标签、复杂度和案例 ID 筛选。真值与预测只通过白名单表格结构重新生成，不能向页面注入任意脚本。

## 4. 服务器启动命令

在服务器项目根目录、代码分支已同步后运行：

```bash
cd /data01/public/zhengguojie/paper
.venvs/eval312/bin/python scripts/build_table_case_report.py \
  --config configs/evaluation/tatr-cropped-val-case-report.yaml
```

脚本自动创建：

```text
outputs/analysis/table-case-reports/<UTC>-tatr-cropped-case-report/
├── index.html
├── cases.json
└── assets/images/                 # 仅复制抽中的约 60 张图
```

目标目录若已存在，脚本立即失败，不覆盖旧报告。运行过程中每完成 100 个样本输出一次 JSON 进度；不需要 GPU，不重新执行模型推理。运行时主要由 13,384 次逐样本 GriTS 计算决定，当前尚无该工具的服务器实测耗时证据，因此不预先承诺完成时间。

## 5. 验证证据

本地 Python 3.12 临时测试环境中：

- 原仓库基线：88 项测试通过；
- 新增案例分析、静态报告、CLI 与既有评分相关回归：29 项测试通过；
- 本功能新增/修改 Python 文件 Ruff 通过；
- 全仓 Ruff 仍有 15 个既有问题，位于旧 `scripts/evaluate_html_exact.py` 和 `scripts/download_models.py`，本功能没有修改这些文件。

正式同步前仍需重新运行完整 pytest、功能文件 Ruff 和 `git diff --check`。服务器实际报告尚未生成，因此本记录不包含案例分布、错误比例或典型案例结论。

## 6. 结论边界与后续

- 本报告分析 Cropped Tables 页内单表恢复，不是跨页表格恢复结果。
- 自动标签只能用于组织抽样和提出假设，正式研究结论需人工查看原图、GT 和预测三栏后形成。
- 第一轮应从 60 例中筛选 12–20 个代表性案例，区分额外行列、列过分割、多级表头、span、文本归位以及空预测。
- 根据人工核验结果再设计 oracle 行数、列数、表头、span 和文字归属消融；不得先假设单一错误类型是主要瓶颈。
