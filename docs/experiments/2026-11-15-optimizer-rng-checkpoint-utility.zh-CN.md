# 2026-11-15 optimizer与RNG断点恢复工具

状态：独立实现及CPU真实torch回归用例已编写；本地.venv未安装torch，pytest收集标记1 skipped，尚未证明真实恢复数值相等。Ruff通过。未访问服务器、未修改现有已评估smoke脚本、未提交。

模块src/cptla/reconstruction/checkpoint_state.py提供save_state/load_state。保存model.state_dict、optimizer.state_dict、torch CPU/CUDA RNG、Python random状态、step/cursor和canonical JSON配置SHA。输出目录独占，state.pt采用xb，最后manifest记录state SHA、torch版本、CUDA拓扑；失败留failure.json。不覆盖旧checkpoint。

load_state要求显式trusted=True，仅用于调用者确认的本项目自产快照。固定format、目录范围、文件SHA、配置SHA、状态/manifest一致、CUDA设备数量先校验，再torch.load(weights_only=True)，绝不退回不受限pickle。SHA保护意外修改，不提供恶意来源认证。读取后复验文件及manifest，恢复模型、optimizer及RNG。模型结构应由调用者提供并与保存模型一致；checkpoint加载失败后不继续优化。

测试tests/reconstruction/test_checkpoint_state.py使用Linear/Dropout/AdamW，比较连续2步与1步保存→新模型/optimizer恢复→1步参数torch.equal，并核验Python RNG相等；另测配置不匹配、state文件篡改、已有目录拒绝覆盖。命令：PYTHONPATH=src python -m pytest tests/reconstruction/test_checkpoint_state.py -q -o addopts= --basetemp 新目录。本地两次均因torch不可用跳过，实际CPU torch结果待root在已具备环境的服务器执行。该测试通过也仅证明小网络恢复，不代表真实Qwen断点恢复或G2全部通过。
