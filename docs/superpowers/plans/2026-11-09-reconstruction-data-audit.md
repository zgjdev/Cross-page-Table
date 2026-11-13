# 跨页联合重建 G0 数据与审计入口实施计划

> 使用 subagent-driven-development 按任务推进，每个模块先验证失败测试，再实现与复核。

日期 2026-11-09。用户已要求开始首阶段。依据 [研究方案](../../plans/2026-11-09-cross-page-joint-reconstruction-research-plan.zh-CN.md)。本轮交付可运行的 train 数据清单、保守重复簇与暂定划分、200 表审计抽样、20 表坐标可视化和服务器 CPU 执行证据。不开启模型训练，不把材料准备等同于 G0/G1 通过。

## 共同约束

- 只读取服务器 `/data01/public/zhengguojie/paper` 内文件；原始数据、旧产物只读，新输出目录必须独占创建。
- 固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，只消费 Full Documents/train，不读取 test 内容。
- R0 使用 GT parts 框和同表分组，必须标注 oracle；输入清单和整表目标分开，不把 HTML/全局 cell 标签写入模型输入。
- 同页多片段不计跨页，非相邻页不补造中间片段；多个同页 part 保留各自 ID。图像页序用数字排序。
- 先少量 smoke，再完整 train 清单；失败保留目录和状态，任何重跑使用新 RUN_ID，不删除或覆盖。
- 重复候选方法仅使用 train 表文本/图像指纹，不能声称已经完成所有内容泄漏审计。未经人工校准与完整检查，split_status 必须为 provisional_do_not_train。
- 200 表在暂定 train_fit 内分层抽样，记录种子 20261109、分层总体、抽样数、概率与权重。20 表为坐标诊断子集，不作总体性能估计。
- 双人独立审计与新模型预测都未完成，审计状态初始 pending，不能写“通过”。

## 模块接口

### T1 原始 train 清单

负责 `src/cptla/reconstruction/__init__.py`、`data.py`、`tests/reconstruction/test_data.py`。

提供 `scan_training_data(project_root: Path, *, limit_documents: int | None = None) -> dict`，数据目录固定为根下 `data/pubtables-v2/extracted/Full Documents/train`。

返回 `inputs / targets / documents / audit / source_hashes`。inputs 每项有 group_id、document_id、source_split、dataset_revision、protocol、page_numbers、fragments；fragment 含 fragment_id、part_index、page_num、page_object_num、image_relpath、image_sha256、image_size、bbox、crop_box、clamped。不含目标 HTML 或 cell 标签。targets 有 group_id、document_id、html、source_pages、source_table_file、source_table_sha256。documents 每项 document_id、text（所有表文本串）、cross_page_groups、table_count；text 仅供去重，不进模型输入。audit 含覆盖、表数、跨页/同页多片段、间隔页、clamp 及目标 profile（group_id、page_count、cell_count、has_span）等。

逐表校验 parts 页存在，bbox 有限/面积正，读取图像宽高，floor 左上/ceil 右下并裁到边界，记录原坐标和 clamping；空裁剪必须失败。逐文件 SHA，跨页图像 SHA 缓存。文件名/重复页/路径越界、非法 JSON/part 明确失败。limit_documents 只用于技术 smoke，audit 中明确不是全量。

- [x] 测试同页/跨页/非相邻页、页码数字序、输入目标隔离、坐标裁剪/越界、缺图、SHA、确定性和源文件不变。
- [x] 实现并通过 `.venv/Scripts/python.exe -m pytest tests/reconstruction/test_data.py`。

### T2 重复候选、簇划分和抽样

负责 `src/cptla/reconstruction/sampling.py`、`tests/reconstruction/test_sampling.py`。

提供 `group_and_split(documents: list[dict], *, seed: int = 20261109) -> dict`，返回 assignments（document_id、cluster_id、split）、duplicate_candidates、summary。normalize HTML/text，空文本不互相合并；非空完整规范化文本相同则合并。近重复候选用 5-word shingles、稳定 64-bit SimHash、4 个 16-bit bands，核验 Hamming <=3 和真实 shingle Jaccard >=0.85（至少 50 tokens）。允许稳定 bottom-256 shingle hash 构造 SimHash 控制成本，但 Jaccard 对完整集合验证。候选与接受边、参数及局限均保存。并查集连通分量永不跨划分；sha256(seed+cluster_id) 映射 70/15/15，实际比例如实报告。标记暂定，视觉近重复/阈值人工校准尚未完成。

提供 `sample_audit_groups(profiles: list[dict], assignments: list[dict], *, sample_size: int = 200, coordinate_size: int = 20, seed: int = 20261109) -> dict`，返回 samples、coordinate_group_ids、strata、summary。profiles 含 document_id、group_id、page_count、cell_count、has_span。按 page_count=2/3/4+ 与 has_span 分层，分配给非空层的均衡配额并补余，层内稳定 seed 排序抽样，概率 n/N、weight=N/n。不足时全部取且明确 shortfall。20 表从样本内分层确定性选取，诊断不作为第二个代表性统计样本。

- [x] 测试完全重复/空文本、近重复候选验证、同簇不跨 split、字典序无关、抽样无重复、概率/权重和小总体。
- [x] 实现并通过对应测试，报告近重复检出的限制。

### T3 CLI、审计预览和配置

主 Agent 负责 `scripts/build_reconstruction_manifest.py`、`src/cptla/reconstruction/audit_bundle.py`、`configs/reconstruction/data-audit-v1.json`、`tests/reconstruction/test_audit_bundle.py` 与 CLI 测试。

CLI 参数 `--project-root --output-dir --limit-documents --sample-size --coordinate-size`，输出目录须位于根下 artifacts/reconstruction，独占 mkdir。保存 inputs.jsonl、targets.jsonl、documents/splits/duplicate-candidates、audit-sample、coordinate-sample、summary、run-manifest、hashes；文档文本不写进 inputs。先完整校验再发布 completed。图像仅在服务器生成，源图不变；200 表审计页显示各片段 crop 和 GT（标为 GT），预测明确未生成；20 表额外提供原页 bbox overlay 和编号，便于人工坐标核验。HTML 目标通过安全渲染或 sandbox iframe 展示，不能执行原始标签脚本。

- [x] 测试拒绝覆盖/路径逃逸、输入目标隔离、采样和截图引用存在、源数据 SHA 不变。
- [x] 跑相关测试与 ruff，独立审查再发布。

### T4 服务器验收与留痕

- [x] 提交前检查保护目录 diff 为空；源码通过新非当前 ref 传入服务器，只做安全 fast-forward 或独立新源码目录。
- [x] 小范围 20 文档 smoke，核对 manifest/targets ID、文件哈希和预测未生成状态。
- [x] 完整 train CPU 清单、暂定划分与 200/20 样本，保存实际命令、时间、环境与结果。
- [x] 检查 20 表坐标预览；如图像/标注存在问题，保留 issue 清单，不能跳过失败表。
- [x] 更新实验记录、记忆、进度。未完成的人审/泄漏校准/基线明确列出，不冒称 G0/G1 完成。
- [ ] 提交并同步 GitHub 与服务器同一功能分支，核对 HEAD 与工作区状态。

## 工作进度

- 已完成启动前检查，原始 train 数据存在。新分支 `codex/reconstruction-data-audit`，起点 `6ee8fcb`。保留上一轮未提交的就绪性文档。
- 2026-11-13：T1–T4 的数据准备与验收已完成，最终同步正在收尾。完整 train 7,359 文档/7,606 跨页表、200 审计材料/20 坐标图已核验；20 表初查含 2 例侧向表，未声称像素/人审通过。当前无 GPU 任务。
- [最终验收记录](../../experiments/2026-11-13-reconstruction-train-data-acceptance.zh-CN.md) 保存源对账、893 产物 SHA、逐例观察与待处理项；独立双人审计、泄漏校准、grid/评分契约和基线均仍未完成，G0/G1 不放行。
