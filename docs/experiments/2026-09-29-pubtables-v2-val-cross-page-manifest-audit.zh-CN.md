# PubTables-v2 validation 跨页表清单与官方续接页面对审计

日期：2026-09-29（UTC；服务器审计开始约 09:34:49 UTC，产物核验截至 09:35:21 UTC）
状态：**已完成阶段 0 数据审计；尚未开展模型推理或训练**。
研究问题：从真实完整文档中严格区分跨不同页面的逻辑表、同页多片段表及官方相邻页续接正负例，为后续四模型对照固定评测范围。

## 1. 固定条件与输入

- 数据集：PubTables-v2 `Full Documents/val`，revision `aa575e798cb00a296925e2086addb3e3fd9a1903`。
- validation 页面：`data/pubtables-v2/extracted/Full Documents/val/images/`；既有全页 manifest：`artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。
- 真值：`val/tables/*_tables.json` 的同一逻辑表 `parts.page_num`（出现至少两个**不同**页面时记为跨页表）；官方续接关系：`val/cross_page_table_pairs/*.json` 的 `page_A/page_B/label`。`train/tables`、`test/tables` **仅枚举文件名**做文档 ID 泄漏检查，不读取 test 内容。
- 页面清单包含无表页，**未用 GT 筛选模型输入**；本阶段没有模型输入或指标。表格对象的序号 ID 是项目由源文件内顺序派生的稳定 ID，不是官方发布的细粒度关系 ID。
- 输入赛道：不适用（仅审计公共真值清单，后续仍须分开报告 `image-only` 和 `PDF-text-assisted`）。模型/权重 revision：不适用；GPU：未使用；随机种子：无随机步骤。Python 3.12.7，pytest 8.4.2，Ruff 0.16.8；代码基础 commit `e6154932b8efe43c98cee6e02f18ea017969aa41`，新增脚本在本次审计时尚未提交，脚本 SHA-256 `b2c642e4c518d884cc533c91df41fd65ec1038553ff8dae025152b7e4adb3ab9`。

## 2. 实际命令与输出

正式审计运行命令（于仓库根目录执行，`RUN_ID` 为运行时 UTC 时间戳）：

```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-cross-page-val-audit"
PYTHONPATH=src .venvs/eval312/bin/python scripts/build_cross_page_manifest.py \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl \
  --images 'data/pubtables-v2/extracted/Full Documents/val/images' \
  --tables 'data/pubtables-v2/extracted/Full Documents/val/tables' \
  --pairs 'data/pubtables-v2/extracted/Full Documents/val/cross_page_table_pairs' \
  --train-tables 'data/pubtables-v2/extracted/Full Documents/train/tables' \
  --test-tables 'data/pubtables-v2/extracted/Full Documents/test/tables' \
  --output-dir "artifacts/cross-page-manifests/$RUN_ID"
printf 'RUN_ID=%s\n' "$RUN_ID"
```

主 run ID：`20260929T093449Z-cross-page-val-audit`。输出在 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/`：

| 文件 | 内容 | 行数 | SHA-256 |
| --- | --- | ---: | --- |
| `gold-cross-page.jsonl` | 跨不同页的逻辑表、`parts` 来源和真值 HTML | 983 | `77797673d5d166e2203f5a5b14cac9661d963c54a6931ea8dda491ca3deb25d9` |
| `official-page-pairs.jsonl` | 官方正负相邻页对；附带**派生的**逻辑表候选 ID，不将其称官方列标签 | 2,062 | `65be030b881270d5158f95390869a2f1d3db209ee5cb343ce4414235a92604bb` |
| `negative-page-pairs.jsonl` | 官方 `label=0` 页面对 | 786 | `d2cb05aa3fe3bc448a07e353493e0ceb07b4a9e07633f3f29d4c99c716eae51f` |
| `nonadjacent-part-gaps.jsonl` | 同一表跨非相邻页面的独立异常清单 | 1 | `9e24dea4c98b29e24df93f6f13427f9ba1359c54599b067f0e0e21ef9491fb73` |
| `discrepancies.jsonl` | 官方页面对与相邻逻辑表片段不一致项 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `summary.json` | 覆盖、来源、分层统计和各 JSONL 的校验和 | 1 | `a040b6230ccdfdbd6a004d6590095cf8cfc1aecc0830e6dee6839a251e4d3e92` |

另有首次审计产物 `artifacts/cross-page-manifests/20260929T093222Z-cross-page-val-audit/`，**保留不覆盖**；它与正式运行的共同清单哈希一致，但首次脚本仅汇总非相邻页计数，没有保存独立 gap 清单。正式运行是在增加该清单与回归测试后重新生成的新目录。没有单独保存服务器 stdout 日志文件；状态与摘要保存在 `summary.json`，产物经独立 `sha256sum` 及结构化 JSON 复核。

## 3. 覆盖与核验结果

| 项目 | 实测 |
| --- | ---: |
| validation 文档 / 全部页面 | 935 / 13,871 |
| 总逻辑表数 | 2,587 |
| 跨不同页逻辑表数 / 来源文档数 | 983 / 869 |
| 多片段但仅同页的逻辑表（已排除） | 63 |
| 跨 2/3/4/5 页表 | 801 / 127 / 31 / 10 |
| 跨 6/7/8/9/10 页表 | 5 / 4 / 2 / 1 / 2 |
| 官方续接正例 / 负例 | 1,276 / 786 |
| 官方页对与相邻逻辑表片段的差异 | 0 |
| train / validation / test 文档 ID 数 | 7,359 / 935 / 878；无交叉 |
| 全页 manifest 缺失/额外/重复 | 0 / 0 / 0（与原图目录完整列表一致） |
| 输出 JSONL 哈希重新校验 | 5/5 一致 |

**特殊案例：**`PMC12274235-table-1` 的 `parts.page_num=[4,5,7]`，第 6 页图像存在，但该表的片段不在第 6 页。第 5→7 页是同一逻辑表的非相邻部分，**不得**把它当成官方相邻页续接正例或假造 page 6 的表格片段。记录已单独写到 `nonadjacent-part-gaps.jsonl`；该异常与官方相邻页标签的零差异不矛盾。

## 4. 测试、错误和边界

- 新脚本：`scripts/build_cross_page_manifest.py`；测试：`tests/test_build_cross_page_manifest.py`。使用项目内 `.venvs/eval312` 与 `PYTHONPATH=src:third_party/grits-main` 的全量回归：**115 passed**；新增测试涵盖同页跨栏、非相邻片段、正负标签不一致、跨 split 重叠、缺页和重复官方页对。Ruff 与 `git diff --check` 通过。
- 一次全量测试收集因忘记设置 vendored GriTS 的 `PYTHONPATH` 而报 `ModuleNotFoundError: grits`；随后在同环境补上 `third_party/grits-main` 重跑通过。该失败不影响审计产物。
- **已提供**：原始 `parts`、官方页面对标签及保存的输入/输出与校验和。**推断/项目定义**：`parts` 中不同页的数目决定 cross-page-only 子集；附在官方页面对上的候选表 ID 为派生关联。**待核验**：同页与跨页细粒度列对应、重复表头和拆分行标签；尚未人工审计，也未从本阶段得到模型准确率。
- 本阶段只保证文档 ID 不跨 split（test 仅读文件名），不保证相似模板、近重复论文或来源 HTML 跨数据集无泄漏；后续训练/外部基准比较前须另做近重复与标签审计。

## 5. 下一步

保持本轮产物不变。在 `train` 开发跨页预测表与全体真值表的文档级一对一匹配、来源页审计和跨页子集评分单元测试；在 validation 上校验协议。之后再评估是否下载 OCRFlux-3B/MinerU-Popo/PaddleOCR-VL-1.5 并安排 GPU smoke；目前仍不启动 GPU、模型微调或 test 评估。
