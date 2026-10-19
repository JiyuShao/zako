# M1 自动执行计划

Status: ready-for-agent
Completion: passed
Updated: 2026-10-16

## 目标与终点

将当前 Rust Core + Zsh Extension 从“编译及基础集成通过”推进到“本机 M1 自动验收通过、可开始日用试用”。允许长时间连续执行，以验收结果为终点，不按固定工作时长提前结束。

完整交付包括：修复已确认需求内的缺陷、真实 Core 测试、真实终端测试、目标插件共存测试、性能报告、可重跑的统一检查入口和更新后的安装/验收文档。长期日用体验不能用自动测试代替，应单独标记为后续观察。

设计来源：[已确认需求](spec.md)、[ADR 0001](../../docs/adr/0001-shell-companion.md)、[ADR 0002](../../docs/adr/0002-m1-no-zle-keybinding.md)。附件只是设计输入，执行以已确认需求为准。

## 连续执行约定

1. 先读仓库 AGENTS.md、docs/agents/domain.md、GLOSSARY.md、相关 ADR 和本计划；读写票据前读 docs/agents/issue-tracker.md。
2. 按下表顺序执行。每完成一票，记录实现、命令、结果及残余限制，继续下一票，不逐阶段请求确认。
3. 普通实现选择、缺陷修复、测试补充、临时测试环境和文档同步由执行者自行处理。沿用用户确认的产品范围，不重新访谈已确认事项。
4. 每票的 Status 表示分工状态，保持仓库五种 triage 状态词；另用 Completion: pending / in-progress / passed / blocked 记录完成度。passed 必须附验证证据。
5. 失败时先保留可复现证据，修复最小原因，运行受影响检查。全量验证只在阶段汇合点或新变化影响其他部分时运行，避免无意义重复。
6. 上下文切换前更新本计划末尾的检查点。恢复时读取检查点与 diff，继续首个未完成依赖满足的任务。
7. 环境缺失先自行定位现有安装；网络/权限故障不能假装通过。可以推进无依赖任务，最后明确剩余阻塞。
8. 当前工作区包含上一阶段未提交的重构成果，属于本任务起点。保留这些成果及用户后续更改，不重置分支。沿用 codex/zsh-companion-m1 和 legacy-shell 回退引用。
9. 在当前会话持续执行；本计划不创建定时任务或后台代理。中断后可由同一聊天继续读取检查点恢复。

## 执行顺序

| 顺序 | 任务 | 依赖 | 交付 |
| --- | --- | --- | --- |
| 01 | [固定基线与验收入口](issues/01-validation-entrypoint.md) | 无 | 统一检查入口、隔离测试约定 |
| 02 | [修复 Core 行为与纠错边界](issues/02-core-contracts.md) | 01 | 确定性行为测试、保守纠错 |
| 03 | [修复 Zsh 生命周期与协议](issues/03-zsh-lifecycle.md) | 02 | 状态、配置、故障与 Prompt 契约 |
| 04 | [真实终端验收](issues/04-pty-acceptance.md) | 03 | PTY 驱动、控制键和退出码矩阵 |
| 05 | [目标插件共存](issues/05-plugin-compatibility.md) | 04 | 两种加载顺序、Tab/fzf/建议/高亮证据 |
| 06 | [性能测量与优化](issues/06-hook-performance.md) | 05 | 原始样本、p50/p95/p99、阈值检查 |
| 07 | [完整复验与交付](issues/07-final-acceptance.md) | 02–06 | 全量通过、验收记录、试用包 |

## 原始基线与调查记录

Rust 1.99.1、Cargo、rustfmt、Clippy、rust-analyzer、rust-src 已安装。macOS arm64 / Zsh 5.9、Python 标准库 PTY，以及本地 Oh My Zsh、autosuggestions、syntax-highlighting、fzf 可用。4 个 Rust 测试、格式、Clippy、release 构建和基础管道输入集成测试已通过。

以下保留实施前基线问题，现已完成相应修复，最终结果见验收记录：

- `zako off` 放弃 Prompt 所有权后，`zako on` 不恢复表情。
- `is_neutral_result` 把 grep/rg/diff 的所有非零退出都当作正常结果，可能掩盖真实错误。
- 失败反馈绕过普通冷却；第四次起持续静默，没有基于时间的恢复。
- 当前会话每次事件重新读取配置，与“新开 Shell 生效”的约定不一致。
- Shell 内部响应缺少版本/字段验证；空字段、命令中的标志样文本、Tab 和控制字符需要验证。
- Core 返回最多 3 个候选，Shell 仅保存第一个；应让展示与配置一致。
- 模糊候选可能把安全的错误拼写改成高风险命令；需校验最终候选，不能仅过滤原始输入。
- 初始化配置错误、Core 非零退出但写出部分响应、Core 卡住时的降级需要真实验证。
- Hook 保留退出码和保留其他插件 Hook 执行必须同时满足，不能只测 `false` 后的 `$?`。
- `doctor` 尚未提供会话集成、Prompt 降级原因与手动接入说明。

## 自动化接口

已提供统一入口：

```bash
# 构建与基础检查
python3 scripts/verify_m1.py --baseline

# 完整门禁，缺少测试程序仍会失败
python3 scripts/verify_m1.py --full
```

已实现以下接口，由统一入口调用：

```bash
python3 tests/core_acceptance.py --binary target/release/zako
python3 tests/zsh_pty.py --binary target/release/zako --profile clean --report <JSON路径>
python3 tests/zsh_pty.py --binary target/release/zako --profile plugins --report <JSON路径>
python3 tests/benchmark_hooks.py --binary target/release/zako --report <JSON路径>
```

优先使用 Python 标准库，避免为测试引入额外服务或包。所有脚本要有帮助文本、失败退出码、步骤/进程超时，以及失败时可定位的场景名。统一入口将每次执行的日志与 JSON 结果放在被 Git 忽略的 target/m1-validation/ 中；基线通过不能显示为完整 M1 通过。

## 隔离与可重复性

- 每个会话使用独立 ZDOTDIR、ZAKO_CONFIG_DIR、工作目录和测试历史文件；不覆盖 HOME、CODEX_HOME。完整门禁不加载用户整份 .zshrc；另设 real profile，按本次授权验证真实安装与启动配置。
- 从用户已安装的位置加载目标主题/插件，关闭 Oh My Zsh 自动更新；只读取插件安装，不升级插件。正式交付另外备份并追加真实 Shell 初始化。
- 测试命令使用临时仓库、临时可执行文件和标记文件；不执行真实删除、提权或强推。纠错的安全断言检查结果字符串和未发生执行的证据。
- 用合成命令记录日志，不复制用户命令历史、令牌、环境变量全集或真实业务输出。
- 概率与冷却以注入时钟/采样值做确定性验证，不靠长时间 sleep 或等待随机命中。
- 每个 PTY 场景等待可识别的就绪标记，设置有限超时并清理进程组；Ctrl+C 通过真实控制字符发送。
- 重试不能掩盖断言失败。只有证据表明属于瞬时环境故障才有限重试，保留第一次错误。

## 性能口径

使用 release 二进制，在同一机器同一轮测试中对照“无集成”和“有集成”。分别覆盖干净 Zsh、目标插件组合，分别报告成功命令、普通失败、可纠错失败以及关闭状态。

预热至少 30 次，每组至少 500 个有效样本。测量包括 preexec/precmd、Core 子进程和输出消费的完整新增路径；启动时间单列。记录系统/工具链版本、样本数、原始样本、p50/p95/p99、最大值和差值算法；不能只计 Core 内部耗时或把 Shell 启动混进每条命令。

M1 门禁为普通命令 Hook 新增耗时 p95 < 10ms。超标先依据测量优化，再重新测量受影响组；不放宽阈值、不隐藏慢样本。若目标在当前架构下仍无法达到，保留报告并将 M1 标记为未完成，解释具体瓶颈和最小后续方案。

## 验收标准

- Rust 格式、测试、Clippy、release 构建、Zsh/Bash 语法全部通过。
- Core 分类、冷却、概率边界、纠错及配置契约有确定性断言。
- 开启/关闭/故障状态下，命令输出、工作目录、退出码、其他 Hook 和原生输入行为均满足约定。
- 真实 PTY 覆盖 Ctrl+C、Tab、建议失效、on/off、重复加载和配置/Core 故障。
- 目标插件组合的两种加载顺序通过；缺少依赖应报环境阻塞，不可跳过后宣称兼容。
- 性能口径和 p95 目标通过，有可追溯数据。
- 隔离目录内的源码安装、初始化与移除初始化后新会话的行为通过。
- `python3 scripts/verify_m1.py --full` 返回 0；所有任务 Completion: passed，证据与当前最终代码一致。
- docs/milestones/M1-acceptance.md、README、架构说明和 spec 状态准确，没有把未测项或基线结果冒充完整通过。

## 交付边界

完成上述工作并安装本地试用产物。用户于本次执行明确授权在真实 .zshrc 末尾加入初始化引用；保留其他内容，备份后追加，验证新 Shell。不添加 Tab/Alt+Z、自动执行纠错、AI、联网、遥测、历史持久化或常驻服务。未经另外要求，不推送、发布或创建远端 PR。

执行者可以自行修复上述范围内的问题，默认无需用户做中途设计决策。若遇到确实改变已确认产品行为的选择，先完成无关工作并记录具体选项，才集中说明阻塞。

## 最终检查点

- 01–07 全部 Completion: passed。
- 完整门禁：target/m1-validation/full-l40yz3sz/summary.json，13 步通过、退出 0。
- 性能：8 组全部 p95 <10ms，最慢 6.272ms；每组 500 对完整往返样本，源代码及二进制哈希与正式安装一致。
- 正式安装：~/.cargo/bin/zako；已备份并在真实 .zshrc 末尾追加唯一初始化块。
- 真实配置：target/m1-validation/real-installed.json，8 项新登录 Zsh PTY 通过；测试命令适配现有 cat→bat 别名后补跑受影响 clean/plugins 场景全部通过。
- 汇总与备份位置：docs/milestones/M1-acceptance.md。历史失败报告保留，未以重试隐藏产品断言。
- 自动执行任务已完成，无待确认项。长期日用观察、其他平台和主题属于后续范围。
