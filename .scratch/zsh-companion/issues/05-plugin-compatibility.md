# 05 目标主题与插件组合共存

Status: ready-for-agent
Completion: passed
Depends on: 04

## 工作

完成 tests/zsh_pty.py 的 plugins profile：本地 Oh My Zsh、robbyrussell、git、z、zsh-autosuggestions、fzf、zsh-syntax-highlighting。自动定位实际安装，记录路径和可获得的版本/提交；不联网更新，不 source 用户整份 .zshrc。

在临时 ZDOTDIR 中分别测试“插件先加载、Zako 后加载”与“Zako 先加载、插件后加载”，保留 syntax-highlighting 所需的插件内部顺序。与相同 fixture 不加载 Zako 的对照比较。

- bindkey/ZLE widget 注册在加入 Zako 前后不被其覆盖；真实 Tab 输入仍可补全临时目录文件。
- fzf widget/绑定可用，在临时合成候选上实际触发并退出，不要求用户手动操作。
- autosuggestions 使用临时合成历史，实际出现并接受建议；syntax-highlighting 对合成输入仍生效，使用状态/渲染证据判断。
- 已有 Prompt 内容不被覆盖，主题动态接管后停止更新，off/on 不清掉用户内容。
- 插件 Hook 与 Zako 同时执行；成功、失败、目录切换和 fix 生命周期与 clean profile 一致。
- 插件初始化需要的临时缓存与历史写在 fixture 内；禁止自动更新和真实网络请求。

## 完成标准

plugins profile 两种加载顺序均通过，有版本、绑定、Hook 与真实输入行为证据。缺失插件或能力要失败并写明环境阻塞，不能 skip 后标记“兼容”。仅声明本组合支持，Linux/Starship/Powerlevel10k 仍后置。

## Comments

规划阶段已只读确认本机存在 Oh My Zsh、autosuggestions、syntax-highlighting 与 fzf 安装目录，尚未完成运行时兼容验收。

## 验证记录（2026-10-16）

plugins profile 两种加载顺序各 14 项，共 28 项通过；本机 OMZ/robbyrussell + git/z/autosuggestions/fzf/syntax-highlighting。真实 Tab、fzf Ctrl-T、建议出现及接受、高亮状态、绑定与无集成对照一致，前后 Hook 与 Prompt 共存通过。路径/版本/提交见 target/m1-validation/full-l40yz3sz/pty-plugins.json。z 插件 disown 写入引起的临时目录清理竞态只对 ENOTEMPTY 有界重试，不重试功能断言。
