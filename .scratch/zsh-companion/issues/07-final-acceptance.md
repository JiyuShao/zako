# 07 完整复验、文档与试用交付

Status: ready-for-agent
Completion: passed
Depends on: 02, 03, 04, 05, 06

## 工作

- 在临时安装前缀执行源码安装，例如 `cargo install --offline --locked --path . --root <临时目录>`，检查 bin/zako 版本与初始化。不覆盖用户已有可执行文件。
- 通过临时 .zshrc 加入初始化行运行新会话；移除该行再运行新会话，无角色问候、Hook 或 Zako 函数残留；既有会话 off 可以停用。
- 运行 `python3 scripts/verify_m1.py --full`，审阅所有结果，确保失败传播、缺项失败且无遗留进程。对应最终代码保存结果路径。
- 自审范围：是否仍接管 Shell 语义、ZLE、执行建议、持久化历史、遥测或后台服务；是否覆盖已确认需求；修复发现的真实问题后只重跑受影响部分及最后门禁。
- 同步 README、docs/architecture.md、docs/migration.md、docs/milestones/M1-acceptance.md、spec.md、execution-plan.md 与每张票据。记录实际平台、插件、样本和限制；不使用旧 Stub 结果替代真实验收。
- 产出本地 release 可执行文件、完整报告和简短试用说明。本次用户明确授权执行者安装，并备份真实 .zshrc 后在末尾追加初始化引用，随后以真实配置的新登录 Zsh 做 PTY 端到端验收；不自动发布/推送。

## 完成标准

所有依赖 Completion: passed，完整入口返回 0，隔离安装/卸载验证通过，最终 diff 可审阅，报告与最终代码一致。长时间真实日用观察单独列出，不冒充自动验收结果。一次性向用户报告成果、测试证据、产物路径和任何真实限制，无需逐阶段确认。

## Comments

若有无法解决的环境或性能阻塞，应保留结果并标明未完成项；不能仅因为工作时间长就结束并声称完成。

## 验证记录（2026-10-16）

完整门禁 13 步退出 0；隔离安装/移除通过。正式 cargo install 完成，真实 .zshrc 完整备份后末尾追加唯一引用；真实登录 PTY 8 项通过。文档同步、二进制/源码 SHA256 对照与原内容保留检查通过。证据汇总：docs/milestones/M1-acceptance.md；完整结果：target/m1-validation/full-l40yz3sz/summary.json；真实安装：target/m1-validation/real-installed.json。
