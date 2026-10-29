# OCRFlux完整文档评测封装设计

日期：2026-10-30（Asia/Shanghai）。状态：**设计待审阅，未实现正式runner/adapter，未启动新GPU任务**。目标是在已验收环境上补齐10页train整文档测试、配对评分与断点恢复，达到可开始全量的条件；不是训练新算法或修改现有模型。

## 1. 已确认范围与证据

- PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，image-only。推理输入整篇所有页面，不提供GT文字/表框/续接标签；train开发，val935篇/13,871页正式比较，test不参与开发。
- OCRFlux官方代码commit `c1b315aa4c8309f8dc436a5d90fc4977bcf0d865`，权重revision `e68592278bbc8ab32edf7b65e6e411f1d878ef72`。环境 `.venvs/20261029T162200Z-ocrflux/` 已通过pip check/CLI/渲染/CUDA/三入口最小生成。证据 [环境验收](../../experiments/2026-10-30-ocrflux-runtime-and-smoke-readiness.zh-CN.md)。
- 现有 `ocrflux/inference.py::parse` 包含不安全eval，最终返回document_text/page_texts/fallback_pages但不返回完整来源链；其build_document_text会修改页面列表。不能靠最终Markdown或GT补来源页。官方原源码/安装包保持不变。
- 仓库已有document_run.py的原子发布、清单数字页序和按文档恢复，以及score_cross_page_predictions.py的统一评分契约。复用，避免另造评分公式。

## 2. 可选方案与推荐

1. **推荐：显式、可审计的官方API封装。**调用官方query/prompt/PageResponse/table_matrix2html，记录三阶段原始响应；按固定官方API的阶段/逆向合并顺序执行，替换eval为安全字面量解析，并显式记录节点与边。代码更多，但单测、失败定位、来源链和恢复边界清楚；命名 `OCRFlux-official-API-instrumented`，不冒称字节级原版CLI复现。
2. 原官方parse的AST/运行时插桩。可保留更多内部控制流，但版本耦合强、返回前的原地修改与异常吞没使审计复杂，不推荐本阶段使用。
3. 直接跑CLI，只保存最终Markdown。开发最少，但不能证明跨页表的来源页和失败路径，不满足本项目正式评测条件，不采用。

## 3. 推荐方案的数据流

整篇无文字层PDF → 官方页面query与逐页生成 → 原始JSON和官方页面转换结果 → 冻结的no_merge表集合；同一份页面结果 → 官方相邻页元素续接query → 安全解析索引 → 官方表重建query → 生成merged表集合与可审计来源链 → 两组CPU评分。两组不分别重跑页面识别，GT只进入独立评分步骤。

每个元素以(document_id, 0-based page_number, element_index)标识，不能用HTML内容去重身份。页面结构列表在合并阶段只操作副本，no_merge保持不变；不根据真值修复、规范化或重排HTML。

模型原始响应按请求持久保存，记录stage、document/page/element IDs、输入prompt/参数、文本、finish_reason、token数量、耗时和错误；来源页只从成功表重建事件的有向链合并，保留空尾片段页。三页链按官方逆页序处理，并保存每次重建的实际输入/输出，不能把最后两页拼错顺序。

## 4. 参数与版本边界

基线采用已验证的官方直接API提示模板；temperature=0、max_tokens=8192、seed=0、max_page_retries=0（直接API默认，不套用CLI的8次重试默认）。解析失败记录明确error终态，不静默跳过页面。只在train验证协议，冻结后才跑val，不能通过val GT调参数。

单卡0、tensor_parallel_size=1、bfloat16、max_model_len=16384、max_num_seqs=1、enforce_eager、gpu_memory_utilization=0.20；仅image输入，禁止video请求。对多模态限额的具体运行参数须在train确认并记入manifest，不能在val期间更改。页面query保持官方最长边1024和Poppler72dpi。

正式任务启动前再次检查显存和已有进程，门槛至少30,000MiB空余（覆盖约15.83GiB预算×1.3+8GiB余量）；每次生成前空余低于8,192MiB安全退出。不得杀其他进程；进程退出显式清理自建分布式组。显存快照不冒充独占峰值或未来保证。

## 5. 安全、失败和评分契约

- 检测字符串仅用ast.literal_eval；校验为二维整数索引列表，bool/负数/越界/重复/冲突索引拒绝。限定单次响应大小；原始非法值与拒绝原因保留，不执行表达式。
- 页JSON遵循官方PageResponse及转换逻辑；失败显式保留覆盖。生成达到长度上限、格式无效和表转换异常分别记录，禁止凭GT补内容或HTML。
- 成功且身份无歧义的表重建才构造合并表。重建失败保留原片段并记录失败，不把普通字符串连接当作成功跨页恢复。此失败处理是封装协议，报告与原CLI可能的差异，不宣称算法增益。
- adapter只读保存产物，不调用GPU、不访问GT；输出标准input-manifest.jsonl、两组page-results.jsonl与document-tables.jsonl，以及table-evidence/decisions。页面status、文档ID、连续页序、唯一表ID与来源页范围必须核验；不能证明身份时停止适配并保留失败现场。
- 模型把表漏识别/误识别属于性能结果，不因分数不好改规则；接口/身份/缺页契约失败是阻塞条件。

## 6. 代码边界（后续实现，不是已完成）

- `src/cptla/evaluation/ocrflux_document.py`：安全响应解析、元素身份/来源链、两组评分输入；CPU可测，不导入vllm。
- `scripts/run_ocrflux_document.py`：官方推理入口封装、原始请求/响应及配置保存、GPU保护与清理；不读取truth。
- `scripts/adapt_ocrflux_document_predictions.py`：只读输出适配、哈希/覆盖与来源页验收。
- `scripts/run_ocrflux_document_full.py`：复用document_run.py的按文档checkpoint、新run恢复、清单冻结和完整导出；不改变现有Paddle入口。
- `tests/test_ocrflux_document.py`、`tests/test_ocrflux_cli.py`、`tests/test_ocrflux_full_entry.py`：先失败再实现的契约/合成/CLI/恢复回归。

## 7. 分阶段验收

1. CPU合成测试：正常/恶意字符串、不合法索引；同文同页重复HTML身份不混；两页/三页合并、重复表头；跨文档隔离；页面错误与空表；重建失败；输入不变、缺页/重复页拒绝。对可比较的合法输出核对官方helper行为，不能只测试mock。
2. 真实train：复用完整PMC10235804、PMC10311686、PMC11626747共10页，包括2个跨页正例、1个无跨页文档及4个无表页，输入不筛页。保存原始预测，导出no_merge/merged两组；逐样本核对来源链和错误。推理失败不隐藏，契约失败先处理。
3. 独立CPU评分：train truth仅生成离线子集gold，评分使用--partial明确标train开发结果。报告覆盖、HTML拒绝、GriTS和内容exact，来源页另核；不将小样本分数称正式性能。
4. 实际恢复演练：完整文档checkpoint有产物SHA，新run传入旧checkpoint，完整文档不重复GPU生成；不完整文档只在新目录重跑。源/参数/代码/依赖/model revision不同则拒绝恢复。
5. 完整val预检：固定源manifest SHA `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`，数字页序SHA `1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`；935/13,871成员一致，权重/源码/环境SHA固定，输出新目录、后台保活与日志就绪。全部门禁有证据后才称全量READY；本设计不表示已启动。

## 8. 留痕与非目标

代码先本地，测试通过后按授权同步特定代码；不传data/artifacts/outputs/logs到远程覆盖。新实验UTC目录，不删除失败环境或结果。阶段结束/启动后台/结论变化同步memory、progress及experiments。

本阶段不训练、不调优提示或合并规则、不升级核心模型、不测试test，不做Popo/POTATR，不替换评分公式或设计GUI。优先完成可复现基线，而不是把工程安全修正包装为研究贡献。
