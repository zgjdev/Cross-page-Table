# dots.ocr 两层 HTML 过滤审计

日期：2026-10-23（Asia/Shanghai；下文运行时刻使用 UTC）。状态：三轮 CPU 审计已完成；尚未更改评分协议或重新评分。

研究问题：区分页级提取器拒绝、XML 评分解析拒绝及两者的页面重叠，判断普通 HTML 格式差异与结构残缺各有多少证据。输入为固定 PubTables-v2 Full Documents validation 的 13,871 页 dots.ocr 四段旧预测、旧 no_merge adapter 与评分失败清单；不读取 GT 或 test，不使用 GPU、不下载数据、不修改原始输入。数据 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，模型 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，赛道 `image-only`。旧实验命令和路径见 [离线评测记录](2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md)。

新入口 `scripts/audit_dotsocr_html.py`，诊断模块 `src/cptla/evaluation/html_audit.py`。对所有预测自动统计，只人工审阅每个诊断桶按固定分片/布局顺序的前三例。种子不适用，确定性顺序抽样，不把前三例当随机代表。词法探针仅尝试 void 标签闭合、实体和裸 ampersand 的 XML 拼写兼容性；不补行、列或单元格，探针结果不是已验证修复，也不用于评分。样本原始 HTML 只保存在服务器新产物目录。

环境与验证：本地 `.venv/Scripts/python.exe` 为 Python 3.12.7；诊断、端到端对账/禁止覆盖及已有提取器共 13 项测试通过，Ruff/diff check 通过。测试临时根显式使用 `artifacts/test-runs/20261023-html-audit-local-02`；默认 Windows 临时目录权限失败、首次自定义父目录缺失的检查均未进入集成测试。本地相关 adapter 回归被缺少 `pylcs` 阻塞，将在服务器 `.venvs/eval312/bin/python` 环境执行；不能据此声称全部通过。

预期产物为新的 `artifacts/html-audits/<时间戳>-dots-html-filter-audit/`，包含逐表诊断、分桶样本、输入前后 SHA-256 和运行元数据。尚无新增指标，不启动全量复评；需先依据审计判断安全可验证的规范，并在 train/合成样本上冻结后才评 val。

## 执行检查点（2026-10-23 05:59 UTC）

状态：运行中。代码提交 `a0c3bb0` 已快进同步到服务器，服务器工作区启动前干净。服务器 `.venvs/eval312/bin/python` 下新审计与原 dots/runner/document/simple_merge/cross_page 共 53 项测试通过。

执行命令（项目根目录内）：

```bash
PYTHONPATH=src .venvs/eval312/bin/python scripts/audit_dotsocr_html.py \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl \
  --predictions outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl outputs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.jsonl outputs/baselines/dots-ocr/20261020T015543Z-dots-full-val/predictions.jsonl \
  --adapter-dir artifacts/cross-page-adapters/20261020T123212Z-dots-full-val-offline-no-merge \
  --failures artifacts/cross-page-scores/20261020T123212Z-dots-full-val-offline-no-merge/failures.jsonl \
  --output-dir artifacts/html-audits/20261023T055916Z-dots-html-filter-audit
```

由当前 SSH 会话维护，非后台任务；完成条件为命令退出 0、输入/adapter/失败清单完整对账、输入前后哈希一致并写出 `summary.json`，然后审阅 `samples.jsonl`。尚未完成。

## 第一轮审计完成（2026-10-23 06:00 UTC）

退出码 0，13,871 页、2,752 条 adapter 表和 637 条评分拒绝逐项对账，输入前后 SHA 全一致。评分拒绝分为词法兼容候选 582、未解决 55；前层拒绝 1,324 条。前层警告涉及 1,168 页、后层拒绝涉及 622 页，两个页面集合交集为 0。不能用这些计数证明原图有同样数量的独立真表，也不能用词法可解析证明结构/文字正确。

抽查发现前层拒绝多为布局元素只有 bbox/category、没有 text；后续只读全量核对为 1,315 条缺 text、9 条有字符串但未通过完整 table 包装检查；没有其他字段保存 HTML。为使这项发现可复算，扩充脚本保存字段键、输入类型、错误类型和根表数量统计，并细分样本桶，计划在新的时间戳目录独立运行，不覆盖第一轮产物。

## 第二轮与原始输出核对

第二轮目录 `artifacts/html-audits/20261023T060600Z-dots-html-filter-audit-v2/`，代码 `50d22be`，实际开始约 06:02:39 UTC，结束 06:03:28 UTC。目录中的时间字符串是标识，不作为实际启动证据。全部主要计数与第一轮相同，输入前后哈希一致；细分样本的开头/结尾、标签和字段已审阅。

只读进一步核对缺 text 对应的 1,159 页：全部布局元素都无 text，原始字符串不包含字面 `"text"` 键或 `<table`。直接 JSON 解析均报告 Extra data，抽样尾部为 `<|endofassistant|>`；这解释了抽样的 JSON 修复需要，但**不能推断 JSON 修复删除了表格内容**，因为原串根本没有 HTML。该结论针对已生成输出，不证明图像真的有表格或模型检测框正确；推理为何只生成布局仍待对照验证。

样本线索（均为诊断，不是 GT 正确性确认）：

- `PMC10170702_page_3.jpg`：完整表中有 `<br>`；XML 报 mismatched tag，词法探针可解析。
- `PMC10251383_page_1.jpg`：单元格 `Author & year` 的裸 `&` 被 XML 拒绝。
- `PMC10805880_page_6.jpg`：HTML `&nbsp;` 实体导致 XML undefined entity。
- `PMC10377578_page_5.jpg`：一个布局 text 中存在多个 table 根，不能简单把整个 text 当成一张表；表格拆分与 bbox/来源对应需另定协议。
- `PMC10801101_page_2.jpg`：完整 table 后有标题段落，外层包装检查拒绝；与真正截断的 8 条字符串分开处理。
- `PMC10157785_page_9.jpg`：有内嵌标签不平衡；其余“探针未解决”还包括科学比较符号等，不能把 55 条全部判成模型结构损坏。
- `PMC10167337_page_35.jpg`：表格布局元素只有 bbox/category，无任何正文。不可用 HTML 规范化补出内容。

本地模型快照 `checkpoints/dots-ocr/README.md` 的 transformers 示例要求 Table 输出 HTML；其 prompt 与本项目压缩版语义相近但不逐字相同，无法据此认定提示词是根因。README SHA-256 `e59f00e56945936a65c74cf53333a9051715ba45e91da0b7d86cd05f5964c2eb`。未核实当前上游最新管线，未将本地运行冒称官方完整复现。

第三轮运行代码 `db2cf36`，实际开始约 06:05:30 UTC，使用同一命令，仅输出目录改为 `artifacts/html-audits/20261023T060500Z-dots-html-filter-audit-v3/`；增加原串缺字段统计与小规模样例。服务器相关 53 项回归再次通过，旧评分 7 项 SHA 再核验均 OK。该轮仍为 CPU 审计，无 GPU、新下载、GT/test 读取或新模型性能指标。

## 最终验收（2026-10-23 06:06 UTC）

第三轮 06:06:23 UTC 正常退出（0），自动复核了全部 13,871 页。两轮最终诊断/样本文件哈希相同；第三轮 summary 补充了 1,159 页的原始字符串证据。最终产物位于上述 v3 目录：

- `summary.json`：命令、Python/代码版本、全部输入 SHA、两层计数、原串证据和输出 SHA。
- `table-diagnostics.jsonl`：4,076 条布局 Table 候选诊断（不是独立 GT 表数）；SHA-256 `2db904ec11b9a26bcbfd68f536b5af0aa4936cf96c4157aabea556e6b4d90ce6`。
- `samples.jsonl`：分桶小样本原始 HTML；SHA-256 `f6d72d543102e7471422ce1d02459b69b9ed468033b3d5582e77ffdfc6c2080b`。

| 检查项 | 结果 | 能支持的结论 |
| --- | ---: | --- |
| 旧预测提取后的评分解析拒绝 | 637 | 其中 582 为有限词法兼容候选，55 本探针未解决；不是 637 张全为结构预测失败 |
| 旧推理阶段拒绝的布局候选 | 1,324 | 1,315 条没有 text；9 条有字符串，其中 8 条未闭合/截断、1 条完整 table 后跟标题段落 |
| 原串无任何 text/HTML 的页面 | 1,159 | 现存输出只包含布局；解析器无法还原缺失内容，具体推理原因待查 |
| 两阶段拒绝的页面交集 | 0 | 当前两组发生在不同页面；仍不能把候选数等同于 GT 丢表数 |
| 原输入前后 SHA-256 | 全一致 | 没有修改旧预测、adapter 或失败清单 |
| 旧正式评分的 7 项 SHA 校验 | 全 OK | 旧结果原样保留，未产生新分数 |

结论：已有输出同时存在 HTML/XML 兼容损失和缺少表格内容两类问题。只修评分不能覆盖所有问题；也不能把格式兼容失败直接视作模型结构错误。582 条仅证明词法探针后可被 XML 读取，不证明单元格文本/行列/span 保真，探针不作为正式修复。HTML 容错、多个 table 的分离、科学比较符号与内嵌格式的文本语义需在 train/合成案例上先形成明确规范；禁止按 val 真值修表。

下一步（尚未执行）：

1. 本地实现保守、显式版本化的 HTML 规范化方案，以 train/合成样例核验文本、单元格和 span 保真；保留无法确定的失败，不自动补内容。验证通过后在服务器新目录用固定旧预测做配对复评。
2. 在 train 上选择固定完整文档小样本，核对官方逐字 prompt、模型 chat 模板与解码设置，做原 prompt/官方 prompt 的受控短推理，记录文字输出覆盖与耗时；GPU 检查通过后才运行。当前没有证据把 1,159 页的缺内容归咎于某个设置，也不据 val GT 调 prompt。
3. 处理后再区分跨页续接、列对应、重复表头和拆分行错误；POTATR 制品核验及 155 次规则接受审计仍未执行。本轮无后台遗留任务。
