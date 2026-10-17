# M1 不接管 ZLE 快捷键

用户现有的 Tab 行为可能由 Oh My Zsh、fzf、补全系统和 autosuggestions 共同包装，接管它需要处理加载顺序、widget 链、编辑上下文和卸载恢复。
M1 只通过 `zako fix` 展示纠错建议，不注册 Tab、Alt+Z 或其他 ZLE 快捷键，也不修改编辑缓冲区，以保留原生输入体验并降低插件冲突风险。
未来若重新引入快捷键，必须先完成针对目标插件组合的 ZLE/PTY 兼容实验。
