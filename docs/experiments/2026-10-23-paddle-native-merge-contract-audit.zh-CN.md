# PaddleOCR-VL-1.5 官方合并字段契约只读审计

日期：2026-10-23 09:51 UTC（北京时间 17:51）。状态：原因核验已完成；兼容修正与评分 adapter 设计待确认，未实现、未全量评测。延续 [环境与 smoke](2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md)。

## 范围与复现输入

- 研究问题：为何已完成 GPU smoke 的两个 train 跨页案例没有触发官方合并；这是否来自页面识别错误、官方合并规则或本项目 adapter。
- 数据：PubTables-v2 Full Documents 固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、train、2 文档/6 页、image-only。案例 `PMC10235804`、`PMC10311686`，沿用既有选择；不读取 val/test，不新增 GPU 推理或数据下载。
- 模型：PaddleOCR-VL-1.5 SHA `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，版面组件 PP-DocLayoutV3 SHA `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`；页面推理代码 `2ceceb9`、seed 0，完整命令/环境/覆盖见前述记录。
- 输入：`outputs/baselines/paddleocr-vl-1.5/20261023T082900Z-paddle-train-smoke/<document_id>/no_merge.json`；该 run 的 native_merge 和页面原始输出只读保留。
- CPU 环境：`.venvs/paddle-v15-20261023T081029Z-paddle-v15/bin/python`，PaddleOCR 3.4.0、PaddleX 3.4.1。只载入纯 Python 合并函数与 AST 提取的 `PaddleOCRVLBlock` 类，不导入 GPU 管线；无模型训练、无随机采样。本次诊断通过 SSH 向 Python stdin 传入内存代码，没有另存新预测。

## 已提供：实际拒绝条件

官方源码： [merge_table.py](https://github.com/PaddlePaddle/PaddleX/blob/v3.4.1/paddlex/inference/pipelines/layout_parsing/merge_table.py)、[result.py](https://github.com/PaddlePaddle/PaddleX/blob/v3.4.1/paddlex/inference/pipelines/paddleocr_vl/result.py)。本次直接核对服务器安装文件，合并器 SHA-256 `95a9fe523b4e226c8a2a7af70d770993b7ccb772afb6fc10dbe079f6083a19e0`。

`can_merge_tables` 先检查宽度差小于 10%、前页表后内容类型、续页表前内容类型，再检查总列数或边界行列数。两例均通过宽度、前页表后内容及结构条件，实际被续页表前 `figure_title` 拒绝：

| 文档 | 两片段宽度/差异 | 列数 | 边界行匹配 | 续页标题 | 官方结果 |
| --- | --- | --- | --- | --- | --- |
| PMC10235804 | 460/458，0.437% | 2/2 | 是 | `Table 1. Continued` | 拒绝 |
| PMC10311686 | 973/970，0.309% | 4/4 | 是 | `Table 1. (Continued)` | 拒绝 |

`is_skippable` 设计上支持 continue/continued 等关键词，但读取对象 `.text`、`.figure_title`、`.doc_title`、`.paragraph_title`。实际 `PaddleOCRVLBlock` 把文字保存在 `.content`，没有上述文字属性，故关键词检测收到空字符串。两例标题文字已被正确识别，却没有传入这个分支；不能据此把未合并归因于 VLM 没识别出 Continued。

## 单变量内存反事实核验

从安装的 `result.py` 用 AST 原样提取该类，依据保存的官方 JSON 重建 block；加载安装的原合并器，不更改其规则或原文件。在两种条件下分别调用 `can_merge_tables` 与 `merge_tables_across_pages`：

1. 原类原字段：两例 `can_merge=False`，两页表 group 分别独立，复现保存结果。
2. 仅为内存 block 设置 `block.text=block.content`：两例 `can_merge=True`，发生同组纵向合并；既有规则各去除 1 行重复表头，后页 block 内容置空并指向前页 group。

| 文档 | 原 table global ID | 桥接后 global group ID | 两页表 HTML 字符数（原 → 桥接后） |
| --- | --- | --- | --- |
| PMC10235804 | 31、35 | 31、31 | 2564/1825 → 4326/0 |
| PMC10311686 | 19、24 | 19、19 | 5337/1534 → 6691/0 |

两输入 no_merge.json 在内存实验前后 SHA 相同。没有修改安装包、脚本、原始结果、数据或日志；没有生成新的正式分数。**触发合并不等于合并内容和结构完全正确**，尚未和 GT 作完整网格对比，也未证明该字段桥接对其他文档没有误连风险。当前是这两个 train 案例上的可复现字段契约原因，不外推整套 validation。

## 下一阶段设计（待用户确认，不是已实现）

推荐保留固定官方原版，单列字段兼容修正版，二者共享完全相同的页面预测：

- `no_merge`：原页面表片段，来源页完整保留。
- `native_merge_official`：不改 PaddleX 3.4.1，记录其真实行为，包括已知字段问题。
- `native_merge_content_compat`：独立后处理，仅补齐续表关键词文字访问；不改变列数、宽度、阈值或内容，不覆盖 site-packages，不混称原始官方结果。先在 train/合成正负例测拒绝逻辑，再冻结并用于 val；不得用 val/test 调参。

替代方案：只跑官方原版（复现最直接但已知兼容问题保留）；升级 PaddleX（需另立版本对照，改变因素更多，不作为本阶段首选）。三者不能静默混用。

评分 adapter 计划只转换保存结果，不执行模型推理或读 GT：按文档内 `global_group_id` 聚合所有 table block 的来源页（包括内容被清空的尾片段），每组只输出一份非空 HTML；页覆盖单独保留，原 HTML 不规范化或修补。拒绝缺页/重复页、重复 global ID、悬空组引用、非表根、组内多份非空 HTML 等不确定情况；跨文档 ID 不混用。来源页无法证明时直接报错，不从 GT 补齐。用 2 页、3 页、无表页、误连拒绝与异常契约测试验收，再对本轮原结果转换并执行 train smoke 评分。

全量门禁仍未通过：需完成上述字段条件选择、adapter 契约测试及 train 评分后，才建立 validation 可恢复分片。本轮无后台任务启动、无新模型结果；研究贡献不以修复该兼容问题作为主张。
