# TATR 表格案例分析可视化设计

## 1. 目标

为一次完整的 PubTables-v2 表格恢复实验生成可复核的案例分析报告。工具读取冻结的输入清单、预测 JSONL、真值目录和原始图像目录，对全量样本计算样本级诊断统计，再确定性分层抽取约 60 个案例，输出同时展示原图、Ground Truth 和预测结果的静态 HTML。

第一版以 TATR-v1.1-Pub 在 PubTables-v2 `Cropped Tables/val` 上的修正后全量结果为验收对象，但接口不得写死模型名称或 run ID。后续符合相同 `PredictionRecord` 契约的 dots.ocr Cropped Tables 结果可以直接复用；Full Documents 因一页可能包含多表，需在后续单独设计匹配与展示适配。

## 2. 科研边界

- 报告分析的是裁剪单表的页内结构与内容恢复，不得表述为跨页表格恢复结果。
- 全量统计与抽样只在同一个 manifest、prediction、truth 和 collection 协议内进行，不自动混合历史实验。
- 自动错误类型是诊断线索，不是模型错误原因的最终结论。行或列整体偏移会造成级联差异，必须结合原图人工复核典型案例。
- 第一版报告 `GriTS-Top`、`GriTS-Con`、拓扑/内容 grid exact，并展示行列、表头和 span 描述；不伪造 GriTS 不提供的单元格级最优对齐解释。

## 3. 输入与安全

命令接受一个 YAML 配置，配置中至少包含：

- `manifest`：冻结的图片输入 JSONL；
- `predictions`：一个或多个符合 `PredictionRecord` 的 JSONL；
- `truth_dir`：PubTables-v2 表格真值目录；
- `images_dir`：manifest 中 `relative_path` 对应的图像根目录；
- `collection`：第一版仅允许 `cropped_tables`；
- `output_dir`、`sample_size` 和 `seed`。

所有输入只读。输出必须位于一个不存在的新目录；若目标已存在则立即失败，禁止覆盖已有报告。工具不修改数据、预测、日志或模型，不使用 GPU，也不重新执行模型推理。

## 4. 全量样本诊断

每个 manifest 单元必须得到一条诊断记录。工具复用固定 GriTS 实现，逐样本计算：

- `GriTS-Top`、`GriTS-Con`；
- `Acc-Top`、`Acc-Con`；
- 推理状态以及是否为空预测；
- GT/预测的行数、列数、单元格数、表头行数、表头单元格数；
- `rowspan`、`colspan` 和跨越面积大于 1 的单元格数量；
- 基于锚点坐标、span 和规范化文本的结构/内容差异摘要。

候选错误标签至少包括：`inference_error`、`empty_prediction`、`row_count_mismatch`、`column_count_mismatch`、`header_mismatch`、`span_mismatch`、`text_mismatch` 和 `mixed`。复杂度标签至少包括 `long`、`wide`、`multi_level_header` 和 `spanning`；长表、宽表阈值由当前实验 GT 行列数的 90% 分位数确定，并写入报告元数据。

## 5. 分层抽样

按每个样本的分数和状态划分五个主层：

1. `exact`：拓扑和内容均完全匹配；
2. `high_non_exact`：非完全匹配且 `GriTS-Top >= 0.9`；
3. `medium`：`0.6 <= GriTS-Top < 0.9`；
4. `low`：`0 < GriTS-Top < 0.6`；
5. `zero_or_empty`：零分、空预测或推理失败。

默认总量为 60，尽量在主层间均衡分配。层内优先覆盖不同复杂度和错误标签，再使用固定 seed 的稳定哈希顺序补足。相同输入、配置和代码必须得到相同的样本 ID 顺序。用户可通过配置增减样本数，并通过 `include_ids` 强制加入指定案例；强制案例计入总量并去重。

## 6. HTML 报告

报告是无 CDN、无服务端依赖的静态目录，至少包含：

- `index.html`：总体摘要、筛选器和案例卡片；
- `cases.json`：全量诊断记录、抽样选择和运行元数据；
- `assets/`：报告使用的样式和抽样图像副本。

页面顶部展示输入覆盖、分数区间、错误标签和复杂度分布。案例卡片采用三栏布局：原始裁剪图、GT 渲染表、预测渲染表；窄屏自动改为纵向布局。宽表支持横向滚动，原图可点击放大，原始 HTML 可折叠查看。

GT 与预测表均由解析后的允许标签重新构造，不直接注入任意 HTML。单元格按同一锚点的 span 和文本比较着色：完全一致为绿色、拓扑一致但文本不同为黄色、span/结构不一致为红色、单侧存在为灰红色。颜色仅表示坐标启发式差异，页面中必须显示该限制。

图像复制到新报告的 `assets/images/`，不修改原始图像。HTML 使用相对路径，使报告目录可以整体移动或通过静态文件服务器打开。

## 7. 代码结构

- `src/cptla/evaluation/case_analysis.py`：数据模型、逐样本指标、结构描述、标签和确定性抽样；
- `src/cptla/evaluation/case_report.py`：安全表格渲染、HTML/JSON 报告生成和图像复制；
- `scripts/build_table_case_report.py`：YAML 配置加载、输入验证和一条命令入口；
- `configs/evaluation/tatr-cropped-val-case-report.yaml`：当前服务器 TATR run 的可复现配置；
- `tests/evaluation/test_case_analysis.py`：评分、标签、分层抽样和确定性测试；
- `tests/evaluation/test_case_report.py`：HTML 安全、三栏内容、相对资源和拒绝覆盖测试。

不引入 Web 框架或前端构建工具。使用 Python 标准库、现有 `PyYAML`、Pydantic 和固定 GriTS 依赖。

## 8. 验收标准

1. 一条配置驱动命令可以生成完整报告，且不使用 GPU或重新推理。
2. 全量诊断记录数与 manifest 单元数一致，缺失、额外和重复输入会明确失败。
3. 相同 seed 重复运行得到相同抽样 ID；默认约 60 个案例覆盖五个分数层和可获得的复杂度类型。
4. 每个案例同时显示原始图片、GT 和预测，支持筛选、横向滚动和图片放大。
5. HTML 不执行真值或预测中夹带的脚本；输出目录已存在时拒绝覆盖。
6. 单元测试、项目全量测试、Ruff 和 `git diff --check` 通过。
7. 当前 TATR 全量结果在服务器新时间戳目录成功生成报告，并在进度索引及实验记录中留下输入、命令、输出路径、覆盖和已知限制。
