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
角色主动发言的频率与节制程度，默认档位为 `active`。
_Avoid_: 人格强度、主题

**人格强度（Persona Style）**:
角色台词的语气强弱，默认强度为 `normal`，与主动发言频率分别配置。
_Avoid_: 互动档位、主题
