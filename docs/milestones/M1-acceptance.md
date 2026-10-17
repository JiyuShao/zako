# M1 验收记录

Completion: passed
Date: 2026-10-16

本文件记录初始重构版本的历史快照。后续角色与会话功能的验收、当前安装结果见 [雌小鬼互动验收](brat-companion-acceptance.md)。

已完成 7 项执行计划、正式本地安装和真实登录 Zsh 的端到端验收。验证平台为 macOS-26.5-arm64-arm-64bit-Mach-O，zsh 5.9 (arm64-apple-darwin25.0)，rustc 1.99.1 (58cf8f9c3 2026-10-13)。

## 完整门禁

`python3 scripts/verify_m1.py --full` 返回 0，13 个步骤全部通过。原始结果：[summary.json](../../target/m1-validation/full-l40yz3sz/summary.json)，每步日志在同目录。

| 检查 | 结果 |
| --- | --- |
| 格式、Clippy、release、Zsh/Bash 语法、diff 空白 | 全部通过 |
| Rust 单元测试 | 5 项通过 |
| 真实 Core CLI | 11 组通过，含分类、概率/冷却、配置快照、参数、纠错风险和 transport |
| 基础集成 smoke | 真实二进制通过 |
| 干净 Zsh PTY | 13 项通过，含故障注入子场景 |
| 目标插件 PTY | 两种加载顺序各 14 项，共 28 项通过 |
| 性能 | 8 组均通过；每组预热 30 次，500 对样本 |
| 隔离安装和移除 | 离线源码安装、打包初始化、新会话 on/off、移除初始化后新会话均通过 |
| 正式安装后的真实启动配置 | 8 项登录 Shell PTY 测试通过 |

干净/插件 PTY 覆盖退出码 0/1/2/127/130、管道及 pipefail、前后 Hook、实际 Ctrl+C、目录切换、建议失效、多候选、on/off/on、Prompt 所有权、配置时机、重复 source/eval、非交互、初始化移除、Core 失踪/挂起/非零、非法协议与控制字符。故障降级不执行注入文本，挂起 worker 有界终止。

目标组合：Oh My Zsh robbyrussell + git、z、zsh-autosuggestions、fzf、zsh-syntax-highlighting。测试比较原绑定，并实际执行 Tab 补全、fzf Ctrl-T 选择、自动建议显示/接受和高亮状态检查。版本为 OMZ `e0d3557e14e52da0426471b565496eb36712c0e9`、autosuggestions `85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5`、syntax-highlighting `1d85c692615a25fe2293bdd44b34c217d5d2bf04`、fzf `0.73.1 (Homebrew)`。未升级插件。

## 性能

配对测量完整 PTY 往返（输入到下一 Prompt），交替先运行有/无集成；每对差值为 integrated − baseline，分位数为 nearest rank。包括 Hook、Core 启动、读取/校验、反馈与 Prompt 消费；不计每条命令的 Shell 启动，不移除慢样本。8 组共 4000 对样本，全部新增 p95 < 10ms。

下表单位 ms，为新增耗时；插件本身耗时保留在原始 baseline/integrated 数据中。

| 环境 | 场景 | p50 | p95 | p99 | 最大值 |
| --- | --- | ---: | ---: | ---: | ---: |
| clean | success | 4.062 | 4.320 | 4.501 | 4.693 |
| clean | failure | 4.131 | 4.370 | 4.513 | 4.985 |
| clean | correction | 4.222 | 4.884 | 5.415 | 6.881 |
| clean | off | 0.054 | 0.090 | 0.147 | 3.304 |
| plugins | success | 3.458 | 6.272 | 10.535 | 73.405 |
| plugins | failure | 3.302 | 5.326 | 8.800 | 12.844 |
| plugins | correction | 3.276 | 4.355 | 5.415 | 6.109 |
| plugins | off | 0.134 | 0.820 | 1.289 | 1.809 |

启动时间按每组单独记录，未混入命令采样。环境、源代码/二进制 SHA256、原始 8000 次往返数据、差值及启动时间见 [performance.json](../../target/m1-validation/full-l40yz3sz/performance.json)。

初次测量 full-f2o8aw54 的 clean/failure p95 11.633ms、plugins/correction p95 10.408ms，按失败保留。将两子进程调用优化为 worker 直接 exec Core 的单子进程调用后达到当前结果，没有放宽阈值或丢弃样本。

## 正式安装与真实配置

- 二进制：`/Users/jiyu/.cargo/bin/zako`，版本 `zako 0.1.0`，与完整门禁二进制 SHA256 一致。
- 已在 `/Users/jiyu/.zshrc` 末尾追加唯一初始化标记块，原内容完整保留；前后语法检查通过。
- 完整备份：`/Users/jiyu/.zshrc.zako-backup-20261016-230231`。
- [安装记录](../../target/m1-validation/local-install.json)。

真实配置验收执行：

```bash
python3 tests/zsh_pty.py --binary ~/.cargo/bin/zako --profile real --report target/m1-validation/real-installed.json
```

新登录 Zsh 读取真实 `.zshenv`、`.zprofile`、`.zshrc` 和存在的 `.zlogin`，历史、缓存及目录跟踪数据使用测试隔离路径。8 项通过：状态/Hook、Ctrl+C、中性非零、多个建议、开关/Prompt、Tab、fzf/自动建议/高亮、纠错生命周期。与去除 Zako 初始化块的同配置对照绑定一致。没有更改用户现有别名；真实 `cat → bat` 的装饰输出使最初两个测试断言失败，改为 `/bin/cat` 后全部通过，初始记录保留在 real-installed-first.json。

[真实配置结果](../../target/m1-validation/real-installed.json)。测试命令调整后的 clean Tab 和双顺序插件回归分别见 [final-tab-clean.json](../../target/m1-validation/final-tab-clean.json)、[final-widgets-plugins.json](../../target/m1-validation/final-widgets-plugins.json)。产品源码和安装二进制与完整门禁/性能记录再次校验一致。

## 使用与边界

新开终端即可加载。`zako fix` 查看建议，`zako off` 立即停用，`zako on` 重新启用，`zako doctor` 检查当前会话。永久停用删除 `.zshrc` 的 Zako 标记块后新开 Shell；可保留完整备份作为回退参考。

本次自动验收通过不等于长期日用观察完成。支持声明限于以上实测平台和插件组合；Linux、Starship、Powerlevel10k 后置。无 Tab/Alt+Z 接管、自动执行、联网、遥测、历史持久化或常驻服务。未推送或发布。
