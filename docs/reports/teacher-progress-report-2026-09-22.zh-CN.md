# 文档级跨页表格恢复研究阶段进展汇报

日期：2026-09-22

研究主题：基于 PubTables-v2 的文档级跨页表格恢复

汇报性质：阶段性进展与下一步方案讨论

## 1. 执行摘要

本项目面向完整文档中的跨页表格恢复，最终目标不是单纯识别一张裁剪表格，而是从多页文档中定位属于同一逻辑表格的页面片段，恢复跨页列对应、重复表头、拆分行或拆分单元格，并输出结构和内容一致的完整逻辑表格。

当前工作主要完成了数据、评测协议和基础模型证据链的建立。项目已固定 PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，并完成 TATR-v1.1-Pub 在 `Cropped Tables/val` 全部 13,384 张长表和宽表上的正式评测。该模型取得 `GriTS-Top=0.7429`、`GriTS-Con=0.7168`，但严格完全匹配指标只有 `Acc-Top=0.0164`、`Acc-Con=0.0069`。这说明模型能够恢复较多局部结构和内容，但距离整张表格完全正确仍有很大差距。

接管项目之前还完成过一次 dots.ocr 的 Full Documents validation 运行，覆盖 935 个文档中的 3,522 个真值表格页，得到 `GriTS-Con=0.6216`、`Acc-Con=0.1380`。重新审计发现，该运行恰好只包含真值表格所在页，未覆盖 validation 的全部 13,871 页，并且没有执行跨页合并。因此这组结果只能作为“真值表格页筛选、未合并”的历史基线，不能表述为严格的 Full Documents 端到端结果。

与课题最相关的 TATR-v1.2/POTATR 结果已经在论文中报告，但截至 2026-09-22，没有核验到官方发布的对应 checkpoint 和完整复现制品。PubTables-v2 与 POTATR 论文目前仍表述代码和模型将发布；Microsoft 官方 TATR 仓库列出的公开预训练权重仍是 TATR-v1.0/v1.1 系列。因此本阶段先使用公开可获得的 TATR-v1.1-Pub 和 dots.ocr 建立可复现下界，并把论文结果作为外部参照，而不把尚未复现的数字写成项目结果。

当前最值得讨论的不是继续无差别增加 OCR 模型，而是研究页面片段之间的显式结构关系：列对应、重复表头、跨页拆分行/单元格和约束重建。希望与导师重点讨论三项决策：是否将研究主线正式收敛到跨页结构对齐；是否投入多卡资源补齐耗时较长的 dots.ocr 全量基线；以及对尚未开放权重的 TATR-v1.2/POTATR，是等待官方发布还是自行训练近似基线。

## 2. 研究问题与任务边界

### 2.1 核心研究问题

项目研究问题可以概括为：

> 在页面级表格抽取存在结构与内容误差的情况下，如何利用几何、文本、表头和上下文关系，对跨页表格片段进行可靠关联、对齐和约束重建，从而提高完整逻辑表格的严格正确率？

该问题包含四个相互关联但不能混淆的层次：

1. **页面级表格抽取**：检测页面中的表格，恢复行、列、单元格、表头和文本；
2. **continuation 判断**：判断相邻页面或同页不同栏中的两个表格片段是否属于同一逻辑表格；
3. **结构对齐**：确定跨片段的列对应、重复表头、拆分行和拆分单元格关系；
4. **约束重建**：在存在上游识别误差时，生成结构有效且内容一致的最终逻辑表格。

目前已完成的 TATR 和 dots.ocr 工作主要属于第一层。它们是后续跨页方法的输入组件和比较基线，而不是课题最终解决方案。

### 2.2 PubTables-v2 的三个 collection

PubTables-v2 包含三个互补的任务设置：

| Collection | 输入单位 | 主要用途 | 与本项目关系 |
| --- | --- | --- | --- |
| Cropped Tables | 紧密裁剪的单张表格图像 | 长表、宽表的结构与内容恢复 | 检验页面解析器在困难表格上的能力 |
| Single Pages | 包含一张或多张表格的完整页面 | 页面级检测与表格提取 | 为完整页面解析器提供训练和评测 |
| Full Documents | 文档全部页面 | 多表、跨页表和同页跨栏表恢复 | 本项目最终主基准 |

官方数据和任务说明见 [PubTables-v2 论文](https://arxiv.org/abs/2512.10888)及[官方 Hugging Face 数据仓库](https://huggingface.co/datasets/kensho/PubTables-v2)。

## 3. 数据、模型与评测协议

### 3.1 数据版本与当前范围

- PubTables-v2 固定 revision：`aa575e798cb00a296925e2086addb3e3fd9a1903`
- 当前开发划分：validation
- Cropped Tables validation：13,384 张表格图像，并有对应 table、word 和 XML 标注
- Full Documents validation：935 个文档，共 13,871 页
- test split：不用于提示词、规则、阈值或模型选择，只保留给最终评估

### 3.2 输入赛道

本项目严格区分两条输入条件：

- **PDF-text-assisted**：结构模型使用页面/表格图像，同时使用 PDF 原生文字和坐标。TATR-v1.1-Pub 属于该赛道。
- **image-only**：模型只接收图像并自行生成文本和结构。dots.ocr 属于该赛道。

两条赛道的文本信息条件不同，因此不能把分数直接解释为模型架构的公平优劣排名。PDF 原生文字通常比 OCR 或视觉生成文本更准确。

### 3.3 指标含义

| 指标 | 含义 | 解读边界 |
| --- | --- | --- |
| GriTS-Top | 表格拓扑的软相似度 | 可部分得分，不代表整表完全正确 |
| GriTS-Con | 表格结构与内容的软相似度 | 对局部正确有奖励，不等于完全正确率 |
| Acc-Top | 拓扑严格完全匹配 | 任一关键结构错误都可能使该表不计为完全正确 |
| Acc-Con | 结构和内容严格完全匹配 | 最严格，文本或结构任一错误都可能导致失败 |

因此，`GriTS-Con=0.7168` 不能解释为 71.68% 的表格完全正确；严格内容完全匹配应查看 `Acc-Con`。

## 4. 已完成工作

### 4.1 数据与评测基础设施

已完成：

1. PubTables-v2 Full Documents train/validation/test 的下载、校验和解压；
2. Cropped Tables validation 四类文件的直接服务器下载和关联审计；
3. TATR 与 dots.ocr 的固定输入清单、可恢复预测 JSONL、离线评分和覆盖检查；
4. missing、extra、duplicate、推理异常和非法 HTML 的显式统计；
5. TATR、dots.ocr Cropped 和 dots.ocr Full Documents 三条 smoke 流程；
6. TATR Cropped Tables validation 全量推理和两次离线复评；
7. 接管前 dots.ocr Full Documents 历史结果的协议审计。

### 4.2 当前状态总表

| 实验 | 状态 | 覆盖 | 输入赛道 | 是否可作为正式全量结果 |
| --- | --- | ---: | --- | --- |
| TATR-v1.1-Pub / Cropped smoke | 已完成 | 4/4 | PDF-text-assisted | 否，仅流程验证 |
| TATR-v1.1-Pub / Cropped full validation | 已完成 | 13,384/13,384 | PDF-text-assisted | 是，但需同时报告65个失败 |
| dots.ocr / Cropped smoke | 已完成 | 4/4 | image-only | 否，仅困难样本 smoke |
| dots.ocr / Cropped full validation | 暂缓 | 0/13,384 | image-only | 否 |
| dots.ocr / Full Documents smoke | 已完成 | 1文档、3/3页 | image-only | 否，仅流程验证 |
| dots.ocr / Full Documents 历史运行 | 已完成但协议不严格 | 935文档、3,522/13,871页 | image-only | 否，使用真值表格页筛选 |
| dots.ocr / Full Documents strict full | 尚未启动 | 0/13,871 | image-only | 否 |

## 5. TATR-v1.1-Pub 全量实验结果

### 5.1 实验设置

- 模型：TATR-v1.1-Pub
- 模型 revision：`372e205368a9b7bd1b9fdcf906c1350999d48939`
- 数据：PubTables-v2 `Cropped Tables/val`
- 输入：裁剪表格图像与 PDF Direct Text
- 分析单位：每张裁剪表格
- 预期输入：13,384
- 实际预测记录：13,384
- 覆盖检查：missing=0、extra=0、duplicate=0
- 推理 run ID：`20260921T082639Z-tatr-cropped-val-full`
- 评分 run ID：`20260921T163325Z-tatr-cropped-val-offline-score-bg`

### 5.2 正式结果

| 指标 | 项目实测结果 |
| --- | ---: |
| GriTS-Top | 0.7429088739 |
| GriTS-Con | 0.7167619958 |
| Acc-Top | 0.0163628213 |
| Acc-Con | 0.0068738793 |
| Topology precision | 0.6422517386 |
| Topology recall | 0.8809809275 |
| Content precision | 0.6196475155 |
| Content recall | 0.8499745662 |
| 推理失败 | 65/13,384，约0.49% |
| 生成预测表 | 13,317 |
| 非法 table HTML | 0 |

两次离线评分的 metrics SHA-256 均为：

`95a4388b5387cb63e09538716447ec2e51c9f168314506fd4735556086bbffb8`

两次 failures 文件 SHA-256 均为：

`8db22441ba3f0d7d088931ceb3270b010c3a2e160ee93b330c12bd07b05f15a7`

这说明保存的预测可以稳定复评，评分结果没有因重复运行而漂移。

### 5.3 结果如何解释

可以得出三个层次的结论：

1. **已观察事实**：GriTS 约为0.72–0.74，说明大量局部行列、单元格和内容仍与真值相似；但 Acc 只有0.69%–1.64%，说明整表严格完全正确非常困难。
2. **已观察事实**：precision 明显低于 recall。模型倾向于覆盖大部分真实结构，但同时产生更多额外或不准确结构。
3. **待误差分析验证的推断**：额外行列、复杂表头、合并单元格、结构碎片化和 PDF text 归属可能是 precision 与 exact match 较低的重要原因。目前不能在没有样本分类证据的情况下，把其中某一项宣称为唯一主因。

## 6. 为什么 TATR-v1.1-Pub 表现不理想

### 6.1 训练分布与测试分布存在差异

TATR-v1.1-Pub 使用 PubTables-1M 训练，而 PubTables-v2 Cropped Tables 专门保留至少30行的长表或至少12列的宽表。后者不是普通表格的随机样本，而是针对旧模型困难区域构建的集合。因此当前结果既反映模型能力，也反映明显的域与难度迁移。

### 6.2 严格指标对局部错误极其敏感

长表和宽表包含更多单元格，也提供更多发生错误的机会。即使绝大多数单元格正确，只要列划分、rowspan/colspan、表头层级或个别内容不完全一致，`Acc-Top` 或 `Acc-Con` 就可能失败。这解释了“GriTS 尚可、Acc 很低”的表面矛盾。

### 6.3 当前模型不是 PubTables-v2 定向版本

项目使用的是可公开获得的 TATR-v1.1-Pub，而不是论文中针对 PubTables-v2 长表和宽表继续训练的版本。因此该实验更适合解释为“公开旧模型在新困难分布上的可复现下界”，不应将其等同于论文中更新版本的能力。

### 6.4 TATR 本身不解决跨页关系

TATR-v1.1-Pub 的输入是单张裁剪表格。它不判断两个页面片段是否续接，也不显式预测跨页列对应、重复表头和拆分行。因此，即使单页结构准确率进一步提高，仍然需要独立的跨页关系与重建模块。

### 6.5 尚有65个推理失败

65个失败约占0.49%，已作为空预测计入正式指标。当前决定是不让它们阻塞下一阶段，但这不等于忽略其科研意义。后续误差分析必须判断这些失败是否集中在极长表、极宽表、异常尺寸或特殊标注上。

## 7. dots.ocr 当前结果及其边界

### 7.1 新严格协议 smoke

| 设置 | 覆盖 | GriTS-Top | GriTS-Con | Acc-Top | Acc-Con | 说明 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Cropped Tables smoke | 4/4 | 0.68224 | 0.40857 | 0.25 | 0.25 | 特意选择普通、长、宽、span困难样本；有1个runner warning |
| Full Documents smoke | 1文档、3/3页 | 0.81967 | 0.81929 | 0 | 0 | 包含无表页；未做跨页合并 |

这些指标只能证明流程可运行，样本量太小，不能用于论文比较或总体性能结论。

### 7.2 接管前历史 Full Documents 结果

| 项目 | 历史结果 |
| --- | ---: |
| documents scored | 935 |
| pages seen | 3,522 |
| validation全部页面 | 13,871 |
| 未推理页面 | 10,349 |
| predicted tables | 2,928 |
| invalid table HTML | 838 |
| GriTS-Top | 0.6563578710 |
| GriTS-Con | 0.6216124466 |
| Acc-Top | 0.2759953614 |
| Acc-Con | 0.1379976807 |

审计确认，3,522个历史预测页面与真值 tables 标注中的表格所在页集合完全相同。这意味着输入选择利用了真值信息，排除了无表页和其他页面，降低了产生页面级假阳性的机会。

此外，旧评分代码只是把各页检测出的合法 table HTML 按文档分组，并没有执行 continuation 分类或跨页 HTML 合并。因此这组结果不能解释为跨页恢复性能。

### 7.3 为什么暂缓 dots.ocr Cropped 全量

当前4个困难样本共耗时354.7秒，机械外推单张 A100 80GB 完成13,384张约需330小时，即约13.7天。由于该 smoke 故意选择困难样本，参考其他页面推理速度后的规划区间约为6.5–14天。这个区间仅用于容量规划，不是可靠完成时间。

在尚未确定 dots.ocr 全量结果是否会改变论文主线之前，立即投入一到两周单卡时间的边际收益有限。因此当前选择先暂停该任务，并把是否多卡补齐作为导师讨论事项。

## 8. 为什么没有测试其他模型

未测模型必须按可获得性和研究角色分类，不能统一解释为“没有开源”。

### 8.1 最相关但尚无已核验官方制品

| 模型 | 相关性 | 截至2026-09-22的状态 | 当前处理 |
| --- | --- | --- | --- |
| TATR-v1.2-Pub | 针对 PubTables-v2 长表/宽表继续训练，是 Cropped Tables 最直接比较对象 | 没有在官方 TATR 权重列表中核验到对应 checkpoint | 引用论文报告值，不声称已复现；等待发布或自行继续训练 |
| POTATR | 29M参数页面级 image-to-graph 模型，是 Single Pages 和文档级组合流水线的重要基线 | 论文仍写明 code and models will be released | 引用论文结果作为外部比较，不把近似实现冒充官方模型 |
| PubTables-v2 continuation ViT | 与跨页续接直接相关 | 没有核验到可直接使用的官方 checkpoint 与完整复现包 | 可使用公开页面对标签自行训练，但必须标注为项目复现版本 |

Microsoft [Table Transformer 官方仓库](https://github.com/microsoft/table-transformer)目前列出的预训练权重为 TATR-v1.0 和 TATR-v1.1 系列，并说明公开预训练权重面向 PubTables-1M。PubTables-v2 [官方论文](https://arxiv.org/abs/2512.10888)和 [POTATR 论文](https://arxiv.org/abs/2606.09788)截至核验日期仍使用将来时描述代码与模型发布。

因此，对这三项最准确的表述是：

> 论文和结果已经公开，但与论文完全对应的官方 checkpoint 或完整复现制品尚未核验到，因此当前无法进行可信的同版本复现。

### 8.2 商业 API 模型

Claude、Gemini、GPT 等不是开放权重模型，但并非完全不可测试。它们通常可以通过商业 API 调用。当前没有优先进行本地复测，主要因为：

1. 全文档、多页面推理成本较高；
2. API 模型版本和默认行为可能变化；
3. 无法冻结底层权重，长期复现性弱于本地 checkpoint；
4. PubTables-v2 论文已提供同一官方评测协议下的结果，可暂作性能上界或外部参照。

如果导师认为商业 MLLM 对论文定位必不可少，可以在方法和评测协议冻结后，用固定 API 版本、保存完整请求和响应的方式补测。

### 8.3 其他已有开放权重的 VLM

Qwen、GraniteDocling、SmolDocling、DeepSeek-OCR 等部分模型已有公开权重。没有全部测试它们，不是因为拿不到参数，而是因为当前阶段先选择：

- 一个经典、轻量、结构显式的检测式模型 TATR；
- 一个开源、端到端生成 HTML 的文档解析模型 dots.ocr。

这两类模型已经代表两种主要范式。后续是否扩展更多 VLM，应取决于它们能否回答新的科学问题，而不是单纯增加模型数量。

## 9. 与公开论文结果的关系

以下数字均为论文报告值，不是本项目复现值：

| 方法 | 任务与输入 | 论文报告的代表性结果 | 用途 |
| --- | --- | ---: | --- |
| PubTables-v2定向 TATR + Direct Text | Cropped Tables | `Acc-Con=0.6831` | 说明定向训练与高质量文字输入可以显著提高严格正确率 |
| PubTables-v2定向 TATR + docTR OCR | Cropped Tables | `Acc-Con=0.0191` | 说明 OCR/文字质量会显著限制内容完全匹配 |
| POTATR + Direct Text | Single Pages | `GriTS-Con=0.964`，`Acc-Con=0.6454` | 强页面级抽取外部参照 |
| POTATR + continuation + merging | Full Documents | `GriTS-Con=0.8269`，`Acc-Con=0.2176` | 显式页面抽取加外部合并的重要参照 |
| Claude Opus 4.6 | Full Documents | `Acc-Con=0.2452` | 商业全文档 MLLM 外部上界之一 |

这些结果不能与项目 TATR-v1.1 分数直接排名，因为模型版本、数据 context 和文字输入条件不同。它们的作用是说明研究难度、可达到的性能区间和可复现基线缺口。

## 10. 当前结果暴露出的研究机会

### 10.1 continuation 判断不是全部问题

PubTables-v2 论文报告 continuation 分类已经接近饱和，但直接纵向拼接仍不能保证严格整表正确。这说明“是否续接”只是必要条件，不是充分条件。

### 10.2 软相似度提升不等于严格正确率提升

公开结果和项目实测都显示，GriTS/TEDS 可以在合并后提高，但 `Acc-Con` 仍然较低。仅仅纵向连接两个 HTML 片段，无法解决列错位、重复表头和拆分行。

### 10.3 论文贡献应聚焦显式跨页结构对齐

一个更有辨识度的研究方向是：将页面片段表示为带空间和文本属性的结构图，显式预测以下关系：

- `continuation-of`：两个片段是否属于同一逻辑表；
- `column-aligned-with`：跨片段列对应；
- `repeated-header-of`：后续页面表头与原表头的同一性；
- `split-row-of`：页面末行与下一页首行是否为同一逻辑行；
- `split-cell-of`：跨页单元格是否需要合并；
- `same-logical-table`：多片段的全局归属。

随后通过结构约束解码，保证列数、行顺序、span和表头层级尽可能一致。该方向与现有简单纵向拼接有清晰差异，也直接回应 strict exact match 较低的问题。

## 11. 下一阶段工作方案

### 阶段A：误差分析与证据补全

目标：确认当前 TATR 的主要失败类型，避免仅凭指标猜测。

工作内容：

1. 对65个推理失败逐条分类；
2. 从正确和错误预测中按长表、宽表、spanning cell、复杂表头分层抽样；
3. 统计额外行列、缺失行列、span错误、表头错误和文字归属错误；
4. 补齐 TATR 全量运行的命令、代码 commit 和追溯 manifest；
5. 形成可用于论文错误分析图表的样本清单。

验收条件：每个主要失败结论都有样本数和证据路径，不再使用未经验证的单一原因解释。

### 阶段B：continuation 与直接拼接基线

目标：建立跨页恢复的最低可复现系统。

工作内容：

1. 使用 PubTables-v2 官方页面对标签构建 train/validation 样本；
2. 按 document ID 进行划分和泄漏检查；
3. 建立简单 continuation 分类器或可解释启发式基线；
4. 实现“预测续接且列数一致则纵向拼接”的直接合并基线；
5. 分别评估 oracle continuation 和 predicted continuation。

验收条件：区分 continuation 错误、页面抽取错误和合并错误，不把三者混成一个总分。

### 阶段C：对齐感知的跨页重建

目标：建立论文的核心方法。

工作内容：

1. 构建列、行、表头和单元格的跨页候选关系；
2. 从最终逻辑表和页面片段中派生列对应、重复表头和拆分行弱标签；
3. 对派生标签记录置信度并人工审计；
4. 训练或设计类型化关系预测模块；
5. 使用结构约束完成最终逻辑表解码。

验收条件：相对于直接纵向拼接，在相同页面抽取输入下提高文档级 `Acc-Con`，并通过消融说明各关系类型的贡献。

### 阶段D：完整评测与论文证据

目标：形成可投稿的公平比较和错误分析。

工作内容：

1. 分开报告 `PDF-text-assisted` 与 `image-only`；
2. 在 Full Documents 全部页面上评测，不使用真值筛页；
3. 报告 GriTS、TEDS、Acc、continuation 指标和跨页子集结果；
4. 进行 oracle/predicted、关系类型、约束解码和文字来源消融；
5. validation 完成方案选择后，仅在最终阶段使用 test。

## 12. 希望与导师讨论的决策

### 决策一：研究主线

是否同意把主要贡献定位为“跨页片段之间的类型化结构对齐与约束重建”，而不是重新训练一个通用页面 OCR 或只做 continuation 二分类？

建议：同意。该方向与现有 POTATR/TATR 页面抽取和近饱和 continuation 分类形成清晰互补。

### 决策二：dots.ocr 全量算力投入

是否现在投入多张 GPU 补齐 dots.ocr Cropped 和严格 Full Documents 全量？

建议：暂不作为前置阻塞项。先完成误差分析和简单跨页基线；当方法与评测冻结后，再决定是否用多卡补齐论文基线。

### 决策三：TATR-v1.2/POTATR 的处理

是等待官方权重，还是自行训练近似版本？

建议：持续监控官方发布，同时准备可复现的项目训练方案。若核心方法需要稳定页面对象输入且官方制品仍未发布，再自行训练，并明确命名为项目复现版本。

## 13. 当前阶段可向导师陈述的结论

可以陈述：

1. 已建立固定数据版本、完整覆盖检查和可重复离线评分流程；
2. 已完成 TATR-v1.1-Pub 在 PubTables-v2 Cropped validation 上的全量评测；
3. 当前结果显示局部软相似度尚可，但整表严格正确率很低；
4. 已发现并纠正接管前 dots.ocr Full Documents 结果的协议边界；
5. 最相关的新模型论文结果已公开，但官方权重和完整复现制品尚未核验到；
6. 下一步科学问题应集中于跨页结构对齐和约束重建。

暂时不能陈述：

1. dots.ocr 已经完成严格 Full Documents 全量评测；
2. 当前方法已经实现跨页表格恢复；
3. TATR-v1.1 与论文中的更新 TATR/POTATR 是同一个模型；
4. 所有其他模型都因没有开源而无法测试；
5. 当前结果已经超过公开方法或足以支持最终论文结论。

## 14. 3–5分钟口头汇报稿

老师好，我目前主要在做 PubTables-v2 上的文档级跨页表格恢复。这个任务与普通的单张表格识别不同，它不仅需要识别每一页中的表格，还需要判断不同页面上的片段是否属于同一张表，并处理跨页列对应、重复表头和拆分行，最后恢复完整逻辑表格。

目前我先完成了数据和评测流程的固定。PubTables-v2 使用固定 revision，现阶段只使用 validation，不使用 test 调参。评测中我把 PDF 原生文字辅助和纯图像两种输入条件分开报告，避免不公平比较。

已经完成的主要实验是 TATR-v1.1-Pub 在 Cropped Tables validation 上的全量测试，共13,384张长表和宽表，覆盖完整，没有缺失、额外或重复样本。结果是 GriTS-Top 0.7429、GriTS-Con 0.7168，但严格的 Acc-Top 只有0.0164，Acc-Con只有0.0069。另外有65个推理失败，已经按空预测计入指标。这个结果说明模型能恢复较多局部结构，但很难保证整张长表或宽表完全正确。

接管项目之前还运行过 dots.ocr 的 Full Documents validation。原结果覆盖935个文档、3,522页，GriTS-Con是0.6216，Acc-Con是0.1380。我重新核验后发现，这3,522页恰好都是真值表格所在页，没有覆盖全部13,871页，而且旧代码没有做跨页合并。因此我把它重新界定为历史筛页基线，而不是严格全文档结果。新的严格流程已经通过一个完整三页文档的 smoke，但全量单卡预计需要约6.5到14天，所以目前先暂停，想请老师判断是否值得投入多卡补齐。

没有测试TATR-v1.2和POTATR，主要不是忽略相关工作，而是目前没有核验到官方对应checkpoint和完整复现制品。官方论文仍写代码和模型将发布，Microsoft当前公开的主要是TATR-v1.0和v1.1权重。Claude、Gemini等模型属于另一类，它们可以通过商业API测试，但不是开放权重模型，成本和版本复现也是问题。其他开源VLM可以后续扩展，只是当前阶段先选了TATR和dots.ocr代表两种主要范式。

从现有结果看，我认为下一步不应只继续堆更多OCR模型。更关键的问题是跨页片段之间的显式结构关系，包括列对应、重复表头、拆分行和拆分单元格。我计划先做TATR分层误差分析，然后建立continuation加直接纵向拼接的最小基线，再研究类型化关系图和约束重建，并通过oracle continuation和predicted continuation区分各模块误差。

这次希望重点请老师讨论三件事：第一，是否同意把研究主线收敛到跨页结构对齐和约束重建；第二，是否现在投入多卡补dots.ocr全量；第三，对尚未开放权重的TATR-v1.2和POTATR，是等待官方发布，还是后续自行训练一个明确标注的复现版本。

## 15. 导师可能追问与建议回答

### 问题1：为什么目前只重点测试了 TATR 和 dots.ocr？

回答：这两个模型代表两种不同范式。TATR是轻量、结构显式、可空间定位的检测式模型；dots.ocr是开放权重、端到端生成HTML的文档VLM。当前阶段先用它们打通统一的数据、覆盖和评分流程。增加模型数量只有在能提供新能力对照时才有意义。

### 问题2：为什么没有测试最相关的 TATR-v1.2 和 POTATR？

回答：论文结果已经公开，但截至核验日期没有找到与论文完全对应的官方checkpoint和完整复现制品。官方资料仍写代码和模型将发布。为避免把自行猜测的实现当作官方复现，目前引用论文值作为外部比较，并使用公开TATR-v1.1建立可复现下界。

### 问题3：能否根据论文自己训练 TATR-v1.2 或 POTATR？

回答：可以尝试，但那将是项目复现版本，而不是官方模型。它需要固定训练配置、数据处理、随机种子和验证流程，投入也明显高于直接加载checkpoint。是否值得做应取决于它是否是跨页方法的必要输入，而不是为了追求模型数量。

### 问题4：为什么 GriTS 有0.7，但 Acc 只有约0.007？

回答：GriTS是软相似度，局部行列和单元格正确就可以得到部分分数；Acc-Con要求结构和内容整体完全一致。长表和宽表的单元格多，任一列划分、span、表头或文本错误都可能使整表无法获得exact match。

### 问题5：这是否说明 TATR 完全不能用？

回答：不能这样解释。TATR的recall较高，说明它仍然能恢复大量真实结构，可以作为候选页面解析器和可解释输入。但需要通过误差分析和约束后处理减少额外、错分或碎片化结构，并且必须另加跨页模块。

### 问题6：65个推理失败会不会使结果失效？

回答：65个失败占13,384个输入的约0.49%，并且已经作为空预测计入指标，因此没有人为排除困难样本。它们不会使整批结果无效，但必须保留并进行错误分类，避免失败集中于某类关键样本。

### 问题7：为什么不直接把 dots.ocr 全量跑完再汇报？

回答：当前单卡容量规划约为6.5到14天，而现有历史结果已经暴露出HTML有效性和评测协议问题。先请导师确认研究主线和算力投入，可以避免在方法目标尚未冻结时消耗大量GPU时间。若决定补齐，可使用多GPU互斥分片和断点恢复。

### 问题8：目前的结果是否足以形成论文？

回答：当前结果足以证明问题难度和建立基线证据，但还不足以形成论文贡献。论文需要一个明确的新方法，以及在相同页面抽取输入下相对于直接纵向拼接的改进、消融和错误分析。

### 问题9：预期创新点是什么？

回答：候选创新点是显式建模跨页片段的类型化结构关系，包括列对应、重复表头、拆分行和拆分单元格，并通过约束解码恢复最终逻辑表格。重点不是重复做continuation二分类，而是解释并提高严格文档级恢复指标。

### 问题10：下一步最小可执行实验是什么？

回答：先对TATR错误进行分层分析，同时使用PubTables-v2官方相邻页面对标签建立continuation基线；随后实现直接纵向拼接，并在oracle continuation与predicted continuation两种设置下评测。这样可以最快判断真正瓶颈位于页面抽取、续接还是结构对齐。

### 问题11：为什么不直接使用真值页面片段做跨页研究？

回答：可以使用真值片段建立oracle上界，隔离结构对齐模块能力；但正式端到端结果仍必须使用模型预测，不能用真值筛页或真值关系作为输入。报告时需要把oracle与predicted设置分开。

### 问题12：如何保证不在 validation/test 上过拟合？

回答：所有训练和规则开发按文档划分，页面不能跨split；validation用于选模和消融；test只在方案冻结后进行最终评估。派生标签也必须记录来源、置信度和审计状态。

## 16. 证据与复现路径

### 16.1 项目进度与实验记录

- `docs/research-progress.zh-CN.md`
- `docs/experiments/2026-09-21-two-baseline-smoke.zh-CN.md`
- `docs/experiments/2026-09-22-historical-dots-full-documents-audit.zh-CN.md`
- `docs/superpowers/specs/2026-09-21-two-baseline-complete-validation-design.md`

### 16.2 TATR 正式结果

- predictions：`outputs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/predictions.jsonl`
- inference log：`logs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/inference.log`
- metrics：`outputs/baselines/tatr-v1.1-pub/20260921T163325Z-tatr-cropped-val-offline-score-bg/metrics-1.json`
- repeated metrics：同目录 `metrics-2.json`
- failures：同目录 `failures-1.jsonl` 和 `failures-2.jsonl`
- checksums：同目录 `checksums.sha256`

### 16.3 dots.ocr 历史结果

- predictions：`outputs/baselines/dots-ocr/c0111ce6bc07803dbc267932ffef0ae3a51dc951/validation/predictions-part0.jsonl`
- predictions：同目录 `predictions-part1.jsonl`
- metrics：同目录 `metrics.json`
- logs：`logs/models/dots-ocr-validation-part0.log` 和 `dots-ocr-validation-part1.log`

### 16.4 官方外部来源

1. PubTables-v2 paper: [arXiv:2512.10888](https://arxiv.org/abs/2512.10888)
2. PubTables-v2 dataset: [kensho/PubTables-v2](https://huggingface.co/datasets/kensho/PubTables-v2)
3. Table Transformer official repository: [microsoft/table-transformer](https://github.com/microsoft/table-transformer)
4. POTATR paper: [arXiv:2606.09788](https://arxiv.org/abs/2606.09788)

## 17. 证据标签说明

- **项目实测**：有项目内预测、日志、指标或校验和支持；
- **论文报告**：来自官方论文，但项目尚未复现；
- **推断**：由指标或样本现象支持，但仍需专门实验验证；
- **待核验**：当前缺少足够证据，不作为正式结论。

本报告中的 TATR 全量指标和 dots.ocr 历史指标属于“项目实测”；公开 TATR/POTATR/商业 MLLM 数字属于“论文报告”；关于额外结构、复杂表头等失败原因属于“待误差分析验证的推断”。
