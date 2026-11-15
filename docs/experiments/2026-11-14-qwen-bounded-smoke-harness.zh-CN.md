# 2026-11-14 Qwen受限技术smoke入口

状态：本地实现和mock验证完成；尚未执行真实模型优化，不代表G2通过或正式训练开始。

入口scripts/run_reconstruction_qwen_smoke.py。必需参数--project-root、--inputs、--targets、一个或多个--upstream-run、1–16个唯一--group-id、--model项目内本地目录、--run时间戳。--steps限制1–50；默认仅准备，只有显式--execute-smoke才加载模型优化。--max-tokens默认8192且上限32768，超长拒绝不截断；--gpu默认0。

从原始固定revision/train_fit/R0输入确认成员，验证已完成upstream prepared/source/crop/预测与完整片段覆盖；真正原图必须在固定train/images内，文件名文档/页码与记录一致。多upstream任何group重叠拒绝。用现有SFTCollator和QwenProcessorAdapter，模型输入仅图像、预测HTML和匿名顺序，不传GT元信息，GT仅assistant标签。

执行固定LoRA r16/alpha32/dropout.05，实际语言self_attn q/k/v/o模块名全量记录；其他参数冻结，AdamW1e-4、seed20261109、bf16、SDPA、单例梯度累积1。GPU启动前至少20480MiB，加载后/每步前后至少8192MiB，记录已有进程且不终止进程。保存每步loss/梯度范数/耗时/peakmem、实际改变参数名。新adapter checkpoint落盘后核验参数一致，清零adapter再reload并逐参数比对；该验证不等于optimizer/RNG断点恢复或生成效果核验。

独占新目录保存参数、命令、版本、seed、输入和全部模型文件SHA；末尾复验，异常保存失败终态。结果永久G2_passed=false、training_authorized=false，status仅completed_smoke/prepared_only，不能宣称完整研究门禁通过。

TDD先确认缺脚本错误，再实现安全范围、实际模块名、路径和train映射mock。9项测试通过，最后命令 .venv/Scripts/python.exe -m pytest tests/reconstruction/test_qwen_smoke.py -q -o addopts= --basetemp artifacts/qwen-smoke-tests-03。真实CUDA/PEFT/模型组合仍待root按GPU门禁执行；没有服务器访问或提交。

追加root审查修复：执行前设置项目内HF_HOME/XDG_CACHE_HOME/TMPDIR及offline、禁隐式token；processor固定min_pixels=65536/max_pixels=262144，记录运行策略；去掉模型不消费的token_type_ids，clip_grad_norm_=1.0并记录preclip全局范数。模型download-manifest须complete且固定revision89644892e4d85e24eaac8bacfd4f463576704203，verified完整文件集合与仓库官方manifest一致，每文件size/SHA及官方LFS SHA或git blob SHA1对账。拒绝.metadata/.cache作为文件来源和越界；允许官方.gitattributes。模型制品末尾复验。字段改full_training_authorized=false，明确微型优化是已授权技术验证。9项mock回归再次通过（artifacts/qwen-smoke-tests-04），Ruff通过；新增真实模型运行策略未在本机GPU执行，不冒称已验证CUDA行为。

2026-11-15恢复接口追加：新增--resume-state（项目自产完整state目录）和--gradient-checkpointing（use_reentrant=False）。每次steps仍1–50，总step从恢复值累计；cursor决定样本循环位置，group仍≤16。resume契约保留group顺序、seed、输入/模型SHA、全部训练超参、token/pixel预算及checkpointing开关，排除run/output/resume路径和本次steps。切换checkpointing会配置不符拒绝。旧只有adapter的50step run没有完整state，不能伪装恢复。

每次执行末尾新目录training-state保存模型/optimizer/RNG/step/cursor/config，manifest及state SHA入口另存。加载前核验自产format/完成状态/配置SHA/stateSHA，load_state再次严格核验；只允许显式--execute-smoke执行优化。adapter重载验证保留，G2仍false。模型真实恢复尚待root执行；本地仅配置契约mock回归（先失败后实现）与原安全mock共10 passed、Ruff通过，不声明Qwen数值恢复已验证。
