# 2026-11-14 强基线与扩大实验准备

状态：实施中。依据已批准联合重建方案，继续自动化部分；用户暂不能安排独立审计，不等于取消G0/G1。已有20表/66片段R0及B0完成，详见11月13日自动化记录。

本轮先新增保守重复表头对照，保持输入、来源、文字、span及失败分母一致，记录删除依据；此对照不能冒称完整的学习列对齐B1。测试覆盖重复正文误删、跨行边界、不同列数和来源异常。使用相同20表缓存作CPU配对诊断，不重新GPU推理。

后续自动化工作：完整列对齐基线、错误分层、近重复与污染处置协议、200表诊断准备。已批准方案G0规定“先修数据/评价，不扩大GPU实验”，故在已知污染处置、方向问题和评分核验未闭合前不启动全量GPU。全量训练另需G1人工结构修复和G2/G3技术与机制信号，不能只凭流程成功宣称可开始。

## CPU配对完成

2026-11-14，代码b0c9ec4；本地135 passed/2 Windows跳过，Ruff通过。固定20表66片段全部无显式header单元格。命令在原B0 CLI增加 --baseline explicit_header_exact_v1 --run 20261114-20table-explicit-header，其余输入保持一致。服务器artifacts/reconstruction-baselines/20261114-20table-explicit-header summary completed；逐表per_group与B0完全一致：top0.05/con0/source0.9/joint0。源文件和结果哈希在该目录。没有重跑GPU，无新下载。此为负对照，不能称完整B1，不能据此宣称重复表头问题不存在。

下一步必须实现不依赖显式th的表头/列对应探索对照并检查误删误对齐，再推进200表审计。完整方案仍有G0污染处置/方向核验、近重复、G1人工结构修复、G2/G3技术与机制验证缺口，当前不能全量训练。暂未启动新的长任务。

## 2026-11-14 持续推进检查点（未结束）

用户再次要求连续工作到可全量实验，不再逐小阶段停止。本轮已启动预测内容驱动列对齐/重复首部对照实现及就绪关口独立审查。当前无GPU任务。

完成20表GT-assisted词元覆盖诊断，artifacts/reconstruction-diagnostics/20261114T070006Z-token-coverage/，summary completed，输入末尾SHA复验。按cell原文空白分词、大小写敏感、词频交集计算覆盖；19/20表有未匹配词元，覆盖0.742–1.0。该值不是正式准确率或可恢复上界，分词/格式差异亦可能造成不匹配，不能直接归因为漏识别。原预测和真值均未修改，逐表统计及input-hashes已保存。下一步仍是同输入结构对照与误差分层，不以本诊断绕过G0/G1。

## 2026-11-14 15:07北京时间：列对齐对照与全引用图审计

代码2314d01，本地151 passed/2 Windows跳过，Ruff通过（Pillow getdata弃用警告，不影响当前执行）。服务器20表同输入对照artifacts/reconstruction-baselines/20261114-20table-alignment完成，top_exact0.30(6/20)，con_exact0，source0.9。相对B0新增5个结构exact、无原成功退化：PMC10889581-table-0、PMC11506176-table-1、PMC10756142-table-3、PMC10631270-table-0、PMC7617839-table-0。删除前缀共26行；两列数异常仍因首行证据不足失败。明确为启发式探索，非学习B1、非官方Acc；未审查每项删除是否语义正确，不能宣称G1成立。

100图dHash smoke产物artifacts/reconstruction-visual-duplicates/20261114T071000Z-visual-smoke，partial、100/17299图、2候选，SHA复验通过。15:07:48北京时间启动全部引用图CPU审计20261114T070748Z-visual-full，PID848360，launcher artifacts/reconstruction-launchers/同run/含command.json、pid.json、stdout.log；输出artifacts/reconstruction-visual-duplicates/同run/。无GPU、下载或数据改写。命令为.venvs/eval312/bin/python scripts/audit_reconstruction_visual_duplicates.py --project-root /data01/public/zhengguojie/paper --inputs artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/inputs.jsonl --run 20261114T070748Z-visual-full，PYTHONPATH=src，PYTHONDONTWRITEBYTECODE=1。通过start_new_session分离标准输入输出，仍须以summary和进程核验终态；预计覆盖17299图，候选未校准，当前运行中。

## 全引用图审计完成与误报检查

20261114T070748Z-visual-full于07:13:25 UTC完成，17299/17299图、17988候选，进程已结束，三个产物SHA独立复核一致。距离0/1/2/3/4候选165/644/1856/4800/10523，其中跨暂定split分别80/281/841/2196/4880；14082不同文档对。汇总及精确文本污染隔离候选保存artifacts/reconstruction-readiness/20261114T093206Z-disposition/report.json，待审查，不改变划分。

只读缩略图检查按候选文件顺序前三个距离0配对：PMC10169604_page_16与PMC10192700_page_13，PMC10205825_page_6与PMC10309525_page_4，PMC10315023_page_4与PMC10349443_page_4。三对版式近似但内容明显不同，判为Agent初查误报，不是双人标签。故不能按dHash距离0自动合并文档，更不能把17988作为确认重复数；需文本证据联合筛查、抽样校准与漏检检查。此证据阻止过早冻结划分，但不阻止后续CPU自动化。

独立代码复核子代理因服务额度限制退出，主代理仍完成全图产物核验和上述可视初查，不能把未完成独立复核写为通过。剩余自动化：联合文本/图像候选筛查、200表审计准备、正式评分契约核准、训练/恢复链实现。完整实验尚未就绪，已有结果不构成G1或G2/G3通过。

## 2026-11-14 17:45北京时间：联合候选筛查与200表CPU准备

联合审计artifacts/reconstruction-joint-audits/20261114T094520Z完成。对视觉候选涉及3345篇train文档的全部表HTML提取数据文本，NFKC、空白折叠、保留大小写，5词shingle Jaccard；14082文档对全部<0.5，无>=0.5候选。原图候选与3345源标注SHA读取/结束复验，input-hashes保存。仅候选交集筛查，整篇聚合会稀释单表重合；不覆盖视觉检索漏检，不可宣称无泄漏或自动冻结划分。未读取test内容。

17:46:04北京时间启动固定原audit-sample中200组CPU prepare-only，run20261114T094604Z-200table-prepare，PID1840819，launcher artifacts/reconstruction-launchers/同run/包含完整argv/start/pid/stdout；输出artifacts/reconstruction-upstream/同run/。使用eval312，PYTHONPATH=src，PYTHONDONTWRITEBYTECODE=1，现有run_reconstruction_upstream.py，--prepare-only，输入原train-full inputs.jsonl、200个group-id。不下载、不改原图、不使用GPU、不推理。当前465片段来源已保存，等待prepared终态及覆盖SHA核验。

## 180表诊断补齐启动（不是全量训练放行）

原200表CPU prepare终态prepared，200组658片段，全部source.json与prepared一致、658 crop SHA复验通过。与已完成20表集合交集恰为20，复用旧66片段，只补剩余180表592片段。

依据用户反复明确“持续完成自动化部分”的授权，本轮继续固定200表诊断样本的推理；此为为G1取得诊断材料的受限试验，不将G0/G1或独立人审记为已通过，也不启动全量训练。此前文档笼统“不扩大GPU”在本次200表诊断范围内作执行澄清；不授权打开confirm/test或大规模训练。

20261114T094831Z-180table-diagnostic于09:48:31 UTC启动，PID1856910，GPU0。启动前free60950MiB/used20089MiB，已有三进程3052349/1462678/1179599，未干预；沿用20000MiB启动与8192MiB逐片保护。launcher artifacts/reconstruction-launchers/同run/command.json保存完整argv、时间、20表复用入口；pid.json/stdout.log同目录；输出artifacts/reconstruction-upstream/同run/。Python .venvs/paddle-v15-20261023T081029Z-paddle-v15/bin/python，代码e375783，固定同权重/seed0/原方向，inputs原train-full，180个显式group-id，--gpu 0。无新数据下载，不覆盖原数据或旧预测；start_new_session、stdin DEVNULL、stdout独立日志。预计数小时，须以summary与完整覆盖验收，不能凭进程启动宣称模型完成。完成后联合旧20表做200表B0/对照及错误分层。

## Qwen骨干准备（尚未完成下载）

复用既定Qwen3-VL-2B-Instruct候选，官方API固定revision89644892e4d85e24eaac8bacfd4f463576704203，12文件4266648961字节，官方LFS/gitblob校验清单configs/models/qwen3-vl-2b-instruct-2026-11-14.json已提交08c8403（上一61bd55c只有文档，因models通配忽略，后补精确文件）。dry-run通过。服务器项目盘34T可用。

09:51:41 UTC启动下载run20261114T095141Z-qwen3-vl，PID1877352，launcher artifacts/reconstruction-launchers/同run/{command.json,pid.json,stdout.log}；命令.venvs/eval312/bin/python scripts/download_public_models.py --manifest configs/models/qwen3-vl-2b-instruct-2026-11-14.json --run-id 20261114T095141Z-qwen3-vl。下载器复用hf-mirror.com，按官方固定SHA逐文件校验，token=False，缓存在项目内。输出models/同run/qwen3-vl-2b-instruct，日志logs/model-downloads/同run。权重只到服务器，不到本地；无GPU训练，完成以download-manifest与summary为准。

## 独立Qwen接口环境安装中

09:53:59 UTC创建.venvs/20261114T095359Z-qwen-env，安装PID1892268。launcher artifacts/reconstruction-launchers/20261114T095359Z-qwen-env/{command.json,pid.json,stdout.log}，tmp/cache均在同目录。依赖清单requirements-qwen3-vl-20261114.txt，torch2.6.0/torchvision0.21.0、transformers4.57.1、accelerate1.10.1、peft0.17.1、Pillow11.3、numpy1.26.4；官方CUDA12.4索引作为extra-index。使用独立venv，不修改旧Paddle环境。原官方模型文档与transformers4.57.1 Qwen3VL文档确认API存在，安装兼容性及真实processor仍待验证。

当前180表诊断已保存16片段；Qwen模型大权重下载中、环境依赖下载中，未完成任何Qwen模型推理或训练。后续继续真实processor CPU验收和200表联合评分，不在单步完成时结束。

## 2026-11-14 23:35北京时间：200表与Qwen真实接口结果

180表补跑于13:41:19 UTC completed，592/592片段；联合旧20表，固定200表/658片段全部齐全。两组新评分artifacts/reconstruction-baselines/20261114T153243Z-200table-b0与同前缀200table-alignment：200目标/预测，missing/extra片段路径0，失败各30。B0 top23/200=0.115、con1/200=.005；对照top69/200=.345、con3/200=.015。全失败保留分母。配对汇总artifacts/reconstruction-diagnostics/20261114T153435Z-200table-paired：196文档，top改善47/退化1，con改善2/退化0，删除211行；按原抽样权重计算top .106758→.358491、con .012942→.037451，探索性诊断非官方指标。失败为首行证据不足21、歧义/不匹配9。退化PMC11277303-table-0删除两行重复列标题；真值为何保留该结构待逐例核验，不自动改标签或反调规则。

Qwen权重于09:57:28 UTC下载完成12/12、日志status0，CPU probe再次独立重算所有权重SHA通过。新环境安装完成，pip-freeze见artifacts/reconstruction-qwen-probes/20261114T153207Z/pip-freeze.txt。最初真实processor因assistant string不符合多模态list content失败，现场保留；回归先失败再修为2d4ef18，不修改目标文本。真实双图CPU probe completed：1452 tokens，监督537，pixel_values[1400,1536]、image_grid_thw[2,3]，max_pixels262144/min65536/token预算32768，未截断。

真实GPU0单表生成probe artifacts/reconstruction-qwen-probes/20261114T153357Z-model-smoke完成，gid PMC10488684-table-0，双图加局部预测，无GT作为prompt，seed0/bfloat16/SDPA/do_sampleFalse/max_new_tokens4096，16.02秒、torch峰值分配4452087296bytes。manifest/prediction/summary保存。严格原文评分artifacts/reconstruction-diagnostics/20261114-qwen-single-score为invalid_html，因原始输出包有完整Markdown代码围栏；尚不算正式Qwen效果。原文保留，后续独立评估仅外层围栏的格式适配，不修改原评分器、不填补内容。无优化/训练。

外层围栏去除的单独诊断保存在artifacts/reconstruction-diagnostics/20261114-qwen-single-unfenced，保留源预测SHA与变换说明；仍invalid_html（multiple or nested tables），不能把格式清理视为整表重建成功。本轮将继续实现最多16表/50step的受限LoRA技术smoke，只验证自动化训练接口、梯度/参数/恢复，不放行全量，不宣称G1或G2通过。
