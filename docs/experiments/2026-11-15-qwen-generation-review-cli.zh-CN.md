# 2026-11-15 Qwen受限生成与独立评分CLI

状态：本地工具及3项mock测试完成，未访问服务器、未做真实模型生成、未提交。

scripts/review_reconstruction_qwen_smoke.py提供generate与score子命令。共同参数--project-root、--smoke-run、--run时间戳；generate默认--max-new-tokens 4096，允许显式增加至32768，--gpu默认0。score额外需要--generation-run，必须为同一个smoke的已完成generate目录。

生成只读取已完成smoke的config、prepared/upstream/source/prediction和原始train输入，不读取targets；从已校验原始输入继承source_pages，按页码/part_index提供多图和局部预测。组数限制1–16，拒绝覆盖或身份不一致。GPU20GiB启动/8GiB前后保护，项目内离线cache，无进程终止。冻结smoke模型和adapter哈希逐项对账、所有输入末尾复验，输出目录独占。

不删Markdown围栏、不修HTML、不补span、不截取table。标准tokenizer去模型特殊token解码正文，clean_up_tokenization_spaces=False，保存正文、token数、EOS与truncated状态；到预算仍无EOS按truncated保留失败分母。score才读取GT目标，按现有严格grid诊断全部组评分，不改变官方协议。summary永久G2_passed=false。

TDD先缺脚本失败，再实现；3项mock覆盖生成API没有target输入、来源页原样继承、输出覆盖、围栏原样保留、截断标注、超过16组/重复组/assistant标签拒绝。Ruff通过。当前尚无真实生成或200表结果变化；CLI运行环境与模型兼容仍需root真实核验。源代码和日志hash由新run记录。
