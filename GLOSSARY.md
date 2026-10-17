# Zako Shell Companion

Zako 的产品语言：为用户的日常命令行活动提供角色陪伴与可靠的纠错建议。

## Language

**Zako（Shell Companion，终端搭档）**:
依附于用户现有 Shell 的角色化命令行搭档，以持续陪伴、适度互动和实用帮助为核心价值。
_Avoid_: 独立 Shell、Shell 内核、终端模拟器

**角色反馈（Character Feedback）**:
Zako 针对命令行活动表达的角色状态或台词，是陪伴体验的组成部分。
_Avoid_: 命令输出、纠错建议

**纠错建议（Correction Suggestion）**:
针对命令中可可靠识别的错误提出的候选修正，供用户决定是否采用。
_Avoid_: 自动修复、自动重试

**待纠错命令（Correction Target）**:
最近一次失败且仍与当前操作上下文相关、供用户请求纠错的一条命令。
_Avoid_: 命令历史、上一条输入

**失败事件（Failure Event）**:
需要 Zako 提供失败反馈的一次命令结果，区别于用户主动中断或已明确识别的正常非零结果。
_Avoid_: 任意非零退出、命令拼写错误

**角色状态（Character Mood）**:
Zako 在当前 Shell 会话中根据命令事件表现出的轻量状态，包括待机、开心、不满、担心和得意。
_Avoid_: 好感度、长期记忆

**互动档位（Interaction Profile）**:
角色主动发言的频率与节制程度。
_Avoid_: 人格强度、主题

**角色风格（Persona Style）**:
角色表达反馈时采用的个性，包括雌小鬼式的嘴硬、挑衅和反向夸奖。
_Avoid_: 人格强度、互动档位、主题

**人格强度（Persona Intensity）**:
同一角色风格下，台词从轻逗到强烈奚落的程度。
_Avoid_: 角色风格、互动频率

**会话统计（Session Stats）**:
当前终端搭档会话中的命令结果概况，包括成功、失败、中性结果、中断和连续成功表现。
_Avoid_: 命令历史、跨会话分析、今日战报

**失败预算（Failure Budget）**:
一段时间内可容忍的失败事件数量，达到后触发暂停尝试、先行排查的提醒。
_Avoid_: 执行限额、命令阻断

**会话成就（Session Achievement）**:
同一次会话中达到连续成功或累计失败目标时获得的角色化纪念。
_Avoid_: 长期成长、好感度
