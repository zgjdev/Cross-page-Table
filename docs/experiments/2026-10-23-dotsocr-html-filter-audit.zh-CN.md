# dots.ocr 两层 HTML 过滤审计

日期：2026-10-23（Asia/Shanghai）。状态：脚本本地实现，服务器审计待运行。

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
