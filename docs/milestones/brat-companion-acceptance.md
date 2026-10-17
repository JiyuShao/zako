# 雌小鬼互动验收

Completion: passed
Date: 2026-10-17

## 交付范围

默认雌小鬼角色，五档独立文案、自定义用户称呼、反向夸奖；保留 gentle/normal 并兼容旧 spicy。独立配置连续失败升级、简单命令家族点评、窗口失败预算、会话统计和成就。

会话战报包括成功/失败/纠错/中性/中断、当前和最高连胜、六类固定家族失败排行、两类一次性成就。关闭时不计数，不同 Shell 独立；reset 清零战报/预算/成就，但不修改角色状态和连续失败计数。统计不存原始命令、路径或输出，不写盘。

`config path/show/init/set` 支持带注释模板、已有文件保护、类型/范围/未知字段校验、保留注释和同目录原子替换。修改后新开终端生效；符号链接配置请直接编辑目标文件。

## 测试与证据

完整门禁 [full-u8e2dfbl/summary.json](../../target/m1-validation/full-u8e2dfbl/summary.json) 的 13 步全部通过。

| 检查 | 结果 |
| --- | --- |
| fmt、Clippy、release、语法、smoke、diff 空白 | 全部通过 |
| Rust 单元测试 | 5 项通过 |
| Core CLI 行为 | 15 组通过 |
| 干净 Zsh PTY | 15 项通过，含故障注入 |
| 插件 PTY | 两种加载顺序各 16 项，共 32 项通过 |
| 性能 | 8 组、每组预热 30 次及 500 对样本，全保留；最大新增 p95 5.710ms < 10ms |
| 隔离源码安装、初始化和移除 | 3 项通过 |
| 安装后的真实登录 Zsh | 11 项通过 |

真实安装后的 [PTY 结果](../../target/m1-validation/brat-real-installed.json) 包括新增战报/成就/配置、会话隔离、关闭不计数、reset 再次解锁、状态和 Hook 链、Ctrl+C、中性结果、多候选、Tab、fzf、自动建议与高亮、纠错生命周期和冷却/预算。真实 `.zshrc` 的既有接入块继续使用，无新增启动文件修改。

二进制已更新至 `/Users/jiyu/.cargo/bin/zako`，版本 `0.1.0`。安装文件、release 文件和性能报告的二进制 SHA256 一致；性能报告中的产品源码摘要也与最终源码一致。详见 [安装核对记录](../../target/m1-validation/brat-install-manifest.json)。二进制 SHA256：`4cb71c98b2a27d671d67b12b4155fc9430b15784d5fb6c4b3fa53e8337ba48a7`。

## 性能

测量完整 PTY 往返，基线和集成轮流先运行；无样本剔除、无阈值调整。数据和环境见 [performance.json](../../target/m1-validation/full-u8e2dfbl/performance.json)。

| 环境 | 场景 | 新增 p95 / ms |
| --- | --- | ---: |
| clean | success | 3.989 |
| clean | failure | 4.328 |
| clean | correction | 4.787 |
| clean | off | 0.088 |
| plugins | success | 4.998 |
| plugins | failure | 5.348 |
| plugins | correction | 5.710 |
| plugins | off | 1.037 |

## 诊断与修复记录

首次门禁 `full-k8vps62q` 在新增 PTY 用例失败：内部命令识别把换行写入字符类的方式错误，导致字母 n 也被过滤，`zako config set` 被当普通命令清除了纠错目标。修正为独立换行匹配，新增用例验证配置命令保留建议且不计入战报；定向回归通过。该失败记录保留，没有放宽断言。

支持边界仍为本机 macOS arm64 / Zsh 5.9 和已安装插件组合；未新增 Linux 或其他主题的兼容承诺。


第二次门禁 `full-kl24_6kg` 的 plugins/off 新增 p95 为 20.004ms，按失败保留。缩小到 150 对样本的诊断同时运行了两份完全未加载 Zako 的插件会话，这一空白对照也出现 38.954ms 的配对差值 p95；同期系统有多路并行编译任务。数据见 [off-diagnostic.json](../../target/m1-validation/off-diagnostic.json)，诊断脚本保留在 `target/m1-validation/off-probe.py`。负载回落后重跑原完整门禁通过，产品源码、样本数、统计方式和门槛均未因此修改。这个结果说明共享主机负载会影响微小配对差值，最终数字代表本次实测条件。

没有残留产品调试日志；诊断脚本和原始失败结果只留在忽略的 target 验收目录。README 和完整带注释的 config.example.toml 已同步。新开终端加载更新后的嵌入式集成；旧终端可能因内部协议升级安全停用。


## 后续：Cargo 包名统一

包名和命令名现均为 `zako`。包名调整后，Rust 测试 5 项、Core CLI 15 组和隔离安装验收 4 项通过，后者包含 `cargo uninstall zako` 实测；本机 Cargo 安装清单已迁移为 `zako v0.1.0`。本节以前的摘要对应角色功能验收快照；包名调整后的安装摘要见 [package-rename.json](../../target/m1-validation/package-rename.json)，新安装文件与当前 release 的 SHA256 一致。
