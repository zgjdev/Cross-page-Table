# 2026-11-15 prepared 显式分片复用入口

状态：本地实现与24项单测已完成；未访问服务器、未运行GPU、未启动全量实验。日期为Asia/Shanghai；没有新增正式研究指标。

scripts/run_reconstruction_upstream.py 新增 --reuse-prepared-run（项目内既有run目录），仍强制逐项 --group-id，支持 --prepare-only。默认prepare行为不变。新run独占创建，失败保留failure.json及部分证据。仅逐字节复制所选crop，不重新裁剪，不复制预测；使用独立文件避免硬链接可写别名。新source.json/prepared.json路径一致，infer继续仅写新run。

沿用固定PubTables-v2 revision、R0协议、train/train_fit、原图SHA与页面/片段身份校验；额外验证旧manifest输入SHA/协议/revision/赛道、selected精确覆盖、prepared/source一致、crop SHA及尺寸、crop必须位于旧run/fragments且名crop.png。记录旧manifest/prepared/source/crop SHA与来源；末尾再次检查所选来源及manifest SHA。

验证：`.venv/Scripts/python.exe -m pytest tests/reconstruction/test_upstream.py -q --basetemp=artifacts/local-reuse-test-20261115a`，24 passed。新增测试覆盖禁止Image.crop、原run字节不变、新run独占、旧预测不复制、fake backend仅写新run、错误SHA/身份/逃逸/重复/缺片段/manifest拒绝。初始系统python因缺PIL无法收集；虚拟环境默认临时目录权限导致setup失败，改项目内新basetemp后通过。

范围与限制：本地合成fixture、无模型和GPU、无正式split样本或实验分数；完整数据端到端兼容及服务器验证待核验。不表述G0/G1通过或全量训练就绪。下一步由主agent检查变更，结合显式分片计划执行授权范围内验证。未提交commit，当前代码来源以工作树diff为准。

## 主审后补强

本地修正read/hash窗口：旧manifest、prepared与source统一用同次read_bytes内容解析JSON并计算SHA，结束再读取文件核验，避免解析A后记录B哈希。新增3种来源在read_bytes返回后改变的回归（prepared/manifest/source均拒绝），以及两组逆序与subset的路径/source一致性测试。

`.venv/Scripts/python.exe -m ruff format scripts/run_reconstruction_upstream.py tests/reconstruction/test_upstream.py`完成；相同文件`ruff check`全部通过；`test_upstream.py -q --basetemp=artifacts/local-reuse-test-20261115b`为29 passed。未访问服务器、未提交。研究边界保持不变。
