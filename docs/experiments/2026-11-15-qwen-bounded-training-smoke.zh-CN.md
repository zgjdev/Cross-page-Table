# 2026-11-15 Qwen受限LoRA技术验证

用户要求持续执行至可全量实验；本记录仅技术链路验证，非G1研究结论或全量训练许可。200表推理和评分已完成，见11月14日baseline-readiness。

最初环境prepare因缺pydantic在导入阶段失败，未训练；新增pydantic==2.13.5，与现有eval312一致，依赖写回requirements-qwen3-vl-20261114.txt。11月15日02:19:30 UTC新prepare-only完成，artifacts/reconstruction-qwen-smoke/20261115T021916Z-qwen-8table-prepare，8组输入、模型官方manifest/SHA核验通过。

02:19:50 UTC启动20261115T021950Z-qwen-8table-50step，PID1001517，launcher artifacts/reconstruction-launchers/同run/{command.json,pid.json,stdout.log}，输出artifacts/reconstruction-qwen-smoke/同run/。完整argv保存；入口scripts/run_reconstruction_qwen_smoke.py，--execute-smoke --steps 50，GPU0，seed20261109，代码5f06245。环境.venvs/20261114T095359Z-qwen-env，模型models/20261114T095141Z-qwen3-vl/qwen3-vl-2b-instruct，revision89644892e4d85e24eaac8bacfd4f463576704203；train固定revision aa575e798cb00a296925e2086addb3e3fd9a1903，R0 image-only。

样本为已观察20表中按目标HTML长度升序前8表，含两页与三页：PMC10488684-table-0、PMC12193938-table-2、PMC11262699-table-2、PMC12072187-table-1、PMC10889581-table-0、PMC11560864-table-5、PMC11149192-table-1、PMC11204794-table-0。这不是代表性性能样本，只用于接口/梯度/恢复验证。

语言attention q/k/v/o LoRA r16/alpha32/dropout.05；其余冻结，AdamW1e-4，clip1.0，bf16/SDPA，图像65536–262144像素，token上限8192，超限拒绝不截断。启动前20GiB和逐步8GiB余量检查。checkpoint只写新目录，原图、数据、模型和历史结果不改、不删；无新数据下载。预期检查：50步终态、有限loss、非零梯度、参数实际更新、adapter保存/重载相等、输入/模型SHA末尾复验。optimizer/RNG恢复、生成合法率、过拟合质量与机制信号尚未证明，不能自动宣称G2通过。

## 50步完成（11月15日02:20:51 UTC）

summary completed_smoke，8组50步；224个LoRA参数张量改变、梯度非零，adapter保存/清零/reload相等。首步loss0.089105、末步0.004977（不同循环样本，不能直接当同样本改善幅度），观测峰值分配约39.56GB；50步逐条日志和optimization.json留存。所有输入/模型文件末尾SHA复验通过。当前正从保存checkpoint独立重载并生成8个训练样本，检验格式/网格，未把smoke标为G2通过。

## 生成与长度审计完成（2026-11-15，UTC）

02:30:28 UTC，8表独立重载生成完成，产物 `artifacts/reconstruction-qwen-probes/20261115T022131Z-lora-generation`。严格网格合法6/8，结构exact4/8，内容exact2/8；两条非法分别为cell outside grid、uncovered grid positions，均非4096输出上限截断。仅训练样本接口/拟合证据，不证明泛化、不满足G2确认合法率要求。

来源页记录勘误：该临时生成脚本曾从target填入source_pages，旧summary“直接继承输入”的表述不准确。02:38 UTC新增独立核验 `artifacts/reconstruction-diagnostics/20261115T023834Z-qwen-input-source-audit`，从原始input fragments推导来源页，8/8与旧预测及target一致，完整重评分不变；保留旧结果。此来源信息属于R0已知分组，不能视为模型预测续表关系正确率。正在实现生成/评分分离的正式CLI，生成阶段不读取GT。

长度证据：`artifacts/reconstruction-qwen-probes/20261115T022533Z-200-token-audit` 对200表真实processor完整上下文审计，最大41582 tokens；超过8192/16384/32768分别74/20/1表。`20261115T022727Z-200-budget-parts` 分离prompt/target，目标超过8192为19表。全5322个train_fit原始target HTML tokenizer审计 `20261115T023025Z-fit-target-lengths`：p50=1998、p90=5135、p95=6918、p99=12011、max38814；超过8192/16384/32768分别176/24/1。后者不含图像、输入和模板开销，不能当完整上下文覆盖。初拟8192输出预算不适合全量，需验证更大预算及长样本内存；不得隐式截断或悄悄剔除。

代码7568668加入完整model/optimizer/Python与torch CPU/CUDA RNG保存恢复和非重入gradient checkpointing。配置/来源/模型SHA须一致，每次仍最多50步、最多16组。此前仅adapter的50步产物不能伪称可完整续训。服务器旧checkpoint工具CPU相关测试187项通过；新CLI本地184通过、3跳过（无torch），Ruff通过。

02:36:14 UTC启动真实Qwen恢复对照：`artifacts/reconstruction-launchers/20261115T023614Z-qwen-resume-comparison`，连续2步、分段1+1步依次执行，输出分别 `artifacts/reconstruction-qwen-smoke/20261115T023614Z-resume-{continuous,part1,part2}`。沿用上述8组、种子/超参，开启gradient checkpointing；GPU0启动空余60950MiB，有既存进程，逐步8GiB保护；所有命令/PID/log独立保存，不修改旧数据。目标核验真实参数与恢复step/cursor，不表示G2或全量训练放行。

## 真实续训验收与长样本（2026-11-15 07:32 UTC检查点）

最初7568668连续2步与1+1步的真实对照未达到参数完全一致，证据 `artifacts/reconstruction-launchers/20261115T023614Z-qwen-resume-comparison/comparison.json`。排查发现独立运行的第一步梯度已不同，不能归因于恢复失败。b5d2f7d启用torch确定性算法及CUBLAS_WORKSPACE_CONFIG=:4096:8，并加入resume契约。新对照 `artifacts/reconstruction-launchers/20261115T072421Z-deterministic-resume/comparison.json` **全部通过**：model、optimizer、CPU/CUDA/Python RNG、step、cursor、config hash完全相等；第二步loss同为0.06185782328248024。保留旧失败对照及原因。

15,480-token/10片段train_fit样本PMC10550294-table-1已在GPU3完成单步真实反传，run `artifacts/reconstruction-qwen-smoke/20261115T072703Z-long15480-smoke`，07:27:50 UTC completed_smoke，峰值34,513,571,840 bytes，4.208秒优化步，loss0.2590705；开启gradient checkpointing，完整上下文不截断，启动时GPU3空余81,031MiB且无列出的计算进程。命令/PID见同名launcher。该运行不证明长样本生成质量。

8表直接SFT从确定性对照的2步checkpoint续训两段各50步，累计102步，输出 `artifacts/reconstruction-qwen-smoke/20261115T072834Z-overfit-{52,102}`。截至检查点均exit0，正在运行独立生成CLI，之后自动评分；launcher `artifacts/reconstruction-launchers/20261115T072834Z-qwen-continued-overfit` 保存每步argv/PID/log。仍仅8训练表，不是正式全量训练，不与旧非确定性50步指标混为同一训练轨迹。

c2908f3正式加入 `scripts/review_reconstruction_qwen_smoke.py generate|score`，生成入口不读GT，来源从input fragments推导；评分独立读取targets，原始输出不修补，截断计失败。4项本地测试包括真实文件映射、拒绝读取GT与训练prompt完全一致。

217453f加入可选 `--supervised-logits-only`：针对环境内Transformers4.57.1 Qwen3-VL forward/ForCausalLMLoss实际代码，保留完整输入与图像、完整目标，只计算最后一个prompt位置至目标结尾的logits，labels同步后缀以保持causal shift。CPU float64 loss/hidden与weight梯度等价测试通过（服务器7项全过）；这不是目标截断。该开关加入resume契约，旧默认false保持兼容。新增token预算上界65536只用于显式长样本技术验证，不等于正式预算冻结。07:32:02 UTC启动GPU3同15,480样本及41,582-token最长200样本的逐例单步验证，launcher `artifacts/reconstruction-launchers/20261115T073202Z-supervised-logits-memory`，新run `20261115T073202Z-suffix-{15480,41582}`，先验验收pending。

## 长样本反传验证完成（2026-11-15 07:33:46 UTC）

`20261115T073202Z-suffix-15480` 单步成功：完整输入15480、监督6917、logits6918，峰值18,904,241,664 bytes，相比同样本完整logits的34,513,571,840 bytes下降约45.23%，loss均0.2590705454349518。BF16下梯度归约有微小数值差别（preclip norm 0.3245615 vs 0.3245768），不声称实际低精度参数逐位等价；CPU高精度目标/梯度等价测试已通过。

`20261115T073202Z-suffix-41582` 最长200样本PMC10653545-table-0单步成功：完整输入41582、监督21747、logits21748；峰值49,134,122,496 bytes，13.604秒优化步，loss0.1187024。两run均completed_smoke/exit0，adapter与完整恢复state已保存，源/模型末尾SHA通过。只证明这两个样本可训练，未证明全5322训练上下文覆盖，更不代表长表生成质量。全部旧结果不变。

服务器2026-11-15相关测试199项全通过（含CPU torch损失/梯度与断点测试）；Ruff通过。此后新增污染隔离3项专项本地通过；服务器专项结果另核验。

## 102步复评完成与后续受限过拟合（2026-11-15 07:42 UTC）

`artifacts/reconstruction-qwen-review/20261115T072834Z-overfit102-{generate,score}` 均完成/exit0，8目标/8预测、extra0、全部EOS结束/无预算截断。生成input-hashes不含targets.jsonl，source_pages仅从输入推导。严格网格合法7/8、结构exact7/8、内容exact6/8；这依然是训练样本复评，不代表G2独立确认或研究泛化。

残差只读分析 `artifacts/reconstruction-diagnostics/20261115T074259Z-qwen102-residuals/report.json`：PMC11262699-table-2的GT为51x3，预测把rowspan5写成3、另一个rowspan2漏掉并补空td，导致未覆盖网格；PMC11560864-table-5为88x3，仅一个cell将弯引号Didn’t输出为直引号Didn't，严格原文exact因此失败。保留评分口径，不利用此例静默改归一化或修补预测。不能把两者都泛称文字完全识别失败。

用户继续授权自动化工作，07:42:29 UTC启动同8表受限续训至累计302步，每段50步新目录并恢复完整optimizer/RNG。launcher `artifacts/reconstruction-launchers/20261115T074229Z-qwen-overfit302`，顺序输出 `artifacts/reconstruction-qwen-smoke/20261115T074229Z-overfit-{152,202,252,302}`，随后新目录 `artifacts/reconstruction-qwen-review/20261115T074229Z-overfit302-{generate,score}` 完整8表复评。所有argv/PID/log独立保存、GPU0守卫，无新数据下载，不改数据/旧检查点，不扩大到新训练样本。代码6621a35；逐例生成现在即时独占保存，避免后续失败丢掉已完成案例。运行中，不预报达到8/8。

## 分块词表损失验证完成（2026-11-15 07:51 UTC检查点）

0bde16b新增可选`--loss-chunk-size 512`，与supervised-logits-only互斥；完整上下文一次进入Qwen视觉/语言骨干，仅监督位置的lm_head/交叉熵按512 token分块并用非重入checkpoint重算。所有目标保留，causal shift包含首个assistant目标；不属于表格/上下文分块，不改变研究输入条件。块大小进入恢复契约。仅允许Linear lm_head以排除未保存随机状态的随机head。先在服务器缺模块失败，再通过真实CPU loss/hidden/head梯度等价测试；本地torch缺失的skip不冒充通过。

真实GPU3单步对照均exit0，launcher `artifacts/reconstruction-launchers/20261115T074851Z-chunked-loss-memory`，run `artifacts/reconstruction-qwen-smoke/20261115T074851Z-chunked-{15480,41582}`。15480完整输入/6917监督：loss0.2590705156，峰值8,743,917,056 bytes；41582完整输入/21747监督：loss0.1187025160，峰值16,015,141,888 bytes，13.938秒优化步。相比监督后缀logits版，最长样本峰值49.13GB→16.02GB。所有来源、原模型与旧结果保留，源/模型SHA末尾通过，checkpoint保存完成。

数值边界：CPU目标/梯度在测试精度内等价，实际BF16分块GEMM及梯度累积有数值舍入差异，不能声称不同实现逐位等价。不同方法的正式对照需固定同一种损失实现和块大小。现有8表过拟合仍沿用完整logits轨迹，未在恢复中切换实现。分块loss也未证明全部5322输入长度/图像预算覆盖或长表生成效果。

## 302步训练样本复评完成；未训练样本检查启动

2026-11-15 12:26 UTC恢复只读检查确认：累计302步训练早已于07:49:45 UTC结束，四段续训与随后generate/score均exit0。末段run-manifest代码commit为e95199a，run内实际脚本SHA保存；不同段代码来源各自记录，不把整个轨迹伪记成单一后续commit。`artifacts/reconstruction-qwen-review/20261115T074229Z-overfit302-score/scores.json`：8目标/8预测、extra0，结构/内容/来源网格诊断exact均8/8，全部网格合法。评分开始时间07:59:02 UTC。这只完成直接SFT的8表过拟合技术验证，不是独立G2确认、不代表复杂结构模块已实现，也不证明泛化。

12:31:11 UTC启动未训练短表接口探针，code e74cd4e。固定seed20261109，从既有200表中完整训练上下文<=4096且排除已用于各类训练smoke的10组，共35候选随机选8组；选前不看新模型结果。明确仅train_fit短表技术范围，非总体代表样本、非train_confirm/test。名单/排除集/长度审计SHA见 `artifacts/reconstruction-launchers/20261115T123111Z-untrained8-probe/selection.json`；完整argv/PID/log同目录。保持302步checkpoint、原prompt、原图像预算、max_new_tokens4096和严格评分；生成完全input-only，不读GT。

新产物 `artifacts/reconstruction-qwen-review/20261115T123111Z-untrained8-{generate,score}`，当前运行中。入口新增显式probe组与upstream参数，禁止与该smoke训练组相交；评分从已hash核验的生成manifest读取相同范围。6项本地回归通过，先缺方法失败再实现；此前服务器全重建测试205项通过。不得将训练8/8代替这组未训练样本结果。

## 未训练短表探针完成与研究边界（2026-11-15 12:39 UTC核验）

`20261115T123111Z-untrained8-{generate,score}`均exit0，8目标/8预测、extra0，无生成预算截断；严格网格合法7/8，结构exact1/8，内容exact0/8。唯一非法项PMC11318497-table-0为mismatched closure: table，原文同时有三列表头/四列正文等结构不一致，未修改原输出或评分规则。固定同8组的B0与alignment均结构1/8、内容0/8、合法8/8。逐组配对和三个源score SHA保存于`artifacts/reconstruction-diagnostics/20261115T123900Z-untrained8-paired/report.json`。该探针经过短上下文筛选、样本仅8，不能估计全体泛化成绩；目前不足以证明直接SFT有未训练样本收益或满足99%输出合法率。训练8/8仅保留为过拟合技术验收，不用继续同8表训练来代替未训练验证。

独立代码审查指出score曾未绑定训练时target SHA；5d3928a修复，将正规化目标路径与smoke input-hashes绑定，缺失/漂移拒绝。实际CLI回归先DID NOT RAISE失败再通过。新目录`artifacts/reconstruction-qwen-review/20261115T124208Z-{train8,untrained8}-pinned-score`按固定SHA复算，两组全部逐表结果与原结果完全相同；此为防漂移缺口修复，未发现既有目标实际漂移。Spec/quality复审通过本轮受限实现，不代表研究关口通过。

本轮服务器完整重建测试**219项通过**（12:46 UTC检查点），Ruff通过。真实恢复、长样本反传、训练样本拟合、未训练短表复评均已结束，当前没有本轮运行中的GPU任务。全量实验仍缺：正式G0数据/近重复验收、G1人工可修复空间与独立审计、通过验证的共同结构模块及G3同预算机制对照；完整train_fit局部预测尚缺11642片段。现有代码是受限直接SFT技术底座，不能冒称完整研究框架或完整训练器已就绪。用户暂无法安排两人审计，保持pending；原计划门槛不自动取消。
