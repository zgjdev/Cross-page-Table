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
