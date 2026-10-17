<h1 align="center">Zako Shell Companion</h1>

<p align="center">
  <strong>A bratty little companion for your terminal.</strong><br />
  雌小鬼陪你写代码。
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://www.rust-lang.org/"><img src="https://img.shields.io/badge/built_with-Rust-dea584.svg" alt="Built with Rust" /></a>
  <a href="#compatibility"><img src="https://img.shields.io/badge/shell-Zsh_5.9%2B-89e051.svg" alt="Zsh 5.9+" /></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#compatibility">Compatibility</a> ·
  <a href="#contributing">Contributing</a>
</p>

Zako is a lightweight Zsh companion written in Rust. It greets you when a shell starts, comments on commands from time to time, gets more impatient after repeated failures, and offers conservative corrections for typos such as `gti` and `git comit`.

It attaches to your existing Zsh through hooks. Zsh keeps ownership of command execution, completion, job control, signals, and editing. Zako 0.1.0 runs locally and speaks Simplified Chinese by default.

## See it in action

After a typo such as `gti status`, Zako keeps the suggestion available until you ask for it:

```console
❯ gti status
zsh: command not found: gti
You mistyped the command, dummy. Run `zako fix` and choose a candidate yourself.
❯ zako fix
Suggestion: git status
Reason: the command name may be git
Type and run it yourself; Zako never executes suggestions automatically.
```

The suggestion expires when you start another ordinary command, change directory, or turn Zako off.

### Bratty interaction examples

The default intensity is 3 and the default nickname is `杂鱼` (“dummy”). For example, after three consecutive failures:

```console
❯ false
这都能失败？杂鱼，先别乱按，看看错误输出。
❯ false
❯ false
连续失败 3 次了。杂鱼，承认需要本小姐提醒了吧？先看错误输出。
```

The second response is normally suppressed by the default 20-second cooldown; the third failure gets one reminder. Other example lines at intensity 3:

| Situation | Example |
| --- | --- |
| Shell startup | `♡ 嘿，杂鱼，今天也别把代码写坏了哦？` |
| Ordinary success | `哼，杂鱼，勉强算你做对了，别以为本小姐会一直夸你。` |
| Test or commit succeeds | `居然成功了？杂鱼，别得意，本小姐只是刚好在看。` |
| Five consecutive successes | `成就解锁：连胜小天才（连续成功 5 次）。杂鱼，别误会，本小姐只是替你记着，才没有偷偷鼓掌。` |
| Five failures in 60 seconds | `60 秒内已有 5 次失败。杂鱼，失败预算都刷光了，还想抽成功保底？先停下来排查。` |

Every command produces at most one event line, and correction suggestions take priority. Interaction profile, sampling, and cooldown still apply to achievements and failure-budget reminders.

The five `brat` intensity levels use different lines:

| Intensity | First-failure example |
| --- | --- |
| 1 · Light teasing | `杂鱼，这次没成功，看看错误输出吧。` |
| 2 · Stubborn | `哼，杂鱼，命令没有成功，检查一下输入。` |
| 3 · Provoking | `这都能失败？杂鱼，先别乱按，看看错误输出。` |
| 4 · Mocking | `杂鱼，这就翻车了？手速挺快，检查输入的速度跟上了吗？` |
| 5 · Full fire | `噗，杂鱼，回车的气势倒是满分，结果就这？先把错误输出读明白。` |

To make her harsher or change the nickname:

```sh
zako config set persona.intensity 5
zako config set persona.nickname "小菜鸡"
```

After opening a new shell, the greeting becomes:

```text
♡ 来了呀，小菜鸡？键盘都准备好了，就等你贡献笑话了。
```

## Features

- **Bratty companionship**: teasing, challenging, and occasionally praising, while still giving you a useful next step.
- **Five configurable intensity levels**: tune `persona.intensity` from light teasing to full fire; keep `gentle` and `normal` styles when you want less attitude.
- **Session stats and achievements**: inspect success streaks, failure categories, corrections, interruptions, and session-only achievements.
- **Failure budget**: get a reminder to stop and inspect errors after too many failures in a configurable time window. It never blocks commands.
- **Conservative correction**: recognize a small set of simple command-name typos and fixed Git subcommand typos, with up to three candidates and reasons.
- **Native input behavior**: keep your theme, Tab completion, widgets, and keybindings. Zako does not register Tab, Alt+Z, or any other ZLE shortcut.
- **Local and offline**: no account, API key, network service, telemetry, command-history persistence, or daemon.
- **Safe switch-off**: `zako off` stops interaction immediately. Invalid configuration or an unavailable Core disables the integration while leaving native Zsh running.

## Quick start

### 1. Install from source

You need [Rust stable and Cargo](https://rustup.rs/), Git, and **Zsh 5.9+**. The tested environment is macOS Apple Silicon; see [Compatibility](#compatibility) for the current support boundary.

```sh
git clone https://github.com/JiyuShao/zakosh.git
cd zakosh
cargo install --locked --path .
```

The Cargo package and executable are both named `zako`. Verify the installation:

```sh
zako --version
```

Cargo normally installs the executable at `~/.cargo/bin/zako`. If the command is missing, run `source "$HOME/.cargo/env"` and check that Cargo's bin directory is in `PATH`.

### 2. Connect it to Zsh

Append this to `${ZDOTDIR:-$HOME}/.zshrc`, after your theme and plugins:

```zsh
# Zako Shell Companion
if (( $+commands[zako] )); then
  eval "$(zako init zsh)"
fi
```

Zako does not edit your startup files. Keep only one initialization block.

### 3. Open a new shell

Run:

```sh
zako status
zako doctor
```

No configuration file is required. Oh My Zsh, fzf, and other plugins are optional.

## Usage

| Command | Purpose |
| --- | --- |
| `zako fix` | Show candidates and reasons for the current correction target |
| `zako on` | Enable Zako in the current shell |
| `zako off` | Disable it and clear suggestions and prompt decoration |
| `zako status` | Show session state, mood, and consecutive failures |
| `zako stats` | Show session totals, failure ranking, achievements, and streaks |
| `zako stats reset` | Clear current-shell stats, achievements, and failure budget |
| `zako config init` | Create the commented default config without overwriting an existing file |
| `zako config set persona.intensity 5` | Validate and save a configuration value |
| `zako config show` / `path` | Show the effective config or its path |
| `zako doctor` | Inspect configuration, hooks, and prompt integration |
| `zako --help` | Show command-line help |

`fix`, `on`, `off`, `status`, and `stats` require the Zsh integration. `config` works directly. The switches affect only the current shell; set `general.enabled = false` to start future shells disabled.

### Character feedback

When `prompt.mode = "auto"`, Zako shows a short ASCII marker such as `:3`, `:)`, or `:/` in an unused right prompt. Set `prompt.ascii_fallback = false` to use Unicode markers such as `♡ (¬_¬)`.

Successful commands reset consecutive failures. Ctrl+C and clearly neutral non-zero results, such as no-match `grep` or a differing `diff`, also reset the counter. The third consecutive failure can trigger one reminder; later ordinary feedback waits for the cooldown. By default, five failures within 60 seconds trigger one failure-budget reminder per window. It never prevents the next command. Corrections take priority, and `zako fix` is never rate-limited.

Five consecutive successes unlock “连胜小天才” (“streak genius”); ten cumulative failures unlock “不服输的杂鱼” (“persistent dummy”). Each achievement unlocks once per session, and `zako stats` shows the achievement state plus a Git/Cargo/Docker/rm/sudo/other failure ranking. Neutral results and interruptions are counted separately. Stats stay in memory, are never written to disk, and are isolated between shells.

### Correction boundaries

The current correction set covers simple cases such as `gti status → git status` and `git comit → git commit`. Quoted input, pipelines, redirections, expansions, complex shell syntax, and high-risk operations such as deletion, privilege escalation, force-pushing, or hard resets do not produce rewrite suggestions.

Zako never writes suggestions into the editing buffer and never executes them.

## Configuration

The default config path is `~/.config/zako/config.toml`. You can configure it without editing TOML by hand:

```sh
zako config init                         # Create the full commented config; never overwrite
zako config set persona.intensity 5      # 1 light / 2 stubborn / 3 provoking / 4 mocking / 5 full fire
zako config set persona.nickname "小菜鸡"
zako config set interaction.profile chatty
zako config set interaction.cooldown_seconds 5
zako config set interaction.failure_budget false
zako config set session.achievements false
zako config set session.enabled false    # Disable session stats and achievements
zako config show
zako config path
```

`config set` preserves comments, rejects invalid keys and values, and leaves the file unchanged when validation fails. Symlinked config files are rejected; edit the target directly. Changes take effect in a new shell because the current shell keeps its validated snapshot. See [config.example.toml](config.example.toml) for the full commented template.

You can also provide only the fields you want to override:

```toml
[interaction]
profile = "quiet"

[prompt]
ascii_fallback = false
```

`quiet` disables proactive event lines while keeping status and `zako fix` available. Set `startup_greeting = false` to hide the startup greeting.

<details>
<summary>Show the full default configuration</summary>

```toml
[general]
enabled = true
language = "zh-CN"

[interaction]
profile = "active"               # quiet | active | chatty
success_probability = 0.35        # 0.0–1.0; chatty ignores this probability
cooldown_seconds = 20             # ordinary feedback interval, 0–86400
startup_greeting = true
consecutive_failure_tip = true
failure_escalation = true
command_commentary = true
failure_budget = true
failure_budget_count = 5           # 2–100
failure_window_seconds = 60        # 1–3600

[persona]
style = "brat"                   # gentle | normal | brat; legacy spicy is accepted
nickname = "杂鱼"                 # user-facing nickname, up to 64 characters
intensity = 3                     # 1–5

[session]
enabled = true
achievements = true
success_streak_goal = 5           # 2–1000
failure_milestone = 10            # 2–1000

[prompt]
mode = "auto"                    # auto | off
ascii_fallback = true

[correction]
enabled = true
max_suggestions = 3               # 1–3

[privacy]
persist_command_history = false
telemetry = false
capture_command_output = false
```

Privacy settings must remain `false` in this version. Unknown configuration keys are rejected. Session statistics are memory-only and disappear when the shell exits. `style` selects the character style; `intensity` controls the five `brat` levels. Legacy `spicy` is treated as `brat`.

</details>

Config lookup order:

1. `$ZAKO_CONFIG_DIR/config.toml`
2. `$XDG_CONFIG_HOME/zako/config.toml`
3. `~/.config/zako/config.toml`

Configuration is read when a new shell starts. `zako on` and `zako off` take effect immediately. A broken config causes one warning and a safe integration shutdown; open a new shell after fixing it.

## Compatibility

| Environment | Status |
| --- | --- |
| macOS Apple Silicon + Zsh 5.9 | Verified with real terminal E2E tests |
| Oh My Zsh + robbyrussell | Verified prompt and hook coexistence |
| git, z, zsh-autosuggestions, fzf, zsh-syntax-highlighting | Verified in both plugin load orders with real input |
| Linux, other architectures, Starship, Powerlevel10k | Not verified yet |
| Bash, Fish | No integration currently provided |

If a theme or user already owns `RPROMPT`, Zako yields the right prompt while keeping feedback and corrections available. Run `zako doctor` to see the integration reason.

### Performance

On macOS arm64 / Zsh 5.9, eight clean/plugin scenarios used 30 warmups and 500 paired samples each. Added p95 stayed below **10 ms** in every scenario; the slowest was **5.71 ms**. The current character and session features are included in the measurement. See the [acceptance record](docs/milestones/brat-companion-acceptance.md).

The benchmark measures the complete round trip from input to the next prompt, including hooks, Core startup, response validation, and prompt consumption. Startup time is recorded separately and slow samples are retained. Re-run [tests/benchmark_hooks.py](tests/benchmark_hooks.py) on your own machine for local measurements.

## Troubleshooting and uninstalling

- **`zako` is not found**: check that `~/.cargo/bin` is in `PATH` and run `zako --version`.
- **`zako fix` says the integration is not loaded**: check the initialization block in your interactive Zsh `.zshrc`, then open a new shell.
- **No right-prompt marker**: run `zako doctor` and check `prompt.mode` and whether the theme owns `RPROMPT`.
- **The integration disables itself**: run `zako doctor`, fix the reported configuration, and open a new shell.

Temporarily disable it:

```sh
zako off
```

For permanent removal, delete the marked Zako block from `.zshrc` and open a new shell. Uninstall the Cargo package with:

```sh
cargo uninstall zako
```

See [migration notes](docs/migration.md) for users of the former standalone shell.

## Contributing

Issues and pull requests are welcome at [GitHub](https://github.com/JiyuShao/zakosh). When reporting compatibility issues, include your architecture, Zsh version, plugins, and a minimal reproduction.

Run the local checks:

```sh
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo build --locked --release
zsh -n integrations/zako.zsh
bash tests/zsh_integration.sh target/release/zako
```

The full Python gate runs:

```sh
python3 scripts/verify_m1.py --baseline
python3 scripts/verify_m1.py --full
```

The complete gate covers the Core CLI, PTY behavior, target plugin combinations, performance, and isolated installation/removal. It uses locked offline dependencies and requires the local Oh My Zsh, autosuggestions, syntax-highlighting, and fzf fixtures for plugin tests. Logs and JSON reports are written under `target/m1-validation/`.

See the [architecture notes](docs/architecture.md) for module boundaries and the event protocol. Extensions should preserve Zsh ownership of command execution and editing, local execution, and manual adoption of suggestions.

## License

[MIT](LICENSE) © Jiyu Shao
