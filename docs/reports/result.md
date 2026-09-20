| 场景 | 数据集 | 方法/模型 | 输入文本来源 | 严格指标 | 结果 | 备注 |
|---|---|---|---|---|---:|---|
| 裁剪表，长表/宽表结构+内容恢复 | [PubTables-v2 Cropped Tables](https://arxiv.org/html/2512.10888v3) | TATR-v1.2-Pub | PDF 原生文本（DT） | `Acc-Con`，结构+内容 exact match | **0.6831** | 当前最强的公开严格结果之一；并非纯 OCR |
| 同上 | PubTables-v2 Cropped Tables | TATR-v1.2-Pub | docTR OCR | `Acc-Con` | 0.0191 | 结构模型很强，但 OCR 误差会使“整表全对率”骤降 |
| 同上 | PubTables-v2 Cropped Tables | Gemini 3.1 Pro | 端到端视觉语言模型 | `Acc-Con` | 0.1613 | 不依赖 PDF 原生文字，但严格全对率远低于“结构+原生文本”方案 |
| 同上 | PubTables-v2 Cropped Tables | Claude Opus 4.6 | 端到端视觉语言模型 | `Acc-Con` | 0.1060 | 同上 |
| 同上 | PubTables-v2 Cropped Tables | dots.ocr | 端到端视觉语言模型 | `Acc-Con` | 0.0566 | 开源小模型路线 |
| 单页、多表的结构+内容提取 | [PubTables-v2 Single Pages](https://arxiv.org/html/2512.10888v3) | POTATR | PDF 原生文本（DT） | `Acc-Con` | **0.6454** | 页面内多表和表定位使难度增加 |
| 同上 | PubTables-v2 Single Pages | Gemini 3.1 Pro | 端到端视觉语言模型 | `Acc-Con` | 0.3524 | 当前公开报告中端到端视觉模型的较强结果 |
| 同上 | PubTables-v2 Single Pages | dots.ocr | 端到端视觉语言模型 | `Acc-Con` | 0.1872 | 开源端到端基线 |
| 科学表格端到端恢复 | [PubTabNet](https://github.com/ibm-aur-nlp/PubTabNet) | OCRFlux-3B | 图像/VLM | TEDS | 0.861 | 不报告 strict exact match |
| 通用/复杂表格恢复 | PubTabNet、OmniDocBench 等 | [PaddleOCR-VL-1.5](https://arxiv.org/html/2601.21957v1) | 视觉模型 + pipeline | Table-TEDS | 约 0.91（特定 Real5 测试条件） | 不是 exact match |
| 金融表格恢复 | OmniDocBench、FinDocBench、自建金融集 | [LingDT-VL-OCR](https://arxiv.org/html/2603.11044v2) | VLM | TEDS | OmniDocBench 表格子集 0.932；FinDocBench 0.957 | 不是 exact match |
| 整篇文档表格恢复 | PubTables-v2 Full Documents | Claude Opus 4.6 | 全文档视觉语言模型 | `Acc-Con` | 0.2452 | 含多表、跨页表和无表页面，难度最高 |










| 工作 | 时间 | 场景 | 数据集/测试集 | 模型或方法 | 评价指标 | 结果 | 可比性 |
|---|---:|---|---|---|---|---:|---|
| [BERT-Based Semantic Matching](https://link.springer.com/chapter/10.1007/978-981-99-7545-7_41) | 2024 | PDF 跨页表识别与拼接 | 未公开标准集 | 表头/语义特征 + BERT 匹配；先判断续表，再合并 | 未找到公开、可核验指标 | - | 早期两阶段方案；无公开结果，无法比较 |
| [OCRFlux](https://github.com/chatdoc-com/OCRFlux) | 2025 | PDF/扫描件中跨页表和段落合并 | `OCRFlux-bench-cross`：1,000 个人工复核中英文相邻页；`OCRFlux-pubtabnet-cross`：9,064 构造性拆分表对 | 先识别相邻页 Markdown 元素的合并索引，再由 LLM 重建完整表 | 合并检测 Accuracy、P/R/F1；合并表 TEDS | 检测 Accuracy **0.986**、F1 **0.986**；合并表 TEDS **0.950** | 检测指标严格要求索引全对；表重建是软指标，且后者不是自然跨页 PDF 样本 |
| [MonkeyOCR v1.5](https://arxiv.org/html/2511.10390v2) | 2025 | 复杂文档跨页表与跨列宽表重建 | 论文案例 | VLM 文档解析与后处理重建 | 未单列跨页表指标 | - | 展示跨页表成功案例，不能证明准确率 |
| [PubTables-v2](https://arxiv.org/html/2512.10888v3) 续表判断 | 2025/26 | 科学论文相邻页续表判断 | PubTables-v2：9,866 正样本页对、5,964 负样本页对 | 双页图像横向拼接，ResNet-50 / ViT-B/16 二分类 | Recall、Precision、F1、AUC | ViT-B/16：Recall **0.995**、Precision **0.987**、F1 **0.991**、AUC **0.996** | 是严格的“是否续表”指标，不衡量合并后整表是否完全正确 |
| [PubTables-v2](https://arxiv.org/html/2512.10888v3) 逐页拼接 | 2025/26 | 科学论文表格逐页解析后合并 | PubTables-v2 Full Documents：9,172 篇文档、9,492 张跨页表 | `dots.ocr` + ViT 续表判断；预测续表且列数相同即纵向连接 | GriTS、TEDS、`Acc-Con` exact match | GriTS-Con **0.5768 -> 0.6844**；TEDS **0.5876 -> 0.7141**；`Acc-Con` **0.1180 -> 0.1180** | 目前最清楚地显示“软指标提升但整表完全正确率未提升”的研究 |
| [PubTables-v2](https://arxiv.org/html/2512.10888v3) 全文档提取 | 2025/26 | 端到端全文档表格提取，包含跨页表 | 同上 | 直接把整篇文档交给前沿 MLLM | `Acc-Con`：结构与内容严格全等的集合级 exact-match F1 | Claude Opus 4.6 **0.2452**；Gemini 3.1 Pro 0.2025；GPT-5.4 0.1636 | 严格程度最高、公开可复核；但评测对象是全文档所有表，不是跨页表专属子集 |
| [PaddleOCR-VL-1.5](https://arxiv.org/html/2601.21957v1) | 2026 | 通用 PDF、扫描件、长文档 | OmniDocBench/Real5-OmniDocBench；跨页表仅案例 | 页面解析 + 轻量后处理引擎合并跨页表 | Table-TEDS 等单页/文档指标；无跨页专属指标 | 无跨页严格数值 | 支持该能力，但不能与上述跨页结果横比 |
| [LingDT-VL-OCR](https://arxiv.org/html/2603.11044v2) | 2026 | 长篇金融文档跨页表 | 自建 472 个金融跨页表 | VLM 分页解析 + 自适应启发式拼接 | TEDS | **0.8915** | 自然金融跨页样本，但 TEDS 不是完全正确率，且没有公开对照表 |
| [VCCT](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6811737) | 2026 | 电力设备故障报告的跨页表 | 自建约 300 个跨页表 | 表头检测、边框分析和前序页上下文的续表预判 | Cross-page structural integrity | **82.0%**，对照 MonkeyOCR 78.5% | 衡量跨页结构是否保持完整；不等价于所有单元格文本和表结构全等；预印本、未同行评审 |
| [MinerU](https://opendatalab.github.io/MinerU/reference/changelog/) | 2025-26 | 通用 PDF 的 pipeline/VLM 跨页表合并 | 未公布跨页专属评测集 | 文档解析后处理 | 未公布 | - | 已实现功能，无公开独立准确率 |
| MinerU-Popo | 2026 | 文档结构后处理，包含跨页表连续性 | 多 OCR 模型输出 | 通用后处理模型重建文档结构 | 标题层级 TEDS、RAG 指标等 | 未报告跨页表严格结果 | 涉及跨页表，但没有可比较的表格拼接数字 |







