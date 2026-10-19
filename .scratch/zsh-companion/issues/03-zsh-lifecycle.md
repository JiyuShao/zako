# 03 Zsh 生命周期、配置与内部协议

Status: ready-for-agent
Completion: passed
Depends on: 02

## 工作

- 开启、关闭、重新开启分别验证角色状态与 Prompt；仅在 auto 模式且无他人占用时恢复表情，绝不抹掉用户/插件 RPROMPT。prompt.off 不能因 on 被开启。
- 默认禁用配置、初始化损坏配置、会话内损坏配置、新会话读取新配置分别覆盖；实现已确认的“配置新开 Shell 生效”，同时保留 on/off 的会话即时控制。
- 普通命令开始、切换目录和 off 清除待纠错命令；fix/status/doctor 等内部命令不覆盖；普通复合命令不能因以 zako 开头就永久保留陈旧建议。
- 真实 Core 返回 1–3 个建议，Shell 正确保留并按配置展示候选与原因；空字段与静默反馈不串列。
- 验证内部协议的版本、字段数、枚举、数值和字符边界；Shell 不 eval 响应、不用未校验字段做算术。先复现当前 TSV 是否丢空列，再决定保留或调整编码；无需通用复杂协议。
- Core 非零但写出部分输出、空输出、乱码/损坏字段、消失及挂起均安全降级。故障只提示一次，清空表情与建议，原生 Shell 继续。为挂起路径建立可测的有限响应预算，并确保没有孤儿进程或常驻服务；若实现影响性能，交由 06 实测。
- 保留退出码与继续运行其他 precmd/preexec/chpwd Hook 同时测试，包括本 Hook 前后各有一个 Hook 的组合；不能靠返回非零阻止后续 Hook。
- doctor 展示当前会话启用、Hook、Prompt 装饰或降级原因；提供实际可用的手动 Prompt 接入方式或明确受支持边界。
- 重复 eval/source 均不重复 Hook/问候且不提前退出当前 Shell；局部选项隔离，避免依赖用户任意 Shell options。

## 完成标准

相关行为有真实 Core 测试；故障注入可以使用一次性受控替身，但不能代替正常 Core。on/off 恢复、空字段、配置时机、Hook 链和降级场景可重跑，并为 04 提供稳定接口。更新架构说明，禁止声称未实现的超时能力。

## Comments

默认不做新架构扩张；优先最小变更把配置与协议责任收拢到明确模块。

## 验证记录（2026-10-16）

配置快照、1–3 候选、空字段、on/off Prompt 恢复、用户 Prompt 接管、重复 source/eval、选项隔离、前后 Hook 与原生退出码均通过。版本 1 使用 U+001F 字段；单 worker 管道 250ms 有界调用，故障提示一次并停用。证据：target/m1-validation/full-l40yz3sz/pty-clean.json；协议详见 docs/architecture.md。
