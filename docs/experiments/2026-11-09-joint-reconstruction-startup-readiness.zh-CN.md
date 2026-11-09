# 联合重建首阶段启动就绪性核验

日期为 2026-11-09，Asia/Shanghai。服务器主探针时间为 08:03:06 UTC，即北京时间 16:03:06。状态为 **只读启动前核验完成，可以进入 G0 数据与评价准备；G0/G1 尚未通过，尚不能直接开始新模型训练**。

本轮响应用户“可以开始实验了吗”，检查 [技术路线 v1](../plans/2026-11-09-cross-page-joint-reconstruction-research-plan.zh-CN.md) 的执行起点。没有生成数据、修改服务器文件、下载权重、读取 test 内容、运行模型或正式评分。没有使用 GPU，也没有检查其实时空闲情况；不能据此宣称训练资源就绪。

## 已提供的命令证据

服务器根目录限定 `/data01/public/zhengguojie/paper`。使用 `ssh -o BatchMode=yes -o ConnectTimeout=15 172.17.60.82`，远程命令为 `cd /data01/public/zhengguojie/paper && .venvs/eval312/bin/python -`，通过标准输入执行只读 Python 探针。解释器后续核验为 Python 3.12.7。探针只调用项目内路径的 `Path` 读取、JSON 解析、SHA-256 与 Git 查询，没有产生服务器产物。

| 检查项 | 命令实际结果 |
| --- | --- |
| 分支与 HEAD | `codex/paddle-merge-compat`，`6ee8fcbc245551bf3a20f3d5f86aa4c7cdd57c3a` |
| 服务器工作区 | `git status --porcelain=v1` 为空 |
| train/images | 110,347 个文件 |
| train/tables | 7,359 个文件 |
| train/cross_page_table_pairs | 7,359 个文件 |
| 既有 val 跨页清单目录 | `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/` 存在 |
| 既有 Paddle 完整 val 运行目录 | `artifacts/paddle-document-runs/20261023T152753Z-paddle-val-full/` 存在 |
| 既有 Paddle 模型目录 | `models/20261023T064109Z-public-models/paddleocr-vl-1.5/` 存在 |
| 新重建入口 | `scripts/build_reconstruction_manifest.py` 不存在 |
| 新重建模块与配置 | `src/cptla/reconstruction/`、`configs/reconstruction/` 不存在 |
| 新重建结果目录 | `artifacts/reconstruction/`、`outputs/reconstruction/` 不存在 |

上述文件计数不是全量内容完整性验收；模型目录存在不等于已复验权重 SHA 或 GPU 可用。数据版本沿用项目固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903` 的历史记录，本轮未重新计算整个数据集校验和。

读取按文件名排序的前三份 train 表标注，三份均为 list，表对象包含 `cells / original_markup / parts / grid_con / grid_top / html`。

| 文件 | 表数 | 本轮重算 SHA-256 |
| --- | ---: | --- |
| `PMC10120619_tables.json` | 1 | `a51eccbf2d6a7620da45271d59c66f7faeea06f687aa02c9c179671c0743d157` |
| `PMC10154839_tables.json` | 2 | `a018260c34d8b31c23790d9d1ca27a3c6adec6fa49c6a103cb99a6ad961cba3f` |
| `PMC10154848_tables.json` | 2 | `764be8017ae896b1b1a6f820941704fe29297098ad6b2b1ad4ee282deb7dadb5` |

第一份样本包含 page 22、23 的跨页片段；`parts` 提供 `page_num / page_object_num / pdf_bbox / bbox`。图像像素坐标与 PDF 坐标不能混用，具体裁剪变换仍待图像核验。该表共 355 个 cell，抽查前两个 cell 的字段含 `row_nums / column_nums / is_column_header / xml_text_content` 等整表结构信息，未见逐 cell 页号或 bbox 字段。这只是两个 cell 的字段检查，不能外推为所有文件均无定位信息，也不意味着已有预测 cell 到全局 cell 的唯一对应标签。

核验选择为文件名排序前三份，没有随机抽样种子，不用于估计错误比例或泛化性能。没有模型 revision、训练随机种子或新指标；本轮不属于模型性能实验。只读输出保存在本次执行工具记录，上表保存了可核对的计数及文件指纹，未伪造服务器日志路径。

## 代码与关口复核

独立只读复核确认，现有 [build_cross_page_manifest.py](../../scripts/build_cross_page_manifest.py) 用于 validation，包含固定 `split="val"` 和 train/val/test ID 互斥检查。不能把当前 train 路径同时填入被审计集合与互斥集合，并称为新的 train 审计。需要先实现计划 P0/P1 的 train 内划分、近重复簇、片段清单和输入/目标隔离。

已有 [simple_merge.py](../../src/cptla/evaluation/simple_merge.py) 与 [cross_page.py](../../src/cptla/evaluation/cross_page.py) 可复用部分合并和评价逻辑，但尚不等于已具备 R0 给定同表片段的 B0/B1、规范化网格、结构/内容联合 exact、人工修复诊断及加权分析入口。

## 决策与下一步

1. 可以开始 G0/P0/P1 的开发与小范围验证，直接利用服务器现有 train 数据，首轮不需要重新下载整个数据集。
2. 先建立独立的 train 输入清单、标签文件、文档/近重复簇划分和采样规则，再核验 20 个坐标案例。此前三份字段探针不算这 20 个图像案例验收。
3. 随后准备 200 张 train-fit 分层审计及强规则基线，估计可修复空间，完成派生标签审计。双人独立复核仍需实际落实，不能由 Agent 单人复看代替。
4. G0/G1 通过后，才进入新骨干环境、直接 SFT 和结构模块 smoke。当前没有新模型全量运行或训练就绪结论。

本轮只将核验结果与下一步写入本地三层记录；实际新增代码、服务器产物和训练任务均尚未开始。
