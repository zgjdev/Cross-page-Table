# 两个基线模型完整验证设计

日期：2026-09-21  
状态：待用户最终审阅  
适用项目：PubTables-v2 文档级跨页表格恢复

## 1. 目标

建立两条可审计、可恢复、不可混淆输入条件的 validation 基线：

1. 在 PubTables-v2 `Cropped Tables/val` 上完成 TATR-v1.1-Pub + Direct Text 的正式评测；
2. 在同一 `Cropped Tables/val` 上完成 dots.ocr image-only 评测，用于同任务但不同输入条件的对照；
3. 在 PubTables-v2 `Full Documents/val` 的全部页面上完成 dots.ocr image-only 未合并评测；
4. 保存从模型、数据、命令、环境、预测到指标的完整证据链，形成可用于导师汇报的阶段基线表。

本阶段只使用 validation。test split 不用于调试、提示词选择、阈值选择、规则调整或模型选择。

## 2. 非目标

本阶段不包含：

- 大规模模型训练或微调；
- 自行实现并命名为官方 TATR-v1.2、POTATR 或 continuation ViT；
- 使用官方 continuation 真值作为正式预测输入；
- 将 PDF-text-assisted 与 image-only 分数合并为单一排行榜；
- 覆盖或删除已有 `data/`、`artifacts/`、`outputs/`、`logs/`、模型或环境；
- 在 validation 流程冻结前运行 test split；
- 把跨页合并结果纳入本阶段的“两个模型完成”验收。跨页合并依赖 continuation 基线，后续单独设计。

## 3. 数据范围

### 3.1 已有数据

服务器已有固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903` 的 PubTables-v2 `Full Documents` train、val、test。`Full Documents/val` 包含 935 篇文档和 13,871 页。

### 3.2 需要补充的数据

只下载并解压 PubTables-v2 固定 revision 的 `Cropped Tables/val`：

- images；
- tables；
- words；
- xml annotations。

归档、解压数据和实验输出必须分目录保存。下载前记录官方文件名、revision、字节数和可获得的校验信息；不得原地修改归档或解压内容。

### 3.3 独立评测单位

- Cropped Tables：每张裁剪表格是模型输入；集合评分按官方评测器的表格集合匹配定义聚合；
- Full Documents：每篇文档是集合匹配单位，推理必须覆盖该文档的全部页面，不能借助真值预筛选含表页。

## 4. 评测矩阵

| 实验 | 数据 | 输入条件 | 输出 | 角色 |
|---|---|---|---|---|
| TATR-v1.1-Pub | Cropped Tables/val | 表格图像 + PDF Direct Text | 表格对象、单元格和 HTML | PDF-text-assisted 可复现结构基线 |
| dots.ocr | Cropped Tables/val | 表格图像 | 布局 JSON 中的 table HTML | image-only 同任务对照 |
| dots.ocr | Full Documents/val 全部页面 | 完整页面图像 | 按文档聚合的 table HTML 集合 | image-only 文档级未合并基线 |

TATR-v1.1-Pub 不能替代 TATR-v1.2-Pub。正式表格必须明确标注模型版本、训练来源和输入文字条件。

## 5. 组件设计

### 5.1 统一运行清单

每个实验保存机器可读的 run manifest，至少包含：

- run ID 与 UTC 时间；
- Git commit；
- 数据集名称、split、固定 revision 和输入样本清单哈希；
- 模型名称、repo ID 和 resolved revision；
- Python、PyTorch、Transformers、CUDA、GriTS 版本或源码 commit；
- GPU 型号与可见设备；
- 完整命令、配置、随机种子；
- 预测、日志和指标路径；
- 已完成、失败、跳过、重复样本数量。

### 5.2 TATR 评测入口

新增独立的 TATR validation 入口，不再使用临时内联脚本。数据流为：

```text
Cropped table image + corresponding PDF words
    -> TATR-v1.1 structure objects
    -> official/project-pinned post-processing
    -> cells and canonical HTML
    -> per-table prediction record
    -> GriTS/Acc evaluator
```

预测键必须使用与真值一致的稳定 table ID，禁止使用完整图片路径充当 table ID。加载、预处理、对象阈值和文字归属规则必须写入配置或 manifest。

### 5.3 dots.ocr 评测入口

沿用可恢复 JSONL，但补充严格输入清单与运行元数据：

```text
image manifest
    -> deterministic dots.ocr generation
    -> raw JSONL with one terminal record per image
    -> layout parsing and table HTML validation
    -> table predictions grouped by table/document ID
    -> GriTS/Acc evaluator
```

Full Documents 输入清单必须由 `val/images/*.jpg` 全量生成，不得读取 tables 或 XML 来筛选页面。Cropped Tables 清单则使用全部 val 表格图像。

### 5.4 评分器

评分器必须：

- 使用项目固定的 GriTS 源码 revision；
- 将缺失预测计为 false negative；
- 将额外预测计为 false positive；
- 显式统计无法解析的布局、非法 table HTML、推理异常和重复页面；
- 拒绝输入覆盖不完整却声明 `full_validation`；
- 支持仅重算指标，不重新推理；
- 保存原始完整指标 JSON 和失败样本索引。

## 6. 测试策略

所有代码修改采用测试先行。

### 6.1 单元测试

至少覆盖：

- table ID 从文件名稳定解析；
- 完整输入清单与预测覆盖集合一致；
- 缺失、重复和额外预测被正确报告；
- 完全正确、空预测、额外假阳性和多表匹配的指标行为；
- 合法与非法 HTML；
- dots.ocr layout JSON 直接解析和修复解析；
- TATR 图片坐标与 word bbox 坐标一致性；
- run manifest 必填字段验证。

### 6.2 Smoke test

每个新入口先运行固定的小型 validation 子集：

- TATR：普通表、长表、宽表、含合并单元格表；
- dots.ocr Cropped：同一组表格图像；
- dots.ocr Full Documents：至少一篇含跨页表的完整文档，包括无表页面。

smoke 必须验证输出覆盖、可解析率、真值关联、耗时和显存，而不是只确认进程退出码。

### 6.3 完整 validation

只有 smoke 验收通过后才启动完整 validation。完整运行结束后，重新从预测文件离线评分一次，结果必须与运行结束时的评分一致。

## 7. 服务器执行与安全

- 代码先在本地修改、测试和提交，再同步到 `/data01/public/zhengguojie/paper`；
- 同步排除 `data/`、`artifacts/`、`outputs/`、`logs/`、`checkpoints/` 和 `.venvs/`；
- 下载只新增 Cropped Tables val 归档和解压目录，不修改已有 Full Documents；
- 所有新实验使用新的 UTC 时间戳目录；
- GPU 任务前查询显存和进程，不终止其他用户任务；
- dots.ocr 按互斥清单分片，每个分片可恢复；
- 只有显存满足已验证 smoke 峰值并保留安全余量的 GPU 才能使用；
- 不读取或修改服务器项目根目录之外的文件；项目外旧 conda 环境不作为正式依赖；
- 网络、显存或环境失败时保留日志和已完成预测，不删除后重跑。

## 8. 输出布局

新运行采用：

```text
artifacts/run-manifests/<run-id>.json
artifacts/input-manifests/<run-id>.txt
outputs/baselines/<model>/<revision>/<run-id>/
├── predictions/
├── metrics/
└── failures/
logs/baselines/<model>/<run-id>/
```

最终汇总表至少包含：

- collection 与 split；
- model revision；
- input track；
- 输入样本数与覆盖率；
- `Acc-Top`、`Acc-Con`、`GriTS-Top`、`GriTS-Con`；
- 可解析率、非法 HTML 数量、推理失败数量；
- 总耗时和每样本耗时分布；
- 与公开论文数字的可比性说明。

如固定官方实现支持 TEDS，则同时报告；否则标记为本阶段未实现，不使用非等价近似值冒充。

## 9. 错误处理与停止条件

满足任一条件时暂停完整运行并保留现场：

- 输入清单与数据文件不一致；
- 真值关联不是 100%；
- smoke 中出现未解释的系统性 HTML/JSON 解析失败；
- 指标单元测试与官方参考行为不一致；
- GPU 显存不足或出现其他用户资源冲突；
- 数据 revision、模型 revision 或评测源码 revision 无法固定；
- 预测恢复逻辑产生重复或覆盖记录。

单个样本的可解释推理失败不终止整批运行，但必须写入失败记录并在指标中按预定义规则处理。

## 10. 验收条件

本阶段完成必须同时满足：

1. TATR-v1.1-Pub 覆盖全部 Cropped Tables validation 输入，真值关联为 100%；
2. dots.ocr 覆盖全部 Cropped Tables validation 输入；
3. dots.ocr 覆盖 Full Documents validation 的全部 13,871 个页面，而非仅含表页；
4. 所有指标可由保存的预测文件离线重复计算；
5. 输入覆盖、失败、重复和非法输出均有显式计数；
6. 运行 manifest、日志、预测和指标路径完整；
7. PDF-text-assisted 与 image-only 分开报告；
8. test split 未用于任何开发决策；
9. 形成中文阶段结果摘要，区分项目实测、论文报告和待核验结论。

## 11. 后续阶段

完成本设计后，再单独设计：

1. 官方 continuation 关系样本构建与泄漏检查；
2. 可复现 continuation 分类基线；
3. 直接纵向拼接；
4. 列对应、重复表头和拆分行派生标签；
5. 对齐感知约束重建及跨页子集评测。
