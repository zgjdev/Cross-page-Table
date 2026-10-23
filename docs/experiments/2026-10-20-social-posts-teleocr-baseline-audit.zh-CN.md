# 两篇社交平台文章与跨页五方案的相关性核验

核验时间：2026-10-20 13:27 UTC。**状态：第一篇已核验；第二篇正文待获取；未新增模型下载、GPU 推理或实验结果。**本记录仅用于候选方案筛选，不改变现行 `docs/2026-10-20-cross-page-five-method-evaluation-plan.zh-CN.md`。

## 微信文章：TeleOCR

- 用户提供的公开页面：<https://mp.weixin.qq.com/s/pz0qloEOB4o5OMnIFoToyw>；标题为《多个榜单登顶、1.2B参数，轻量化TeleOCR解锁文档智能化解析新能力》。2026-10-20 使用公开移动端 User-Agent 只读获取正文；正文介绍了 `TeleOCR` 的文档解析、表格结构、页内跨行跨列和跨栏表格，未出现“跨页”。**“跨栏”是同页版面概念，不等于跨页续表。**文章数字引用的是 OmniDocBench / Wild-OmniDocBench 等解析基准，不是 PubTables-v2 跨页整表结果。
- 原始论文：Cai 等，*TeleOCR: Navigating Document Parsing Across Digital and Camera-Captured Documents*，<https://arxiv.org/abs/2608.12898v3>；论文的主要目标是文档解析及表格、公式等结构表达。官方代码入口见论文 <https://github.com/caipeng328/TeleOCR>；官方模型卡当前由 `XingChen-AGI/TeleOCR` 托管，<https://huggingface.co/XingChen-AGI/TeleOCR>。模型卡提供图片表格 OTSL 到 HTML 及图像版面识别示例，标称约 1.2B 参数、Apache-2.0。公开模型元数据只读核验返回 `private=false`、`gated=false`、revision `70a19ec6a3b036311af19ae5e762e650f41a5980`，镜像端点为 `hf-mirror.com/api/models/XingChen-AGI/TeleOCR`；模型卡是否还提供文档 PDF 输入接口不代表可恢复跨页逻辑表。本次官方 HF 主站连通超时，镜像信息需要下载前复核；仓库内未见此模型权重。
- **依据与判断分开：**已提供的论文、公开代码/模型卡和文章证实它可作为**页面解析器候选**；未发现官方说明或可比实验展示跨页续接决策、重复表头消重、跨页拆分行恢复和完整文档跨页整表评测。由此推断**不能以原生跨页恢复方法列入现行五方案的核心比较**；这不是断言该系统绝对无法处理多页 PDF 或未来不会新增能力。
- **可选补充（计划中，未批准启动）：**如研究页级解析上限，可作为 image-only 的第六个上游，与 dots.ocr 在相同全部 13,871 validation 页输入上做 `no_merge` / 同一冻结合并器的配对实验；保留页号、bbox、结构及 HTML/OTSL 转换失败记录。先使用 train 小样本检验输出契约、模型 revision 和 GPU 显存门禁，再决定是否投入完整评测。其公开解析分数不能直接与现有 PubTables-v2 跨页 GriTS/网格 exact 比较；优先级低于验收 dots、核验 POTATR 和现有跨页专用基线。

## 小红书文章：待核验

- 用户提供的链接指向 `/explore/6abccaf1000000001501104e`；**不记录分享 token**。2026-10-20 只读访问不带 token 的公开页面、移动端页面和公开搜索，没有获得可靠的标题、正文或所述模型。页面标题仅为“小红书”，曾返回“你访问的页面不见了”或不含笔记正文的通用页面。
- 无法确认它介绍的是哪篇论文、什么模型、是否开源或是否有跨页合并能力；不能把未知内容列入当前计划。下一步请用户提供文章截图、正文或论文/模型名称，再逐一从原论文和官方实现验证任务/输入/权重/许可/评价协议，确认是否新增独立跨页方法或只是页面识别器。

## 对当前工作的影响

现行五方案及 PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903` 的完整文档主协议**不变**；不将微信营销页的解析 benchmark 误记为跨页能力证据，不对小红书未知内容作推断。本次没有下载、训练、启动 GPU，也没有修改运行中的 dots.ocr CPU 评测；该评测状态以独立实验记录 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 和服务日志为准。
