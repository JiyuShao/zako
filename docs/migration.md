# 从独立 Shell 迁移到 Shell Companion

当前分支把 `zako` 从独立交互 Shell 改为 Zsh Companion。旧执行栈曾自行处理 Parser、Executor、进程组、信号、Readline、变量和作业控制；这些职责不再进入新的产品路径。

## 回退

迁移前的提交保存在 `legacy-shell` 标签（如果本地 Git 元数据可用），实施分支为 `codex/zsh-companion-m1`。即使不保留本地标签，Git 提交历史仍是旧实现的回退源。

回退步骤：

```bash
git switch main
git show legacy-shell
```

切换回旧实现后，不要继续使用新的 `.zshrc` 初始化行；删除该行并打开新的 Shell。

## 兼容边界

- 旧版 `zako` 启动自研 Shell；新版 `zako` 是 CLI，不再创建 REPL。
- 旧环境变量配置和历史文件不自动迁移。
- 旧主题台词只筛选可接受文案后迁移到新的角色层。
- 新集成只在交互式 Zsh 中启用；非交互式 `zsh -c` 和 CI 不主动输出角色内容。

## 迁移原则

先验证 Zsh Hook 与 fail-open 行为，再逐步增加角色策略和纠错规则。任何新能力都不能重新引入 Shell 解析、执行、作业控制、持久化命令历史或后台常驻服务。

## 本机接入与移除

本次交付按用户明确授权安装到 `~/.cargo/bin/zako`，并在真实 `.zshrc` 末尾追加带 `Zako Shell Companion` 标记的初始化块；执行前保留完整备份。备份位置和验收结果见 [M1 验收记录](milestones/M1-acceptance.md)。产品 CLI 自身不修改启动文件。

当前会话执行 `zako off` 即停用。永久停用时删除该标记块，再打开新终端；无需删除其他插件初始化。卸载二进制可执行 `cargo uninstall zakosh`。回退旧实现前先移除新初始化块，避免调用旧版不支持的 `init` 子命令。
