<h1 align="center">Zako Shell Companion</h1>

<p align="center">
  <strong>给你的终端，加一点傲娇。</strong><br />
  A little attitude for your Zsh.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://www.rust-lang.org/"><img src="https://img.shields.io/badge/built_with-Rust-dea584.svg" alt="Built with Rust" /></a>
  <a href="#兼容性"><img src="https://img.shields.io/badge/shell-Zsh_5.9%2B-89e051.svg" alt="Zsh 5.9+" /></a>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#使用">使用</a> ·
  <a href="#配置">配置</a> ·
  <a href="#兼容性">兼容性</a> ·
  <a href="#参与贡献">参与贡献</a>
</p>

Zako 是一个用 Rust 编写的轻量 Zsh 终端搭档：启动时打个招呼，命令完成时偶尔点评，连续失败时提醒你，并为 `gti`、`git comit` 这类拼写错误提供纠错建议。

它依附于你现有的 Zsh，通过 Hook 接收命令事件；命令执行、补全和作业控制都由 Zsh 负责。当前为 **0.1.0 早期版本**，角色台词支持简体中文。

## 看看效果

在已安装 Git 的环境中，输入 `gti status` 后，可以通过 `zako fix` 查看建议：

```console
❯ gti status
zsh: command not found: gti
命令拼写好像不对，我给你找了个可能的写法。
❯ zako fix
建议：git status
原因：命令名可能是 git
请手动确认并输入；Zako 不会自动执行。
```

你决定是否采用建议，再自行输入命令。下一条普通命令开始、切换目录或关闭 Zako 后，旧建议会失效。

## 特性

- **有性格的陪伴**：启动问候、五种角色状态，以及成功、失败和连续事件的反馈。
- **可调节的互动**：默认普通成功反馈概率为 35%，普通台词间隔至少 20 秒；互动频率与语气分别配置。
- **保守的纠错**：识别少量简单命令名和固定 Git 子命令拼写，最多展示三条候选及原因。
- **保留输入习惯**：沿用现有主题、Tab 补全和快捷键；右侧 Prompt 空闲时显示角色状态。
- **本地离线运行**：无需账号、API Key 或网络服务，无遥测、命令历史持久化或常驻进程。
- **随时开关**：`zako off` 立即停用；配置或 Core 出错时自动停用集成，保留原生 Shell。

## 快速开始

### 1. 从源码安装

需要 [Rust stable 与 Cargo](https://rustup.rs/)、Git，以及 **Zsh 5.9+**。已验证环境为 macOS Apple Silicon，完整支持范围见[兼容性](#兼容性)。

```sh
git clone https://github.com/JiyuShao/zakosh.git
cd zakosh
cargo install --locked --path .
```

安装后确认可执行文件已在 `PATH` 中：

```sh
zako --version
```

Cargo 默认将它安装到 `~/.cargo/bin/zako`。如果提示找不到命令，可先运行 `source "$HOME/.cargo/env"`，并确认新终端也能访问 Cargo 的 bin 目录。

### 2. 接入 Zsh

在 `${ZDOTDIR:-$HOME}/.zshrc` **末尾**加入以下内容，放在主题和插件初始化之后：

```zsh
# Zako Shell Companion
if (( $+commands[zako] )); then
  eval "$(zako init zsh)"
fi
```

Zako 自身不会修改启动文件。若已配置过初始化，保留一处即可。

### 3. 打开新终端

在新的交互式 Zsh 中运行：

```sh
zako status
zako doctor
```

无需创建配置文件即可使用。Oh My Zsh、fzf 和其他插件均为可选组件。

## 使用

| 命令 | 作用 |
| --- | --- |
| `zako fix` | 查看当前待纠错命令的候选与原因 |
| `zako on` | 开启当前 Shell 会话中的 Zako |
| `zako off` | 立即关闭，并清除待纠错建议和自动 Prompt 装饰 |
| `zako status` | 查看当前会话的开关、角色状态与连续失败次数 |
| `zako doctor` | 检查配置、Hook 和 Prompt 接入情况 |
| `zako --help` | 查看 CLI 帮助 |

这些会话命令需先加载 Zsh 集成。开关只影响当前 Shell；长期默认关闭可设置 `general.enabled = false`。

### 角色反馈

默认在空闲的右侧 Prompt 显示简短 ASCII 表情，例如 `:3`、`:)` 和 `:/`。设置 `prompt.ascii_fallback = false` 后，可显示 `♡ (¬_¬)` 等 Unicode 表情。

成功命令会打断连续失败计数；Ctrl+C 和能明确识别的正常非零结果（例如简单 `grep` 无匹配、`diff` 有差异）也会重置计数。第三次连续失败可触发一次帮助提醒，之后普通反馈继续受冷却限制。纠错提示优先，主动执行 `zako fix` 不受限流。

### 纠错范围

目前覆盖 `gti status → git status`、`git comit → git commit` 等简单拼写场景。带引号、管道、重定向、展开或复杂 Shell 语法的输入，以及删除、提权、强推等高风险场景，不生成改写建议。

Zako 不注册 Tab、Alt+Z 或其他 ZLE 快捷键，也不会把建议写入编辑缓冲区或执行它。

## 配置

默认配置文件为 `~/.config/zako/config.toml`。支持只填写需要修改的字段，例如：

```toml
[interaction]
profile = "quiet"

[prompt]
ascii_fallback = false
```

`quiet` 关闭主动事件台词，仍保留可用的角色状态和 `zako fix`。如需关闭启动问候，另设 `startup_greeting = false`。

<details>
<summary>展开完整默认配置</summary>

```toml
[general]
enabled = true
language = "zh-CN"               # 当前仅支持简体中文

[interaction]
profile = "active"              # quiet | active | chatty
success_probability = 0.35       # 0.0–1.0
cooldown_seconds = 20
startup_greeting = true
consecutive_failure_tip = true

[persona]
style = "normal"                # gentle | normal | spicy
nickname = "杂鱼"                # 帮助提醒中的称呼

[prompt]
mode = "auto"                   # auto | off
ascii_fallback = true

[correction]
enabled = true
max_suggestions = 3             # 1–3

[privacy]
persist_command_history = false
telemetry = false
capture_command_output = false
```

当前版本要求三个隐私选项均为 `false`，未知配置键会报错。

</details>

配置路径按以下优先级查找：

1. `$ZAKO_CONFIG_DIR/config.toml`
2. `$XDG_CONFIG_HOME/zako/config.toml`
3. `~/.config/zako/config.toml`

配置在**新开 Shell 时读取**；`zako on/off` 则立即生效。配置损坏时，集成只提示一次并停用；修复后打开新终端即可重新加载。

## 兼容性

| 环境 | 当前状态 |
| --- | --- |
| macOS Apple Silicon + Zsh 5.9 | 已通过真实终端端到端测试 |
| Oh My Zsh + robbyrussell | 已验证 Prompt 和 Hook 共存 |
| git、z、zsh-autosuggestions、fzf、zsh-syntax-highlighting 组合 | 已验证两种加载顺序及真实输入行为 |
| Linux、其他架构、Starship、Powerlevel10k | 尚未验证 |
| Bash、Fish | 当前未提供集成 |

已有主题或用户占用 `RPROMPT` 时，Zako 会让出右侧 Prompt，其他反馈与纠错功能仍可使用。可用 `zako doctor` 查看降级原因。

### 性能

在 macOS arm64 / Zsh 5.9 的一次本机验收中，干净 Zsh 与目标插件组合共 8 组场景，每组预热 30 次、采样 500 对，新增耗时 **p95 均低于 10ms**，最慢一组为 **6.27ms**。

测量覆盖从输入到下一提示符的完整往返，与无集成会话配对比较，包括 Hook、Core 启动及响应处理；启动时间单列，保留慢样本。该结果反映上述机器与配置，可用[性能脚本](tests/benchmark_hooks.py)在自己的环境中复测。

## 排障与卸载

- **找不到 `zako`**：确认 `~/.cargo/bin` 在 `PATH` 中，并且 `zako --version` 可用。
- **`zako fix` 提示先加载集成**：确认初始化位于交互式 Zsh 的 `.zshrc` 中，随后打开新终端。
- **没有右侧表情**：运行 `zako doctor`，检查 `prompt.mode` 和主题是否已占用右侧 Prompt。
- **配置错误或集成自动停用**：运行 `zako doctor` 查看原因，修复后打开新终端。

临时停用：

```sh
zako off
```

永久停用时删除 `.zshrc` 中的 Zako 初始化块，并打开新终端。卸载可执行文件：

```sh
cargo uninstall zakosh
```

Cargo 包名为 `zakosh`，安装的命令名为 `zako`。旧版独立 Shell 用户可参考[迁移说明](docs/migration.md)。

## 参与贡献

欢迎通过 [Issues](https://github.com/JiyuShao/zakosh/issues) 提交可复现的问题或功能建议，也欢迎提交 Pull Request。报告兼容性问题时，请附上系统架构、Zsh 版本、相关插件与最小复现步骤。

本地开发可先运行：

```sh
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo build --locked --release
zsh -n integrations/zako.zsh
bash tests/zsh_integration.sh target/release/zako
```

需要 Python 3 的统一验收入口：

```sh
python3 scripts/verify_m1.py --baseline
python3 scripts/verify_m1.py --full
```

完整验收包括真实 CLI、PTY、目标插件组合、性能与隔离安装/移除。它使用离线锁定依赖，需要先准备 Cargo 缓存；插件场景还依赖本地 Oh My Zsh、autosuggestions、syntax-highlighting 和 fzf，缺少依赖会明确失败。日志和 JSON 结果写入 `target/m1-validation/`。

模块边界与事件协议见[架构说明](docs/architecture.md)。扩展功能时，请保留 Zsh 对命令执行与编辑的控制权，以及本地运行、建议手动采用的约定。

## 许可证

[MIT](LICENSE) © Jiyu Shao
