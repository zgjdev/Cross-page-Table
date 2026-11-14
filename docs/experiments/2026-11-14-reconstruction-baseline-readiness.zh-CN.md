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
