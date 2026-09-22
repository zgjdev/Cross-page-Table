# 文献检索方案

## 范围

检索主题包括表格抽取、跨页表格、层次化文档解析、文档图、结构化表格生成，以及模板与领域泛化方面的英文研究。主要发表时间范围为 2015-07-24 至 2026-07-24；通过后向引文检索发现的更早期奠基性工作亦可纳入。

## 来源

检索 arXiv、DBLP、Semantic Scholar、IEEE Xplore、ACM Digital Library、SpringerLink 和 CVF Open Access。记录论文的规范链接；如存在官方代码或数据链接，也一并记录。

## 检索式

- "multi-page table" AND (recognition OR extraction OR detection)
- "cross-page table" AND (continuation OR merging OR structure)
- "table extraction" AND (full document OR page context)
- "hierarchical document parsing" AND (graph OR relation)
- "table structure recognition" AND (long table OR document)
- "document layout analysis" AND (relationship OR reading order)
- "template generalization" AND document AI

## 纳入标准

- 定义了相关任务、数据集、模型、指标或评测方案。
- 包含足够的方法细节，能够复现结果或进行结果比较。
- 使用文档图像、PDF 文本与版面信息，或同时使用二者。

## 排除标准

- 不包含文档版面的网页表格或关系型表格研究。
- 仅处理电子表格的研究。
- 对版面或表格结构没有贡献的纯 OCR 论文。
- 缺乏技术证据的非研究类产品页面。

## 筛选流程

依据 DOI/arXiv ID 去重，先筛选标题与摘要，再阅读全文以确定最终纳入的论文。对于每篇纳入论文，记录其任务、上下文层级、模态、数据、方法、指标、代码可用性、最有力的证据，以及一项与本项目相关的局限。

## 停止规则

首次检索在满足以下条件后停止：已筛选至少 40 篇论文，已阅读全文至少 25 篇论文，并且连续两轮前向与后向引文检索均未发现新的方法类别或数据集类别。
