# dots.ocr与PaddleOCR-VL-1.5完整文档基线结果

日期：2026-10-30（Asia/Shanghai）。状态：**已提供：读取服务器保存的五组metrics并重新核对SHA；不是新评分或模型训练**。本报告对应Full Documents的dots/Paddle，不包含早期TATR裁剪单表赛道。

## 范围与证据

PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、validation，935文档/13,871页，所有页面均输入（含无表页），image-only，不提供GT表框、文字层、续表关系或筛页。全表真值2,587张（既有真值审计记录），跨页真值子集983张。五组覆盖均13,871/13,871，missing/extra/duplicate=0；覆盖完整不代表全部页面识别成功。

dots输入为逐页JPEG，使用其保存的页面预测；Paddle把相同完整页面按原文档数字页序封装为无文字层PDF，使用版面检测+逐页VLM+官方重组。输入逻辑成员相同，但模型、预处理、生成配置和合并方法不同，以下是当前系统管线结果比较，不是仅替换同一合并模块的因果消融。每个模型内部则复用同一页面预测进行合并配对对照。

详细复现依据：[dots实验记录](../experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md)、[Paddle推理记录](../experiments/2026-10-23-paddle-full-val-inference.zh-CN.md)、[Paddle三组评分](../experiments/2026-10-29-paddle-full-val-three-condition-scores.zh-CN.md)。权重分别为dots revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`、Paddle revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，Paddle版面模型revision `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`。依赖/完整命令/代码commit/输出哈希与错误见各实验记录，不以本汇总替代。

## 全文档全部表格

### “合并”的实际含义（同日源码复核）

这里均为逐页解析之后的跨页表格结构后处理，不是拼接像素图片，也不是无条件把相邻页所有表连接。dots项目规则仅考虑相邻页边界表，要求页边几何、同列数和相同显式首行表头，通过后去掉后片段首行、按行追加HTML（`src/cptla/evaluation/simple_merge.py::_append_without_header`）。Paddle官方为宽度/上下文/列结构等规则判定后执行跨页结构合并与重复表头处理，具体已审计版本见Paddle合并契约实验；兼容版仅补齐文本访问字段，仍调用同一官方合并器（`paddle_document.py::remerge_document`）。这些后处理不重新调用VLM联合识别两页；不是训练得到的跨页关系图重建模型。没有新实验或指标，不据此推断所有拆分行/列错位可恢复。

GriTS为0–1分数；exact列转为百分数。Top侧重结构，Con同时考虑单元格内容。内容网格exact按本项目评分器定义，不能不核对协议就与论文不同split/输入的Acc-Con横比。

| 系统条件 | GriTS-Top | GriTS-Con | 内容网格exact |
| --- | ---: | ---: | ---: |
| dots，不合并 | 0.544990432 | 0.507793689 | 8.156165% |
| dots，项目简单合并 | 0.581836676 | 0.547900148 | 8.194820% |
| Paddle，不合并 | 0.681752302 | 0.651021738 | 11.519134% |
| Paddle，官方原版合并 | 0.730608322 | 0.700574254 | 11.751063% |
| Paddle，字段兼容版合并 | 0.803682515 | 0.774418507 | 11.982992% |

## 983张跨页真值子集

| 系统条件 | GriTS-Top | GriTS-Con | 内容网格exact |
| --- | ---: | ---: | ---: |
| dots，不合并 | 0.487391646 | 0.457699197 | 0/983（0%） |
| dots，项目简单合并 | 0.542889708 | 0.513144539 | 2/983（0.203459%） |
| Paddle，不合并 | 0.702955116 | 0.672710736 | 0/983（0%） |
| Paddle，官方原版合并 | 0.763892548 | 0.734669528 | 6/983（0.610376%） |
| Paddle，字段兼容版合并 | 0.836100530 | 0.806670507 | 12/983（1.220753%） |

跨页子集按Con在文档全表中匹配后抽取GT子集，Top沿用Con匹配；不是独立续表检测precision。内容网格exact不检查来源页，不能称以上2/6/12已核验完整恢复。结构网格exact也不等于内容exact。

## 覆盖之外的诊断

| 系统条件 | 推理错误页 | 评分拒绝HTML表 | 跨页正内容重叠匹配 | 其中缺来源页的匹配项 |
| --- | ---: | ---: | ---: | ---: |
| dots，不合并 | 2 | 637 | 643 | 643 |
| dots，项目简单合并 | 2 | 637 | 639 | 527 |
| Paddle，不合并 | 0 | 13 | 979 | 979 |
| Paddle，官方原版合并 | 0 | 13 | 979 | 780 |
| Paddle，字段兼容版合并 | 0 | 13 | 979 | 478 |

“正内容重叠匹配”不是成功恢复数；来源页缺失与额外页计数可能重叠，也不是完整续接P/R/F1。637与13为评分解析器拒绝的表数量，不能直接解释为模型没有检测到这些表。dots历史HTML审计显示存在解析兼容风险，因此当前分差不能全归因模型能力；任何HTML处理变更须先在train核验冻结，另立目录复评，不能按val GT修表。

## 结果解释与下一步

已提供的结果：当前Paddle管线在所列GriTS及内容网格exact上高于当前dots管线；各自合并提高了整体相似度，但内容整网格exact增幅小，跨页严格内容全等仍罕见。待核验：低exact具体由文字、列错位、重复表头、跨页拆分行还是漏连/误连主导；不能仅凭汇总指标断言原因。字段兼容版是独立改动条件，不冒称官方原版。

下一步按10月23日优先计划准备OCRFlux-3B独立环境与train smoke，再全量；随后固定Paddle上游测MinerU-Popo。配合有限抽样进行来源页/错误审计，不重跑已完成推理或评分，不用test开发。

## 本次只读核对的metrics SHA-256

服务器`artifacts/cross-page-scores/`下：

- `20261020T123212Z-dots-full-val-offline-no-merge/metrics.json`：`ba5e206bb7ac3d4c091d53eea29bc66c2740b6ab6f4de78c63c6d46e22bdff02`；
- `20261020T123212Z-dots-full-val-offline-simple-merge/metrics.json`：`fb40d5ae6d33399f1250b0b113c9f98ec23b9636d58fca109747855eb1e18cba`；
- `20261029T035007Z-paddle-full-val-scores/no_merge/metrics.json`：`bedff43c8d91c06103be74e86ed5b3b1964c691c6e710fd0e69e782627b64428`；
- 同Paddle根`native_merge_official/metrics.json`：`c5d16f623cad48d2645115ae27420486f3fbcd1fe0d6db2957eda4c5924481f8`；
- 同Paddle根`native_merge_content_compat/metrics.json`：`350c4b2d96bfb15a86c55ecfc6d39864fd94663f8a48bf64d774421531e3e67b`。
