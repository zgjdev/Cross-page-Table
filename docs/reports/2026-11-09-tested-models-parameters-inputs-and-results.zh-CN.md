# 已测模型的参数、输入与公开结果对照

更新日期为 2026-11-09（北京时间）。项目已完成三套 Full Documents 图像输入管线的验证集推理与评分，以及一套 Cropped Tables 的文字辅助评测。以下结果引用保存的实验产物，本次额外核对论文、官方资料和服务器已有权重的参数口径。

## 模型与项目实际输入

| 已测模型 | 官方参数口径与实际核对 | 项目输入和输出 | 评测范围 |
| --- | --- | --- | --- |
| dots.ocr | 官方发布说明称语言骨干为 1.7B，实际完整视觉语言权重约 **3.04B** | 逐页输入原始 JPEG 和固定解析提示。提取页面输出中的表格 HTML，按原文档归组，对比不合并和项目简单合并 | Full Documents validation，935 篇、13,871 页，image-only |
| PaddleOCR-VL-1.5 | 官方称识别 VLM 为 **0.9B**，实际权重约 **0.959B**。流程另有 PP-DocLayoutV3 版面检测组件 | 将文档全页 JPEG 按页序打包为无文字层 PDF。版面检测和 VLM 逐页输出结构化表格，再分别评估不合并、官方原版合并和字段兼容版合并 | 同一 Full Documents validation 全页，image-only |
| OCRFlux-3B | 官方型号为 **3B**，来自 Qwen2.5-VL-3B-Instruct。按当前配置对共享权重去重，完整模型约 **3.75B** | 文档全页 JPEG 打包为无文字层 PDF。推理逐页渲染图像并解析表格，再使用预测的页面元素检测续接，使用表格 HTML 重建接口合并候选片段 | 同一 Full Documents validation 全页，image-only |
| TATR-v1.1-Pub | 表格结构识别模型约 **28.8M** | 裁剪表格图像进入 TATR 预测行、列、表头与跨格结构。后处理用数据集提供的 PDF 词文本和坐标回填单元格，输出整表 HTML | Cropped Tables validation，13,384 个裁剪表样本，PDF-text-assisted |

参数核对使用服务器现有文件的 Safetensors 头部形状，按每个张量各维相乘后加总。dots、Paddle VLM、TATR 存储张量元素分别为 3,039,179,264、958,588,736、28,847,819。OCRFlux 存储张量元素为 4,064,739,328，包含两份各 310,640,640 元素的输入词嵌入和输出词表权重。用固定配置在 meta device 构建模型并调用 `tie_weights()`，确认两者共享同一参数对象，`model.parameters()` 去重合计 3,754,098,688，其中视觉组件 668,684,288。参数量以各主模型为单位。 [dots.ocr 官方发布说明](https://github.com/studio-dots-ai/dots.ocr#news) · [PaddleOCR-VL-1.5 技术报告](https://arxiv.org/abs/2601.21957) · [OCRFlux-3B 官方模型卡](https://huggingface.co/ChatDOC/OCRFlux-3B) · [TATR 官方模型卡](https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub)

固定模型来源如下。

- dots.ocr revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，项目路径 `checkpoints/dots-ocr/`。
- PaddleOCR-VL-1.5 revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，PP-DocLayoutV3 revision `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`。VLM 路径 `models/20261023T064109Z-public-models/paddleocr-vl-1.5/`。
- OCRFlux-3B revision `e68592278bbc8ab32edf7b65e6e411f1d878ef72`，官方源码 `c1b315aa4c8309f8dc436a5d90fc4977bcf0d865`，权重路径 `models/20261023T064109Z-public-models/ocrflux-3b/`。
- TATR-v1.1-Pub 为 Microsoft 的 `table-transformer-structure-recognition-v1.1-pub`，项目路径 `checkpoints/tatr-v1.1-pub/`。v1.1 权重训练来源为 PubTables-1M，见 [Aligning benchmark datasets for table structure recognition](https://arxiv.org/abs/2303.00716) 与官方模型卡。

## 论文与官方基准结果

| 模型 | 公开实验的输入与评测范围 | 公开结果 |
| --- | --- | --- |
| dots.ocr | PubTables-v2 v3 表 7。Full Documents，逐页图像识别，比较不合并和 ViT-B/16 判续接后同列数纵向拼接。统计文档内全部表格 | 不合并 GriTS-Top **0.6054**、GriTS-Con **0.5768**、Acc-Con **11.80%**、TEDS **0.5876**。合并后分别为 **0.7206**、**0.6844**、**11.80%**、**0.7141**。 [PubTables-v2 论文](https://arxiv.org/html/2512.10888v3) |
| PaddleOCR-VL-1.5 | 技术报告表 2，OmniDocBench v1.5 文档解析 | Overall **94.50**、Table TEDS **92.76**、Table TEDS-S **95.79**，为论文表的 0–100 口径。 [PaddleOCR-VL-1.5 技术报告](https://arxiv.org/html/2601.21957) |
| OCRFlux-3B | 作者公开的 OCRFlux-pubtabnet-single 单表评测，以及 OCRFlux-pubtabnet-cross 的 9,064 对人工拆分 HTML 表格片段合并评测 | 单表平均 TEDS **0.861**。给定两个结构化片段后的合并平均 TEDS **0.950**，其中简单表 **0.965**、复杂表 **0.935**。 [OCRFlux 官方基准](https://github.com/chatdoc-com/OCRFlux#benchmark-for-cross-page-tableparagraph-merging) |
| TATR-v1.1-Pub + DT | PubTables-v2 v3 表 3，Cropped Tables 长宽表结构识别，使用 Direct Text | GriTS-Top **0.9608**、GriTS-Con **0.9590**、Acc-Top **48.94%**、Acc-Con **48.40%**、TEDS **0.9387**。 [PubTables-v2 论文](https://arxiv.org/html/2512.10888v3) |

公开基准与项目结果需按输入、数据划分、合并器和指标解释。dots.ocr 公开合并使用训练过的续接分类器，项目使用重复表头等规则。Paddle 报告的 Overall 是文档解析综合分。OCRFlux 的 0.950 衡量给定 HTML 片段后的平均树相似度。项目三个整文档模型的主结果统一使用 PubTables-v2 validation，跨页列专门统计其中 983 张自然跨页真值表。

## 项目正式结果

前三款模型共享完整文档验证集，共 2,587 张真值表，983 张属于跨页子集。每款模型的不同合并条件复用同一批逐页预测。

| 管线 | 全表 GriTS-Top | 全表 GriTS-Con | 全表内容网格 exact | 跨页 GriTS-Top | 跨页 GriTS-Con | 跨页内容网格 exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dots，不合并 | 0.5450 | 0.5078 | 8.16% | 0.4874 | 0.4577 | 0/983 |
| dots，项目简单合并 | 0.5818 | 0.5479 | 8.19% | 0.5429 | 0.5131 | 2/983（0.20%） |
| Paddle，不合并 | 0.6818 | 0.6510 | 11.52% | 0.7030 | 0.6727 | 0/983 |
| Paddle，官方原版合并 | 0.7306 | 0.7006 | 11.75% | 0.7639 | 0.7347 | 6/983（0.61%） |
| Paddle，字段兼容版合并 | 0.8037 | 0.7744 | 11.98% | 0.8361 | 0.8067 | 12/983（1.22%） |
| OCRFlux，不合并 | 0.5907 | 0.5355 | 4.33% | 0.5669 | 0.5238 | 0/983 |
| OCRFlux，表格重建合并 | 0.6418 | 0.5963 | 4.48% | 0.6320 | 0.5889 | 4/983（0.41%） |

整文档三款模型的推理错误页分别为 dots 2、Paddle 0、OCRFlux 729。评分保留失败页面并覆盖全部输入。跨页内容网格 exact 检查结构与内容全等，来源页完整性另行审计。Paddle 字段兼容版补齐合并器读取字段，沿用同一个官方规则实现。 [三模型完整评分与诊断](2026-11-08-dots-paddle-ocrflux-full-val-results.zh-CN.md)

| 裁剪表实验 | GriTS-Top | GriTS-Con | Acc-Top | Acc-Con |
| --- | ---: | ---: | ---: | ---: |
| TATR-v1.1-Pub，项目正式复评 | 0.8848 | 0.8704 | 38.97% | 38.27% |

TATR 表采用修正 HTML 组装后，用同一批预测得到的正式评分。13,384 个样本全覆盖，其中 65 个推理错误。早期 dots.ocr 另有历史结果，使用真值筛出的 3,522 个含表页且没有跨页合并，全表 GriTS-Con 为 0.6216、Acc-Con 为 13.80%。该结果保留在历史记录。 [TATR 正式复评](../experiments/2026-09-22-tatr-html-rebuild-rescoring.zh-CN.md) · [dots 历史实验核验](../experiments/2026-09-22-historical-dots-full-documents-audit.zh-CN.md)

## 2026-11-09 PubTables-v2 v4 对照与分差核查

已核对 arXiv 2026-11-03 发布的 v4。上方公开结果表保留此前引用的 v3，当前引用用下表对应的版本。差值按论文减项目计算，两套数据划分不同，属于描述性差值。项目数据固定于 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`。本轮核查原文、上游代码和已有实验记录。 [论文版本记录](https://arxiv.org/abs/2512.10888)

| 对照条件 | 论文 v4 test GriTS-Con / Acc-Con | 项目 validation GriTS-Con / 内容网格完全匹配率 | GriTS-Con 差值 |
| --- | ---: | ---: | ---: |
| dots.ocr，逐页无合并，Full Documents 全表 | 0.5768 / 11.80% | 0.5078 / 8.16% | 0.0690 |
| dots.ocr，论文 ViT-B/16 合并 vs 项目规则合并，Full Documents 全表 | 0.7495 / 11.80% | 0.5479 / 8.19% | 0.2016 |
| TATR-v1.1-Pub + DT，Cropped Tables | 0.9585 / 48.16% | 0.8704 / 38.27% | 0.0881 |

**已核实的差异。** dots.ocr 的 v3 合并结果是 0.6844，v4 为 0.7495，无合并均为 0.5768。论文表 12 使用 Full Documents test 的全表集合，项目上表用 validation 的全表集合。项目另外报告的 2/983 是 validation 跨页子集网格完全匹配数，来源页完整性单独审计。PaddleOCR-VL-1.5、OCRFlux-3B 无 v4 同模型完整文档行。论文表 11 的 `POTATR + PaddleOCR` 是 POTATR 配外部 OCR 的 Single Pages 实验。 [PubTables-v2 v4 §4.5、§4.6、附录 F.2](https://arxiv.org/html/2512.10888v4) · [PubTables-v2 v3 表 7](https://arxiv.org/html/2512.10888v3)

**dots.ocr 的页级输出和合并需要分开归因。** 无合并时已差 0.0690。本地 adapter 留下 2,752 条预测，随后有 637 条（23.1%）被严格 XML 解析排除，且合并后失败数相同。已见可容错的 HTML 写法，也有真实的标签损坏或截断线索。核对作者 GriTS 上游 `f595883c64baed976f183996bdff83a5ea092996`，当前转换器使用容错的 `lxml.html.HTMLParser`，与本地固定版本的 `ElementTree.fromstring` 存在可定位差异。论文每组实际用的 HTML 预处理版本、可恢复表数和分数影响待核验。论文用训练过的 ViT-B/16 判续接，预测列数相同后纵向拼接，项目用页边位置、列数和重复表头规则。两边的组内增益分别为 0.1727 与 0.0401。需固定预测、数据和评分器交换合并器，才能测得合并器自身贡献。 [项目 dots.ocr 离线评分与解析审计](../experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md) · [作者 GriTS 转换器](https://github.com/kensho-technologies/grits/blob/f595883c64baed976f183996bdff83a5ea092996/grits/conversion.py)

**TATR 的剩余差距也出现在结构分。** v4 同型号、同为 PDF Direct Text，GriTS-Top 0.9608、Acc-Top 48.67%，项目为 0.8848、38.97%。项目内容 exact 仅比结构 exact 低 0.70 个百分点，因此优先核对同样本的输入缩放、检测阈值、行列及 span 后处理和单元格转换。现有证据支持结构环节值得排查，尚无法分配 split、实现和预测误差的占比。论文 v1.2 用 PubTables-v2 train 微调后再配 DT，分数 0.9801 / 68.57%，属于另一组权重。 [论文 v4 §4.3 与表 10](https://arxiv.org/html/2512.10888v4) · [TATR 正式复评](../experiments/2026-09-22-tatr-html-rebuild-rescoring.zh-CN.md)

**对研究问题的含义。** 论文页对续接 F1 为 0.991，合并使全表 GriTS-Con 从 0.5768 升至 0.7495，但全表 Acc-Con 均为 11.80%。相似度的提升和完全匹配率持平同时成立。论文给出全文档恢复与页对判别的证据，已知同表片段图条件下的列对齐、重复表头和拆分行贡献仍需隔离评测。先固定已有 dots.ocr 预测，在 train 的代表性样本逐条比较两种 HTML 转换输出，确认是否保留单元格、文本和 span。规则冻结后再在 validation 离线配对复评，旧分数与产物保留。 [论文 v4 §4.5–4.6 与表 12](https://arxiv.org/html/2512.10888v4)

**公开权重状态补记。** 作者现已发布 POTATR-v1.1-Pub 权重与训练、推理及评价代码，先前“等待权重”的项目状态需要更新。公开 checkpoint 与 v4 论文各行、以及独立的 ViT-B/16 续接权重的对应关系仍待核验。本轮仅确认公开来源。 [POTATR 官方权重](https://huggingface.co/kensho/POTATR-v1.1-Pub) · [POTATR 官方代码](https://github.com/kensho-technologies/POTATR)
