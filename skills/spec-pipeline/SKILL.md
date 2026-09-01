# Spec Pipeline — 派发/复测/checkpoint 循环

按 spec 索引逐个执行交付 spec 的标准循环(本 repo specs/EXECUTION_PROTOCOL.md 的主 session 侧执行版)。

## 前置检查
1. `python3 -m pytest -q` 确认基线全绿并记下数字;`git status --short` 确认工作树干净。
2. 读 specs/README.md 状态表确认下一个 spec(依赖 Ready);读 orbital/PROJECT_STATE.md 当前阶段。

## 派发 brief 必含要素
- repo 绝对路径 + 项目一句话背景 + 当前基线测试数与最近 commit。
- 必读清单(按序):AGENTS.md → orbital/ 三记忆文件(点出与该 spec 相关的 D 条目)→ EXECUTION_PROTOCOL + spec 文件 → 上游 spec 的 Completion Record → 相关现有模块。
- 硬约束:只做该 spec;复用 src/orbital_team/ 既有 storage/状态机,禁止第二套写路径;绝不 git commit/push、不碰 .git;git 只读命令加 `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null`;测试禁 ProcessPoolExecutor;不加新依赖;要改冻结契约先报 BLOCKED;沙箱做不到的外部 smoke 如实记 limitation 不伪造。
- 用量守则:额度不足时优先实现+测试+全绿,handoff 文档按序尽量推进。
- 要求:发总结前先 `git status` 核对,汇报必须与工作树一致。

## 主 session 复测(不信任子 agent 汇报,信任工作树)
1. 全量 `python3 -m pytest -q`,数字必须真实增长且全绿。
2. 抽查契约红线:stub 模块无网络 import;actor/权限负向测试存在;specs/README 状态与实际一致;Completion Record 数字与实测一致。
3. 工作树即真相:子 agent 总结可能早于文件落盘(出现过两次误报),也可能用量中断在写文件后——先看树再定性,勿因"失败/夸大"汇报直接回退。

## checkpoint(每 spec 两笔)
- feat: `git add src/ tests/ demo/ docs/ skills/ specs/ pyproject.toml` + `feat(spec-NN): <一句话>`(用实际改动的目录)。
- chore: `git add orbital/` + `chore: update project memory after SPEC-NN checkpoint`。

## 记忆维护
- PROJECT_STATE 当前阶段:替换为本 spec 完成事实 + commit hash + 下一个 spec 派发去向。
- INDEX.md:新文件各一行(只做导航,不写状态);新决定进 DECISIONS.md,新坑进 LESSONS.md。

## 编排者故障切换
claude-code(org 禁用)→ codex(用量重置后可用)→ cursor(需付费)→ dsh / gemini-cli(未验证)。切换时给全新会话的 brief 必须完全自带上下文;codex 线程可延续(带自身 SPEC 上下文)。
