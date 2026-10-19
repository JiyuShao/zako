# 01 固定基线与验收入口

Status: ready-for-agent
Completion: passed
Depends on: none

## 工作

读取 execution-plan.md；核对工作区、工具链与测试依赖。保留现有未提交成果。运行 `python3 scripts/verify_m1.py --baseline`，保存结果目录。

审查入口：失败退出码必须被传递，子进程有超时与清理，日志只含合成测试输入；完整模式缺少后续验收程序必须失败。核实现有基础集成测试确实加载临时 .zshrc。

明确后续测试 fixture：独立 ZDOTDIR、ZAKO_CONFIG_DIR、临时工作目录和历史文件；使用 Python 标准库，无额外包依赖。不要加载真实 .zshrc。

## 完成标准

基线通过；完整模式不会将缺项视作成功。记录命令、结果目录、工具版本以及任何真实环境阻塞，更新 Completion 与计划检查点。

## Comments

统一入口在规划阶段创建，尚需按本票验收后才算任务完成。

## 验证记录（2026-10-16）

- `python3 scripts/verify_m1.py --baseline`：退出 0，8 个检查通过。
- 结果：target/m1-validation/baseline-ib0taw63/summary.json；各检查独立日志保存在同目录。
- `python3 scripts/verify_m1.py --full`：按预期退出 2，明确列出 02–06 尚未实现的 3 个验收程序；结果为 incomplete，没有冒充完整通过。
- 工具：Cargo 1.99.1、Zsh 5.9 (arm64-apple-darwin25.0)、本地 Python PTY/统计模块；计划所需插件目录均存在。
- 现有 smoke 使用 `zsh -di` 和临时 ZDOTDIR，确实读取临时 .zshrc，不再使用会跳过初始化的 -f。
- 入口对子进程设定超时并按进程组终止；中断/失败传播非零退出码。全套 PTY 清理由后续 04 的真实终端测试验证。
- 无当前环境阻塞。下一票为 02。
