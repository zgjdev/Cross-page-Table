# dots.ocr 两层 HTML 过滤审计

日期：2026-10-23（Asia/Shanghai）。状态：脚本本地实现，服务器审计待运行。

研究问题：区分页级提取器拒绝、XML 评分解析拒绝及两者的页面重叠，判断普通 HTML 格式差异与结构残缺各有多少证据。输入为固定 PubTables-v2 Full Documents validation 的 13,871 页 dots.ocr 四段旧预测、旧 no_merge adapter 与评分失败清单；不读取 GT 或 test，不使用 GPU、不下载数据、不修改原始输入。数据 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，模型 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，赛道 `image-only`。旧实验命令和路径见 [离线评测记录](2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md)。

新入口 `scripts/audit_dotsocr_html.py`，诊断模块 `src/cptla/evaluation/html_audit.py`。对所有预测自动统计，只人工审阅每个诊断桶按固定分片/布局顺序的前三例。种子不适用，确定性顺序抽样，不把前三例当随机代表。词法探针仅尝试 void 标签闭合、实体和裸 ampersand 的 XML 拼写兼容性；不补行、列或单元格，探针结果不是已验证修复，也不用于评分。样本原始 HTML 只保存在服务器新产物目录。

环境与验证：本地 `.venv/Scripts/python.exe` 为 Python 3.12.7；诊断、端到端对账/禁止覆盖及已有提取器共 13 项测试通过，Ruff/diff check 通过。测试临时根显式使用 `artifacts/test-runs/20261023-html-audit-local-02`；默认 Windows 临时目录权限失败、首次自定义父目录缺失的检查均未进入集成测试。本地相关 adapter 回归被缺少 `pylcs` 阻塞，将在服务器 `.venvs/eval312/bin/python` 环境执行；不能据此声称全部通过。

预期产物为新的 `artifacts/html-audits/<时间戳>-dots-html-filter-audit/`，包含逐表诊断、分桶样本、输入前后 SHA-256 和运行元数据。尚无新增指标，不启动全量复评；需先依据审计判断安全可验证的规范，并在 train/合成样本上冻结后才评 val。
