# Zako Shell Companion 架构

Zako 由用户现有的 Zsh 扩展和按需启动的 Rust Core CLI 组成。原生 Zsh 负责命令解析、执行、状态、信号、作业控制和 ZLE；Core 只计算角色反馈与纠错建议。

## 会话与事件

初始化调用 `zako session`，校验 TOML 并获得一次性配置快照。快照、角色状态、连续失败次数和最近建议只保存在 Shell 内存中。`zako on/off` 立即改变当前会话；修改文件后新开 Shell 生效。

`preexec` 清除过期建议并记录普通命令；`precmd` 首先保存原生命令退出码，通过参数调用 Core，把已校验的返回值用于反馈、状态与建议。`chpwd` 清空建议。单独的 `zako fix/status/stats/config/doctor` 不覆盖待纠错命令，含复合语法的普通输入仍会使其过期。

三个 Hook 都通过 `add-zsh-hook` 注册，并返回零以继续插件 Hook 链；Zsh 自身在 Hook 之间及提示符处保留原生命令状态。重复 source/eval 不重复注册或问候。

## 内部协议与调用预算

Shell 调用 `zako --shell-transport session|event`。私有进程替换管道先输出 worker PID，随后 worker 直接 exec Core，仅启动一个短命子进程。Core 成功完成请求后输出 `S:0`；错误没有成功尾标。父 Shell 用 `zsh/system` 的 `sysread` 有界读取，默认总预算 250ms、最多 32768 字节；无成功尾标、格式错误或到期会停用集成并终止未完成 worker。

内容为版本 2 的单行 U+001F 分隔字段，保留空字段。session 为 6 字段：版本、初始开关、Prompt 模式、标记、问候、JSON 配置快照。event 为 14 字段：版本、Mood、失败次数、分类、台词、标记、建议数量、三组候选/原因、会话聚合 JSON。Shell 校验字段数量、枚举、整数、字符、标记及候选数量一致性，然后更新状态；不 eval Core 响应。Shell 将聚合 JSON 视为不透明数据（最多 4096 字节），下次由 Core 严格校验 schema 和有界窗口；不解释为 Shell 表达式。公开 `--json` 供诊断与测试。

该边界没有常驻进程、全局 coprocess、外部 timeout 或持久化命令文件。Core 不执行建议、不捕获用户命令输出、不联网、不持久化原始命令。

## 反馈、雌小鬼台词与统计

成功、Ctrl+C 和可靠中性结果打断连续失败。简单 grep/rg/diff/test/[ 的退出码 1 为中性，退出码 2 或复杂语法保守标为未知。第三次失败可绕过冷却提示帮助一次，后续普通反馈须等待冷却到期。默认 active 档成功概率 35%、间隔 20 秒；quiet 静默、chatty 更积极，普通台词仍限流。纠错提示优先，`fix` 不限流。

角色风格默认是 `brat`（雌小鬼）：台词可以嘴硬和挑衅，但纠错消息必须保留可执行的建议。`persona.intensity` 为 1–5 级，`interaction.failure_escalation` 控制连续失败升级，`interaction.command_commentary` 控制 Git、Cargo、rm、sudo 和 Docker 等命令类型点评。五档有独立台词，昵称始终指向用户；`gentle` 与 `normal` 保留为低刺激配置，旧 `spicy` 兼容为 `brat`。命令分类仅在保守识别的简单输入上生效，点评不推断具体失败原因。

`session::State` 负责聚合命令结果、当前/最高成功连胜、六种固定命令家族的失败排行与两种一次性成就。Shell 只持有和往返 JSON。`session.enabled=false` 停止统计和成就；失败预算独立开关，仅保留最多 100 个短期失败时间戳。无原始命令、路径、输出或跨会话数据。

默认 60 秒内 5 次失败触发预算提醒，窗口内最多一次，服从普通冷却。反馈优先级为纠错、第三次连续失败、预算、成就、普通台词，每个事件至多一条；成就即使被静默/冷却抑制也保留解锁状态。`zako stats` 展示战报；`stats reset` 清零聚合状态、成就和预算，但不修改角色状态或连续失败计数。关闭 Zako 期间不记录结果。

`zako config path/show/init/set` 使用同一 Config 校验器；init 独占创建带注释默认配置，set 经 toml_edit 保留注释、完整验证后同目录原子替换。拒绝修改符号链接配置。修改在新 Shell 读取，不热更新当前配置快照。

退出码 127 才支持纠正不存在的命令名；固定 Git 子命令另有规则。只检查 PATH 中小范围低风险工具候选，不遍历全部目录。候选必须可执行；拒绝控制字符、展开、复杂语法、引号及高风险原始输入和最终候选。最多展示三条，始终由用户手动输入执行。

## Prompt 与故障

auto 模式仅在 RPROMPT 空闲时接入。用户或主题接管后停止更新；off/on 可以在空闲时恢复表情，不清除用户内容。`prompt.mode=off` 保持关闭。手动主题可在启用 prompt substitution 时引用 `${_ZAKO_PROMPT_MARKER}`，由主题自行控制装饰。doctor 报告配置快照、Hook 和降级原因。

Core 消失、非零、挂起、配置或协议损坏时，错误只提示一次，清空表情和建议并安全停用；原生 Shell 继续。故障总预算与进程回收通过 PTY 注入测试验证。250ms 是故障等待上限，正常新增延迟单独以完整 Hook 路径测量。

## 验证边界

支持声明限于本机 macOS arm64 / Zsh 5.9、Oh My Zsh robbyrussell 和 git/z/autosuggestions/fzf/syntax-highlighting 两种加载顺序。Zako 无 Tab、Alt+Z 或其他 ZLE widget/绑定。初始重构证据见 [M1 验收记录](milestones/M1-acceptance.md)；当前角色/会话功能的完整门禁、性能与真实安装结果见 [雌小鬼互动验收](milestones/brat-companion-acceptance.md)。Linux、Starship、Powerlevel10k 和长期日用体验另行验证。
