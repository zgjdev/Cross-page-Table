# 接管前 dots.ocr Full Documents 结果核验（2026-09-22）

## 1. 核验目的与状态

状态：已完成只读核验。

核验时间：2026-09-22（Asia/Shanghai）。

服务器项目根目录：`/data01/public/zhengguojie/paper`。

本记录用于确认接管项目之前是否已经运行过 PubTables-v2 Full Documents，并界定该历史结果与当前严格评测协议的差异。核验过程中未修改服务器文件。

## 2. 已核验证据

历史输出目录：

`outputs/baselines/dots-ocr/c0111ce6bc07803dbc267932ffef0ae3a51dc951/validation/`

其中：

- `predictions-part0.jsonl`：1,761 条；
- `predictions-part1.jsonl`：1,761 条；
- 合计 3,522 条且页面键唯一；
- `metrics.json`：历史正式指标；
- `metrics-partial.json`：早期 8 文档的部分评分，不作为最终结果。

对应日志：

- `logs/models/dots-ocr-validation-part0.log`
- `logs/models/dots-ocr-validation-part1.log`
- `logs/models/dots-ocr-validation-scoring.log`

预测记录中的图像路径明确指向：

`data/pubtables-v2/extracted/Full Documents/val/images/`

因此“接管前运行过 PubTables-v2 Full Documents validation”是已核验事实。

## 3. 输入覆盖核验

对以下三个页面集合进行了只读集合比较：

1. `Full Documents/val/images/*.jpg` 的全部页面；
2. 两个历史 predictions 分片中的页面；
3. `Full Documents/val/tables/*_tables.json` 中所有 table `parts.page_num` 对应的页面。

结果：

| 集合或关系 | 数量 |
| --- | ---: |
| validation 全部页面 | 13,871 |
| validation 真值文档 | 935 |
| 真值表格所在页面 | 3,522 |
| 历史预测页面 | 3,522 |
| 历史预测与真值表格页交集 | 3,522 |
| 历史预测中不属于真值表格页 | 0 |
| 真值表格页中缺少历史预测 | 0 |
| validation 全页中未推理页面 | 10,349 |

结论：历史输入不是 Full Documents validation 的全部页面，而是由真值表格位置筛选出的页面集合。该做法覆盖了全部 935 篇真值文档的目标表格页，但排除了无表页和其他非目标页，会降低端到端表格检测中的假阳性机会。

## 4. 历史结果

历史 `metrics.json` 保存的结果为：

| 项目 | 结果 |
| --- | ---: |
| documents scored | 935 |
| pages seen | 3,522 |
| page inference error | 0 |
| page parse error | 0 |
| invalid table HTML | 838 |
| predicted tables | 2,928 |
| GriTS-Top | 0.6563578710 |
| GriTS-Con | 0.6216124466 |
| Acc-Top | 0.2759953614 |
| Acc-Con | 0.1379976807 |

旧指标文件中的 `scope` 为 `full_validation`，但旧评分脚本只按真值目录枚举 935 个文档，没有检查 13,871 个页面是否全部出现。因此该字段表示“对全部 validation 真值文档评分”，不表示“对 validation 全部页面完成推理”。

## 5. 跨页处理核验

初始代码 commit `44951a9` 中的 `scripts/score_dotsocr_pubtables_v2.py` 将各页面检测出的合法 table HTML 按 document ID 加入预测集合，再与文档级真值表集合匹配。代码没有 continuation 分类、相邻页关系判断、重复表头处理或跨页 HTML 合并。

因此历史结果是“逐页识别后按文档汇总的未合并结果”，不能表述为跨页表格恢复结果。

## 6. 可用结论与限制

### 已提供/已核验

- 接管前确实运行过 dots.ocr on PubTables-v2 Full Documents validation；
- 覆盖 935 个文档、3,522 个真值表格页；
- 所有 3,522 个页面推理状态为 `ok`；
- 保存了可复查的 predictions、日志和指标；
- 没有执行跨页合并。

### 不能据此声称

- 不能声称覆盖了 validation 全部 13,871 页；
- 不能声称完成了当前严格协议的 Full Documents 端到端评测；
- 不能把该结果解释成跨页合并或跨页恢复性能；
- 不能与不使用真值筛页的公开 Full Documents 结果直接作公平排名。

### 待核验

- 历史推理的完整启动命令和当时 GPU 环境没有独立 run manifest；如论文需要精确复现，应从项目内日志、Git 历史和现存环境继续恢复，不得凭记忆补写。

## 7. 后续处理

保留所有历史产物不变。在论文实验表中如需引用，应标注为：

> dots.ocr historical validation run, image-only, ground-truth table-page filtered, no cross-page merging.

当前严格基线仍需对 `Full Documents/val` 的全部 13,871 页重新推理，并通过 missing、extra、duplicate 均为 0 的覆盖门禁。
