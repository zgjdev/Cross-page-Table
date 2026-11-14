# 2026-11-14 图像近重复候选CPU工具实施

状态：本地实现及合成测试完成；未访问服务器，未运行真实train全量审计，无新科研指标。

新增 scripts/audit_reconstruction_visual_duplicates.py，只接受项目内train输入清单，唯一图片路径按清单SHA在读前、读后和结束前复验。低分辨率灰度9×8水平比较产生64位dHash（不是pHash）。距离<=4的跨文档候选采用13/13/13/13/12位五分桶检索；四个不同bit至多影响四桶，至少一桶相同，随后完整Hamming复核。该保证只针对dHash距离阈值，不保证语义近重复召回。空白页碰撞、旋转/裁剪/版式变化漏检均可能存在。

run要求UTC时间戳，目录独占；保留输入、实现、产物及原图hash、argv、配置、Python/Pillow版本和commit。summary最后写入，失败保存failure.json；limit-images输出partial。候选阈值未经人工校准，training_authorized固定false，不改变split；仅train，不能得出跨官方split或预训练污染结论。

TDD：先写tests/reconstruction/test_visual_duplicates.py；系统Python缺Pillow，改用项目.venv后确认缺实现文件的预期失败。实现后默认pytest临时目录权限失败，采用新项目内basetemp。最终4项通过，包含固定和随机变异hash与穷举参照对账、同文档排除、SHA失败留痕、非train/越界拒绝、目录独占和partial。Pillow getdata有未来弃用警告，不影响当前结果。

验证命令：`.venv/Scripts/python.exe -m pytest tests/reconstruction/test_visual_duplicates.py -q -o addopts= --basetemp artifacts/visual-duplicate-tests-20261114-02`。

后续实际运行需传入 --project-root、--inputs、--run，可先 --limit-images 20。全量完成后仅能称图像指纹候选审计完成；候选审查与联合文本污染处置另留版本化证据。
`n追加审查修复：原实现仅信任source_split字段不足以证明实际train来源。新增四个先失败回归，核验伪train的val路径、revision、文档ID和页码；实现严格限定固定train/images目录且拒绝目录重定向、固定数据revision、文件名身份与记录一致。8项测试通过（basetemp artifacts/visual-duplicate-tests-20261114-05）；Ruff通过。旧4项通过记录保留，不代表当时具备本轮来源防护。
