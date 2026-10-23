# Paddle 字段兼容与评分适配实施计划

> 使用 writing-plans 制订；当前用户已批准上一轮契约审计中的设计，按 executing-plans 在本会话逐项执行，不委派子 Agent。

目标：复用 train 6 页预测，保留 no_merge / native_merge_official，单列 native_merge_content_compat；三组均能保留来源页进行现有评分。

架构：纯 Python 模块负责严格校验和来源页转换，兼容层调用安装的固定官方合并函数，仅增加 text=content 字段桥接；CLI 负责 SHA、原版回放对账和新目录输出。评分复用现有 grits 及 cross_page，不改变公式。

约束：固定数据/模型 revision 见契约审计；不读 val/test 调规则；服务器仅项目根目录，新时间戳产物、不覆盖；本阶段 CPU、不下载、不训练。train 分数不作为正式基线。兼容版不得冒称官方原版。原 HTML 不清洗，空尾片段仍须贡献来源页。

## 任务 1：严格来源页转换与兼容函数

文件：新增 `src/cptla/evaluation/paddle_document.py`、`tests/test_paddle_document.py`。

- [ ] RED：用两页/三页表含空尾片段测试 `adapt_document(pages, document_id, expected_pages)`，断言 `source_pages == [0,1,2]` 且 HTML 原样；缺页、重复 global ID、悬空引用、非表根、组内多非空 HTML 均拒绝。
- [ ] GREEN：按页号校验覆盖、构建所有 block 全局 ID 索引；按 table global_group_id 聚合，要求根为自身且为 table，每组恰一非空根，输出标准 document table 字典与证据。不引用 GT。
- [ ] RED/GREEN：`remerge_document(pages, merge_function, content_compat=False)` 要求原始组未合并且 global ID 与官方列表序号一致；深复制 block，创建等价 label/bbox/content/global ID 对象，兼容条件仅额外设置 text。调用原官方函数，只写回 content/group。正例续表标题、普通标题/正文负例、宽度不匹配拒绝、三页链均测试；输入不变。
- [ ] 测试命令：`.venv\Scripts\python.exe -m pytest tests/test_paddle_document.py -q --basetemp artifacts/test-runs/<新时间戳>`；原版 RED 后 GREEN，Ruff 通过。

## 任务 2：服务器 CPU 输出适配入口

文件：新增 `scripts/adapt_paddle_document_predictions.py`。

- [ ] 校验固定官方 merge_table.py SHA，输入 packing manifest 及原推理 summary/pages 覆盖。验证每份 no_merge 回放原版与保存 native_merge 全对象一致，不一致直接报错。
- [ ] CLI 参数：`--inputs`、`--predictions`、`--official-merge-source`、`--output-dir`；输出目录须不存在。每模式输出 page-results.jsonl、document-tables.jsonl、table-evidence.jsonl，并保存 compat 官方形状 JSON。原/生成文件 SHA 及覆盖、配置、代码 commit 写 summary。
- [ ] page-results 仅用于覆盖，耗时字段 0 为明确标识的未知占位，不拿来报告速度。input_manifest 必须完整覆盖原推理输入，document ID/path 必须拒绝穿越。
- [ ] 本地回归/语法检查后提交新分支，推送到 gpu 的新引用；服务器干净情况下仅 fast-forward 代码。服务器 eval312 跑测试，用新 artifacts 路径做 CPU 适配，核验原输入 SHA 未变。

## 任务 3：train 配对评分与交付

- [ ] 从两个 train tables 文件构造这两篇文档全部跨页 GT，单独保存在新产物目录；只评分时读取 GT，不传入适配器/合并器。按 tables parts 的 page_num、html 和 table_id 契约构造 gold。
- [ ] 分别运行 `scripts/score_cross_page_predictions.py`，指定 6 页 input-manifest、各组 page-results/document-tables、train truth-dir、该 gold 和新 score 目录；使用 `--partial` 标明 train 小规模诊断，不冒称 full_validation。
- [ ] 检查 coverage、invalid HTML、来源页 matched 明细及指标；单列合并触发与严格内容 exact，不能把触发数当正确率。保存三组输出 SHA。
- [ ] 更新 memory、progress 与实验记录；标明是否仍有全量门禁缺口，不自动启动大规模 val。

验收：合成契约测试及服务器真实 6 页转换均成功，原版回放一致，兼容版不覆盖官方结果；三组 train 评分完成/失败必须如实记录，原输入不变。全量运行的可恢复入口与额外负例泛化审计不属于本次交付。

## 首轮交付与用户新增要求

2026-10-23：任务1、2、3已完成；服务器首轮60测试通过，三组train评分与来源页验证成功，详情见 `docs/experiments/2026-10-23-paddle-compat-adapter-and-train-score.zh-CN.md`。独立只读代码审查无Critical/Important；CLI端到端及原版回放异常测试已补充，等待服务器末轮回归。

用户随后明确要求“持续完成直到可以开始全量模型测试推理为止”。因此新阶段纳入更多真实train正负例、可恢复全量入口、固定val清单与资源预检。上述“全量入口不属于本次交付”仅指首轮范围，现已扩展；不因此自行更换模型/参数或以val调规则。达到可启动条件后报告，不擅自把尚未开始的全量写为运行中。
