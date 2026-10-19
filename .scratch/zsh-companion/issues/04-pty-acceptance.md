# 04 干净 Zsh 的真实终端验收

Status: ready-for-agent
Completion: passed
Depends on: 03

## 工作

新增 tests/zsh_pty.py，支持 `--binary`、`--profile clean|plugins`、`--report`。本票完成 clean，05 完成 plugins。使用 Python pty/select/termios，建立真实控制终端和前台进程组，按就绪标记同步，不使用无限等待。

- 模式区分：交互、非交互、重复 source、重复 eval、初始化移除后新会话。
- 开启/关闭/故障三种状态下测试 0、1、2、127、130 及管道退出码；检查用户输出与状态，正确处理 Zsh pipefail 的对照。
- 真实 Ctrl+C：启动可中断的合成前台命令，发送控制字符，验证返回提示符、计数重置、下一条命令能执行。Shell 作业控制仍由原生 Zsh 负责。
- gti、git comit、fix、下一条普通命令清空、cd 清空、多个候选、on/off/on 和 Prompt 所有权切换。
- 用可注入测试时钟覆盖冷却，不为验证 20 秒间隔反复 sleep；不改变生产默认值。
- 初始配置损坏、Core 丢失/异常/挂起、损坏响应各有有限超时和恢复断言，确认不执行任何建议。
- 按 03 的接口检查前后 Hook 的执行和退出码。比较有/无集成的 Shell 行为。
- 每场景失败输出场景名、必要的转录和状态；用进程组清理确保执行完没有遗留 Shell/Core。

## 完成标准

`python3 tests/zsh_pty.py --binary target/release/zako --profile clean --report <路径>` 返回 0，报告中场景有明确 passed/failed。故意破坏关键断言时测试必须失败；不能只匹配终端回显中的输入文本。

## Comments

已有管道输入脚本保留作快速 smoke；PTY 通过才证明控制键和交互生命周期行为。

## 验证记录（2026-10-16）

clean profile 13 项真实 PTY 测试通过（含多子场景）：状态矩阵、pipefail、Ctrl+C、建议生命周期、Tab、禁用配置、配置损坏、Core 消失/非零/挂起、协议注入及移除初始化。真实控制终端输入并按输出标记同步；有界清理测试 Shell。证据：target/m1-validation/full-l40yz3sz/pty-clean.json。
