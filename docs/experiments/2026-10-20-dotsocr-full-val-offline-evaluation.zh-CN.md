# dots.ocr Full Documents/val 全量离线跨页评测

## 启动检查（2026-10-20 12:32 UTC）

- **状态：计划启动。**研究问题：固定 dots.ocr `image-only` 逐页预测在完整文档的无合并及预先冻结的重复表头简单合并基线下，跨页整表恢复程度如何。只在 PubTables-v2 Full Documents/val 评估，不改规则、不读取 test，不与 PDF-text-assisted 混算。
- 数据 `kensho/PubTables-v2` revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，validation 935 篇/13,871 页；全页 manifest `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`（SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`）；真值 `data/pubtables-v2/extracted/Full Documents/val/tables/` 和 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl`，仅用于离线评分。
- 模型 `rednote-hilab/dots.ocr` 本地权重 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`；推理固定 `max_new_tokens=24000`、`do_sample=False`、无采样随机种子。代码 HEAD `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d`，工作树包含尚未提交的推理修复与记录，离线适配、合并、评分脚本未修改。
- 四个只读预测输入，按 manifest 连续顺序：`outputs/baselines/dots-ocr/{20261006T172527Z,20261010T024700Z,20261017T081912Z,20261020T015543Z}-dots-full-val/predictions.jsonl`；分别 6,151/636/6,844/240 条，合计 13,871；已审计唯一、无缺页、13,869 `ok` / 2 `error`。各分片 SHA 与终态详见 `docs/experiments/2026-10-20-dotsocr-full-val-last-240-resume.zh-CN.md`。
- 运行 ID `20261020T123212Z-dots-full-val-offline`。环境 `.venvs/eval312/bin/python`、`PYTHONPATH=src:third_party/grits-main`；**CPU-only，无 GPU、无下载、无训练、原始数据和旧产物只读**。新适配产物 `artifacts/cross-page-adapters/<ID>-no-merge/`，合并产物 `artifacts/cross-page-merges/<ID>-simple-merge/`，两份分数 `artifacts/cross-page-scores/<ID>-{no-merge,simple-merge}/`，执行日志 `logs/cross-page-scores/<ID>/`。每个脚本要求输出目录不存在，不覆盖任何已有文件。

## 预定执行顺序

1. `PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/adapt_dotsocr_document_predictions.py --manifest <上述 manifest> --predictions <上述四个预测路径依序> --output-dir artifacts/cross-page-adapters/<ID>-no-merge`
2. `PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/score_cross_page_predictions.py --manifest <上述 manifest> --page-results <适配目录>/page-results.jsonl --document-tables <适配目录>/document-tables.jsonl --truth-dir 'data/pubtables-v2/extracted/Full Documents/val/tables' --cross-page-gold artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl --output-dir artifacts/cross-page-scores/<ID>-no-merge`
3. `PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python scripts/merge_dotsocr_repeated_header.py --manifest <上述 manifest> --adapter-dir <适配目录> --images 'data/pubtables-v2/extracted/Full Documents/val/images' --output-dir artifacts/cross-page-merges/<ID>-simple-merge`
4. 同步骤 2，但 `--document-tables` 改为合并目录下的 `document-tables.jsonl`，`--output-dir` 改为 `artifacts/cross-page-scores/<ID>-simple-merge`。两条评分均按完整覆盖严格模式，不传 `--partial`。计算结束后核对覆盖、失败、指标与 SHA-256，并追加实测时间/状态/结论边界。

## 运行检查点（2026-10-20 12:33 UTC）

- **运行中。**四分片严格适配命令按第 1 步执行，正常退出（0）。日志 `logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/adapter.log`；产物 `artifacts/cross-page-adapters/20261020T123212Z-dots-full-val-offline-no-merge/summary.json`。完整覆盖 13,871/13,871，duplicates/extra/missing 全 0；935 文档，2,752 张未合并预测表，2 页 error，1,324 条 runner warnings。三个适配输出 SHA-256 见 summary；原四段输入 SHA 在 summary 内逐段保存。
- 已启动第 2 步无合并严格全量评分（CPU）；日志 `logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/no-merge-score.log`；进程由本轮命令会话维护，尚未完成/无指标。未启动 GPU、未下载或修改旧产物。

## 后台接管（2026-10-20 12:35:55 UTC）

- 用户要求关闭 VS Code 后继续运行。原交互进程 PID `1255832` 在写入评分目录前由本轮发送 SIGINT 终止（退出 130，栈见 `no-merge-score.log`）；无合并分数当时**未生成**，该次中断不算模型失败。
- 新增 `scripts/run_dotsocr_full_val_offline_background.sh`，`bash -n`、`git diff --check` 通过。后台完整命令：`systemd-run --user --unit=paper-dots-eval-20261020T123212Z --description='dots.ocr full validation offline paired scores' --property=WorkingDirectory=/data01/public/zhengguojie/paper --property=Type=exec --property=StandardOutput=append:/data01/public/zhengguojie/paper/logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/background-events.log --property=StandardError=append:/data01/public/zhengguojie/paper/logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/background-events.log /usr/bin/bash scripts/run_dotsocr_full_val_offline_background.sh 20261020T123212Z-dots-full-val-offline`。
- 启动后 `paper-dots-eval-20261020T123212Z.service` 为 `active/running`，wrapper PID `1269023`；`background-events.log` 记录 `START 2026-10-20T12:35:55Z` 和 `STEP no_merge score`；单步日志为 `background-{no-merge-score,simple-merge,simple-merge-score}.log`。按预定四步顺序，三步全成功才写 `background-checksums.sha256`；退出会记录 `END ... status=...`。本时点尚无评分结果。
- **持久性限制：**`loginctl show-user` 检查 `Linger=no`，检查时有 7 个登录会话。用户级 unit 与本次 VS Code 命令会话独立；关闭 VS Code 后若仍有其他会话通常可继续，但**最后一个会话退出后可能被 systemd 停止**。启用 linger 需修改项目目录外的系统设置，现有项目约束未授权；在获明确授权/管理员执行前不能保证完全无会话运行。

## 运行与结论

### 中途检查点（2026-10-20 13:12 UTC）

- 用户级 service 仍 `active/running`，`background-events.log` 已写 `STEP repeated_header merge`，说明 no-merge 评分子步骤已返回成功，合并与第二组评分**尚未完成**；不把单组结果冒充完整配对结果。无 GPU 任务变更或原始数据写入。
- 无合并评分产物 `artifacts/cross-page-scores/20261020T123212Z-dots-full-val-offline-no-merge/{metrics.json,matches.jsonl,failures.jsonl}`，分别已写出；coverage 13,871/13,871，missing/extra/duplicate 全 0；跨页 GT 983 张，匹配 643 张，但这只代表部分内容有正重叠，**不代表正确恢复了 643 张跨页整表**。cross-page GriTS-Con `0.4576991966`，内容网格 exact `0.0`；matched 跨页预测的来源页缺失计数 643（全部匹配项）；全表 GriTS-Con `0.5077936893`、内容网格 exact `0.0815616544`。错误页 2、非法 HTML 637、未匹配预测表 424。`metrics.json` SHA-256 `ba5e206bb7ac3d4c091d53eea29bc66c2740b6ab6f4de78c63c6d46e22bdff02`；`matches.jsonl` 983 行、`failures.jsonl` 637 行，后续总结束时按 `background-checksums.sha256` 核验三份文件。`cross_page.grits_con_precision` 仅对已匹配跨页 GT 的网格单元计分，**不是跨页表检测 precision 或误合并率**。
- 这是一组严格全页输入下的正式 no-merge 子结果，不能归纳为完整合并方案的增益或论文同协议的数字；待 service `END ... status=0`、第二组 metrics 和合并决策落盘后再配对比较并追加最终结论。

### 中途检查点（2026-10-20 13:17 UTC）

- 后台 `background-events.log` 已写 `STEP simple_merge score`，合并步骤结束、第二次严格全量评分正在运行。`artifacts/cross-page-merges/20261020T123212Z-dots-full-val-offline-simple-merge/summary.json` 显示 2,752 张输入表、1,213 个规则候选边界、**155 次规则接受**、2,597 张输出表；这些计数只说明规则动作，不表示 155 次合并全部正确。`decisions.jsonl` 保存每个候选的原因。`summary.json` SHA-256 `0a6ae6ae494b3fdd7b32dd2f2267ad2b960a319b4f6d486bb202b360a9a254c6`；文档表 SHA-256 `43cee955739ae2b6fdcf346cc8ff219834b1ca356fe7187e65bcbf24d0b6105e`。第二组 `metrics.json`、最终 exit/status 及完整校验和仍待核验，不能推测提升或误连率。

### 完成核验（2026-10-20 13:59 UTC）

- **已完成。**`background-events.log` 记录 `STEP all finished`、`END 2026-10-20T13:48:59Z status=0`；`paper-dots-eval-20261020T123212Z.service` 为 `inactive/dead`、`ExecMainStatus=0`。`sha256sum -c logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/background-checksums.sha256` 中两组 metrics/matches/failures 和合并 summary 共 7 项全部 `OK`；两组 `matches.jsonl` 均 983 行、`failures.jsonl` 均 637 行。第二组 metrics SHA-256 `fb40d5ae6d33399f1250b0b113c9f98ec23b9636d58fca109747855eb1e18cba`；原始预测/GT 均未修改。数据、模型、赛道、代码状态、命令、环境、完整输出位置及种子见本记录启动检查与后台接管段。
- 两组均严格覆盖 val 935 篇/13,871 页，missing/extra/duplicate=0；跨页 GT 983 张。`no_merge` → `simple_merge`：跨页 GriTS-Con `0.4576991966` → `0.5131445386`（差 `+0.0554453420`）；跨页内容网格 exact `0` → `0.0020345880`（按 983 张真值计为 2 张）；全表 GriTS-Con `0.5077936893` → `0.5479001476`（差 `+0.0401064584`），全表内容网格 exact `0.0815616544` → `0.0819482026`。匹配跨页表 `643` → `639`，来源页缺失匹配项 `643` → `527`，预测表 `2752` → `2597`；错误页仍 2、非法 HTML 仍 637。`matches` 数减少，不能把 GriTS 提升解释成全方位改进；来源页缺失是所匹配项的计数，并非跨页完整恢复率或续接 precision。
- **限制与下一步：**目前仅为冻结的保守规则相对同一上游的配对离线结果；没有验证 155 个接受边界是否真续表，也没有真实 train 正负例误连率、拆分行指标或完整续接 P/R/F1。下一阶段只读做配对案例/错误与合并决策审计，并在 train（不能用 val）补充误连核验；随后核验 POTATR 官方权重/续接器及其可复现性。`test` 仍不得用于调规则。

### 与 PubTables-v2 论文表 5/7 的可比性核查（2026-10-20 15:50 UTC）

- **原始证据：**项目根目录 `PubTables-v2:_A_new_large-scale_dataset_for_full-page_and_multi-page_table_extraction.pdf`，PDF 第 12 页表 5、第 14 页表 7 和第 13 页 §4.6（按文件页序，从 1 开始）；附录 PDF 第 22 页说明汇总指标的集合级 Hungarian + pseudo-F1 口径、第 23 页提到 Full Documents `test` 的 878 篇。论文表 7 `dots.ocr`：全表 GriTS-Con `0.5768`、Acc-Con `0.1180`；`dots.ocr + merging`：全表 GriTS-Con `0.6844`、Acc-Con `0.1180`。分类合并器是横拼相邻页输入的 ViT-B/16：判续接为正且预测表列数相同才纵向连接；**不是**本项目的相同重复表头/页边阈值规则。论文并未在表 7 报告我们构造的 983 张 validation 跨页真值子集指标。
- **当前实测对齐视角：**本实验用 validation 935 篇/13,871 页；与论文表 7 所列任务最接近的数字是本地 `full_document`，即 `no_merge` GriTS-Con `0.5077936893`、内容网格 exact `0.0815616544`，`simple_merge` GriTS-Con `0.5479001476`、exact `0.0819482026`；**不是**本地 `cross_page` GriTS-Con `0.5131445386`、exact `2/983`。这组 full-document 差距也真实存在：合并后 GriTS-Con 约低 `0.1365`，exact 约低 `0.0361`（小数分数）；但由于 split/规则/推理配置不一致，不能解释为同协议复现失败或直接宣称论文结果不可信。
- **追加失败线索（已提供，不等于定位根因）：**本地 adapter 输出 `2,752` 条未合并预测表，评分器跳过 `637` 条 `invalid_table_html`（约 23.1% 的 adapter 表，合并后同为 637 条）；该解析器调用 `third_party/grits-main/grits/conversion.py::html_to_cell_list`，内部使用 XML `ElementTree.fromstring`。只读抽样发现多个失败表包含普通 HTML 内嵌标签（例如 `<br>`、`<ul>`）或 HTML 截断；未检查全部失败类型，也未证明论文的预处理/HTML 容错策略如何，不能将 637 条全部归咎于模型或评分器。现有推理 prompt/权重 revision、预处理与论文官方推理配置是否相同仍**待核验**。
- **对先前口头比较的修正：**把跨页子集 `2/983` 直接与论文全表 `Acc-Con=0.1180` 比是**不同分母、不同任务范围**，会夸大差距；此前“跨页 2 张完全正确”仅指内容网格 exact、并未逐一审计来源页/合并路径，不能冒充严格跨页完整恢复的已核查成功数。历史数值不变，只更正解释。
- **下一步，保持 validation/test 隔离：**先只读按 GT 无关的格式原因归类失败 HTML 和上游表覆盖，再在 train 样本核对通用 HTML 解析/标准化方案与官方推理 prompt、处理顺序及表 7 评估实现；冻结任何修复后在新目录复评 val，不据 val 调阈值。另对 train 的官方正/负页对核验相同列数规则的误连/漏连；若要复现表 7，须取得同版本 ViT 权重、确立同一输入/归一化/后处理并在协议冻结后才评 test。不可把本地固定表头规则命名成论文 ViT + merging。

### 推理与评分链路只读审计（2026-10-20 15:56 UTC）

- **已确认的解析/覆盖风险：**从 val 935 份 `tables/*.json` 只读汇总真值共 `2,587` 张（其中跨页 983）。`scripts/evaluate_dotsocr_pubtables_v2.py` 的自定义 prompt + `src/cptla/evaluation/dotsocr.py::extract_table_html` 只接受 `<table...>...</table>` 完整包裹的预测；运行记录还有 **1,324 条 `invalid_table_html` runner warnings**，属于提取前拒绝或警告，不能算作评分阶段的 637 条。adapter 留下 2,752 张表，`src/cptla/evaluation/cross_page.py` 调用的 `html_to_cell_list` 再用 XML `ElementTree.fromstring` 解析，剔除 **637/2,752=23.1%**，有效进入评分仅 **2,115** 张。基于旧失败清单和旧 adapter 原始 HTML 的只读 XML 分类：`mismatched tag=520`、`not well-formed (invalid token)=99`、`junk after document element=12`、`undefined entity=6`。样本包含普通 HTML `<br>` 和未转义 `&`，也可能含真正标签缺失；不能把全部判定为模型“没预测表”，更不能不核验语义就直接自动修复。上述诊断**没有改变旧产物和分数**。
- **评分公式核对：**`full_document` 使用仓库 `third_party/grits-main` 的 `GritsEvaluator(metrics=["top","con"])`，按文档做 Hungarian 匹配、全数据集汇总 pseudo-F1；`grid_exact_match_accuracy` 按 GT 表数归一。这与论文附录的集合级评测**大方向一致**，目前没有找到可证实的聚合算式 bug，但没有拿论文发布的原始预测执行逐项一致性检验，不能声称完全复现其评测实现。
- **自定义跨页指标边界：**`cross_page` 先对文档全真值和全部合法预测按 **Con** 匹配，再抽出 983 张跨页真值重新计算格子指标；这不是论文表 7 的全表指标，也没有扣除跨页子集外的未匹配假阳性。跨页 `Top` 沿用 Con 所选的匹配关系，不等同于按 Top 单独优化匹配。`grid_exact` 只检查 HTML 格子，不验证 `source_pages`，因此 `2/983` 不等于已证实的“两个跨页续表完整恢复”。这些是协议定义限制，报告时必须标明。
- **已确认的实验方法不等价：**模型输入为固定官方 val JPEG、自定义布局 prompt，`do_sample=False`、`max_new_tokens=24000`；论文当前 PDF 未给出可直接一一核对的该权重/推理 prompt 和后处理配置；**不能断言配置相同**。已记录 2 页 error，按终态计入覆盖但无预测表。项目合并器须页边坐标 + **完全相同的显式表头** + 同列数；论文是 ViT/B-16 续接判断 + 同列数连接，连接定义不同。即使先解决解析，仍不能将此运行称为论文原方案同条件复现。
- **风险驱动的下一步：**(1) train 非 GT 筛选样本与官方解析实现审计两层过滤的可恢复性/文本保真/异常分布；(2) 在 train 冻结规范化、推理 prompt 与模型配置之后，使用**新目录**只读旧预测或新版本推理重评 val；(3) 区分页级输出错误、HTML 解析丢失、合并漏连与 GT 结构差异，报告前后覆盖/相同输入对照；(4) 取得论文 ViT 权重与完整协议前，不承诺复现表 7，也不对 test 调参。不得原地覆盖旧输出或按 val GT 手工修 HTML。
