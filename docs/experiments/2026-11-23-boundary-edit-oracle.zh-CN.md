# 200 张表的跨页边界编辑上界诊断

2026-11-23 北京时间。CPU 任务已完成。问题是在固定 Paddle 页内预测、固定现有列映射、不重新识别文字的条件下，跨页边界保留、删除或合并动作能够覆盖多少整表结构错误。

## 协议

- PubTables-v2 固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，历史 200 张 train_fit 表。固定同表组和片段先后顺序，沿用 image-only Paddle 预测。上游版本及来源见 [200 表复评](2026-11-22-paired-reconstruction-pilot.zh-CN.md#200-表误差分解)。
- 逐表按输入清单核对 group、片段身份、页码和顺序。真值 SHA 与历史评分记录一致。170/200 张通过原列映射，其中 166 张为真值列宽。30 张列映射失败保留在全分母，4 张宽度与真值不同也无法通过本动作目录修复。
- 在后续片段开头保留所有行，或删 1–3 行。精确目录要求与首片段前缀在文字、结构和角色上相同，且删行处不切开 rowspan。宽松目录只验证后续片段的 rowspan 安全，可能删除正文，属于诊断性搜索。前缀均不得删空片段。
- 可选合并目录要求前片段末行与后片段删前缀后的首行均不含跨行单元格或表头，两行横向单元格边界必须相同。相应非空文本按原顺序以一个空格连接。没有替换预测文本。
- 真值只用于离线计算每套动作中存在多少与真值精确匹配的路径。拓扑比较行列跨度，联合匹配另要求展开文本逐格全等。动态规划合并等价状态，保留各组路径数及示例。路径数大于 1 表示仅凭该得分无法唯一决定编辑动作。上述口径为项目严格诊断指标。

## 结果

| 条件 | 结构完全匹配 | 相对历史启发式 | 结构匹配动作有歧义 | 结构与文字联合全等 |
| --- | ---: | ---: | ---: | ---: |
| 历史强启发式 | 69/200 | — | — | 3/200 |
| 保留或删精确重复前缀 | 72/200 | +1.5 个百分点 | 2 张 | 3/200 |
| 精确前缀加边界行合并 | 80/200 | +5.5 个百分点 | 50 张 | 3/200 |
| 保留或删跨度安全前缀 | 80/200 | +5.5 个百分点 | 27 张 | 3/200 |
| 跨度安全前缀加边界行合并 | 81/200 | +6.0 个百分点 | 53 张 | 3/200 |

扩展动作目录可以提高真值辅助的结构覆盖。全表联合精确匹配始终只有 3 张。精确前缀加边界行合并相较历史启发式多匹配 11 张，其中 4 张动作路径唯一，最歧义的一张有 210 条拓扑全等路径。

进一步单列精确前缀目录引入合并才达到结构匹配的 8 张表。每表精确拓扑路径数与仅要求总行数正确时的路径数一致，说明在这 8 张表中，仅用拓扑无法辨认正确的边界合并。下面两项固定文字守门仅作事后诊断。两侧各有非空单元格且非空列互补的约束下，8 张全部缺少可行路径。改用左首列非空、右首列空的较弱约束后，只有 PMC11181895-table-0 保留一条路径。所有合并路径都未实现联合全等，并且没有任何一条路径的全部合并行文本恰好等于真值。具体片段顺序与编辑动作、涉及的预测文本及对齐真值行可供人工复核。

| 表 ID | 拓扑全等路径数 | 行数匹配路径数 | 联合全等路径数 |
| --- | ---: | ---: | ---: |
| PMC12072187-table-1 | 1 | 1 | 0 |
| PMC12193938-table-2 | 1 | 1 | 0 |
| PMC11830496-table-0 | 2 | 2 | 0 |
| PMC10806231-table-0 | 1 | 1 | 0 |
| PMC11181895-table-0 | 2 | 2 | 0 |
| PMC12154909-table-0 | 5 | 5 | 0 |
| PMC10674981-table-0 | 4 | 4 | 0 |
| PMC11416846-table-1 | 3 | 3 | 0 |

观察到的 +5.5 个百分点不能作为可实际学习的边界合并收益，也不能代替 G1 的独立人工审计。下一步优先核查保留/去重动作的唯一性和文本证据，同时保留 30 张不等列失败作为独立诊断层。避免将结构正确的任意编辑路径直接用作合并正标签。

## 复现与证据

- 主报告 `artifacts/reconstruction-diagnostics/20261122T165111Z-boundary-oracle-200/report.json`，SHA256 `c4af0c67b6dd3dc053e26ac8bc162533a31fa06ef01dbe3622ca5398e2e61874`。含输入 SHA、配置、覆盖及逐表路径。代码本地和服务器副本 SHA256 `6a5597618b91c13454a98b890bbeb7d46cf38e7d8de09bb713c3fdbbab197f06`，脚本不加载权重。执行使用现有服务器 Python 3.12.7 环境，GPU 禁用，无随机抽样或下载。Ruff 检查通过，六项合成检查验证保留/去重、松弛去重、合并、路径歧义和连锁合并。
- 8 例报告 `artifacts/reconstruction-diagnostics/20261122T165346Z-boundary-merge-review/cases.json`，SHA256 `188daadc2114613d3ae22db65961b5185b5b6e0cee6a69f076e0c98a4946986d`。同目录保留实际执行的 `trace_boundary_candidates.py`，SHA256 `6547e3f19946e247ea92b896b099ab2d40f53a4dc03d47fe46348ed149a5229b`。输入来自主报告和原固定预测，逐例记录所有匹配路径。
- 主审计完整命令如下。目录已存在，复执行须使用新时间戳目录作为输出。源数据和历史产物均保留。

```bash
cd /data01/public/zhengguojie/paper
run=artifacts/reconstruction-diagnostics/20261122T165111Z-boundary-oracle-200
PYTHONPATH=src CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 \
  .venvs/20261114T095359Z-qwen-env/bin/python "$run/audit_reconstruction_boundary_oracle.py" \
  --project-root /data01/public/zhengguojie/paper \
  --baseline artifacts/reconstruction-baselines/20261114T153243Z-200table-alignment \
  --inputs artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/inputs.jsonl \
  --targets artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/targets.jsonl \
  --output "$run/report.json"
```
