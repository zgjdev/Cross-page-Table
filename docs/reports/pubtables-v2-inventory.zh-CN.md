# PubTables-v2 仓库清单

- 仓库：`kensho/PubTables-v2`
- 解析后的修订版本：`aa575e798cb00a296925e2086addb3e3fd9a1903`
- 文件数：48
- 字节数：218471925494
- 扩展名：`{".gz": 42, ".md": 1, ".sh": 4, "<none>": 1}`

JSON 清单位于 Git 之外的 `artifacts/manifests/` 路径下。

## 审计范围与数据来源

本报告固定于仓库提交 `aa575e798cb00a296925e2086addb3e3fd9a1903`，评审日期为 2026-07-24。证据来源包括：

- 解析后修订版本上的 Hugging Face 数据集卡片；
- 使用 `files_metadata=True` 生成的 48 文件元数据清单；
- 仓库中的四个解压脚本；
- 对 Full Documents 公开测试集的每个归档执行最多 1 MiB 的 HTTP Range 审计，足以检查首个 tar 成员和少量序列化样本。

未下载任何完整数据集归档、PDF 语料库或页面图像集合。

## 许可证

数据集卡片声明采用 **CDLA-Permissive-2.0**。这是数据集许可证，不得与采用 **CC BY 4.0** 的 PubTables-v2 论文许可证混淆。源论文内容还可能继续受原始论文所对应的 PMC Open Access 条款约束；下游再分发必须保留这一区别。

## 集合、划分与路径

仓库包含三个集合和三个公开划分标识符：

| 集合 | 公开划分标识符 | 解压后的子目录 |
|---|---|---|
| `Cropped Tables` | `train`、`val`、`test` | `tables`、`images`、`words`、`xml_annotations` |
| `Single Pages` | `train`、`val`、`test` | `images`、`tables`、`words`、`xml_annotations` |
| `Full Documents` | `train`、`val`、`test` | `cross_page_table_pairs`、`images`、`single_page_table_continuations`、`tables`、`words`、`xml_annotations` |

数据集卡片报告了 135,578 个裁剪表格、467,541 个单页及其中的 548,414 个表格，以及 9,172 篇全文档及其中的 9,492 个多页表格。部分样本仍位于尚未发布的私有测试集中。内部项目划分名 `validation` 必须映射到仓库标识符 `val`；后续清单应明确记录这一映射。

仓库中存在一处需要防御性处理的不一致：`uncompress.sh` 将名为 `*_tables.tar.gz` 的 Cropped Tables 归档解压到 `tables`，而 `uncompress_cropped_tables.sh` 引用了 `grits` 目录/归档，但解析后的 48 文件清单中并不存在该目录/归档。后续工具应以清单中的名称为事实来源，不应假设特定集合的脚本仍为最新版本。

## 序列化格式

以下格式均已通过固定修订版本上的归档成员核验：

| 制品 | 成员命名示例 | 序列化格式与观察到的字段 |
|---|---|---|
| 页面图像 | `Full Documents/test/images/PMC12259915_page_4.jpg` | JPEG/JFIF 渲染页面图像 |
| PDF 词元 | `Full Documents/test/words/PMC11470387_page_0_words.json` | JSON 列表，包含 `bbox`、`text`、`block_num`、`line_num`、`span_num` 和 PDF 抽取标记 |
| 逻辑表格 | `Full Documents/test/tables/PMC11518671_tables.json` | JSON 列表，包含 `cells`、`parts`、`grid_top`、`grid_con`、`html` 和 `original_markup`；每个片段包含 `page_num`、`page_object_num`、`pdf_bbox` 和渲染图像 `bbox` |
| 跨页表格对 | `Full Documents/test/cross_page_table_pairs/PMC11276610.json` | JSON 列表，包含 `page_A`、`page_B` 和二元 `label` 记录 |
| 同页表格片段 | `Full Documents/test/single_page_table_continuations/PMC10474523_page_3.json` | JSON 对象，包含表格片段 `bboxes` 和 `adjacency_matrix` |
| XML 标注 | `Full Documents/test/xml_annotations/PMC11243142_page_4.xml` | Pascal-VOC 风格 XML，包含页面文件名、图像尺寸、数据库名称，以及存在时的页面对象 |

表格 JSON 证实数据包含文档级逻辑结构和页面片段框，但不提供每个多片段表格片段内部的行/列边界框。该局限与研究论文的描述一致，并构成拟议对齐标签派生工作的动机。

## 文档元数据可用性

- **PMCID：** 可作为文档、页面、表格和标注文件名的稳定前缀获得。
- **DOI：** 未在数据集卡片、清单路径或抽样表格 JSON 字段中公开。
- **期刊/ISSN：** 未在数据集卡片、清单路径或抽样表格 JSON 字段中公开。

因此，不能仅使用 PubTables-v2 文件构建拟议的期刊/ISSN 不相交划分。它需要另行建立带版本的 PMC 元数据查询，并以 PMCID 为键。如果该查询不可用或不完整，则模板聚类必须成为主要的不相交方案，不能暗中将 PMCID 当作期刊标识符。

## 压缩下载预算

所有数值均为解析后清单中的精确压缩字节数；近似二进制单位仅用于规划。

| 下载范围 | 字节数 | 近似大小 | 用途 |
|---|---:|---:|---|
| 仅 Full Documents 测试标签（`tables`、XML、表格对及同页续接标签） | 9,906,334 | 9.45 MiB | 不含图像或词元的小规模元数据/样本审计 |
| 所有集合中的全部结构元数据归档（相同标签类别） | 3,812,578,532 | 3.55 GiB | 仅结构的数据准备 |
| 所有非图像仓库文件，包括 PDF 词元 | 16,217,869,144 | 15.10 GiB | 不含渲染页面的文本/结构准备 |
| 完整 Full Documents 公开测试集 | 3,413,101,914 | 3.18 GiB | 首个端到端样本划分 |
| 所有 Full Documents 划分 | 36,333,161,334 | 33.84 GiB | 主要文档级实验 |
| 整个仓库 | 218,471,925,494 | 203.44 GiB | 全部三个集合 |

下一项任务应先处理 9.45 MiB 的 Full Documents 测试标签，再按文档执行范围请求或选择性样本下载。在模式、哈希、存储和样本审计全部通过之前，不应下载完整的 203.44 GiB 数据。

## 审计结论

1. PubTables-v2 在 CDLA-Permissive-2.0 许可下可公开使用，三个集合均具备所需的公开 `train`/`val`/`test` 归档。
2. Full Documents 直接提供逻辑表格、页面片段来源、困难表格对标签、页面图像、PDF 词元和页面标注，但不提供细粒度的片段级行/列边界框。
3. PMCID 可直接获得；DOI 与期刊/ISSN 需要外部补充。
4. 必须固定清单后再执行解压，因为其中一个附带辅助脚本与实际 Cropped Tables 归档名称不一致。
5. 无需批量下载即可开展元数据优先的工作；在样本流水线得到验证之前，完整仓库应继续保留在本地 CPU 工作区之外。
