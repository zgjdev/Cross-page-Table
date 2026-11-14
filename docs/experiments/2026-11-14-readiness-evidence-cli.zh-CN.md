# 重建就绪证据检查CLI（2026-11-14）

状态：本地工具和5项合成测试完成；没有服务器检查或新增实验结果。TDD先确认缺实现文件失败，随后5 passed；Ruff通过。测试目录artifacts/readiness-test-02。

入口scripts/check_reconstruction_readiness.py。参数：--project-root 项目根目录 --manifest 项目内清单 --manifest-sha256 清单SHA256 --scope data_preparation|diagnostic_inference|full_training --output 项目内新报告路径。输出使用独占创建，不覆盖旧报告。清单及关联证据都只允许项目内路径。

清单schema为 {"evidence":[{"kind":"data_integrity","path":"证据.json","sha256":"64位小写SHA256"}]}。kind支持data_integrity、contamination_disposition、coordinate_audit、score_contract、research_space、model_smoke、mechanism_signal，分别对应G0–G3。

每份证据schema为status=completed、coverage={expected,completed,missing,extra,duplicate}（整数，expected>0、completed=expected、其他三项0）、artifacts=[{path,sha256}]。原始脚本不同schema须由明确来源的版本化适配证据汇总，不应把原summary直接改成completed。引用证据与产物均核验SHA；不能仅凭自报completed通过。

污染处置checks须含all_known_overlaps_disposed、split_frozen；评分checks须含roundtrip_passed、contract_passed、protocol_frozen。model_smoke须含overfit_passed、gradients_updated、resume_passed、cache_passed、coverage_passed，metrics须overfit_tables在8–16、steps>=50、legal_rate>=.99、source_coverage=1。布尔具名检查必须引用真实产物，不得补造。

三个scope分别只核查数据准备条件、G0诊断推理条件、G0–G3全量训练条件。报告列出全部缺口、对应关口与已核验证据。人工坐标审计、G1研究空间和G3机制判断始终列为外部审查要求，即使证据自报approved也不自动放行。ready仅表示本工具检查通过，绝不构成运行授权。本工具不证明记录者诚实或hash引用内容的科学结论正确，不替代人类审查，也不应成为停止其他获授权CPU工作的理由。

测试覆盖缺证据完整缺口、伪造completed缺SHA、自报人工approved、缺G2smoke和越界路径。没有对实际项目宣布G0–G3通过。
