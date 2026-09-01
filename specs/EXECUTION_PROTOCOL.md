# Spec Execution Protocol

本协议适用于 `specs/` 下每个实现 session。目标是让任何新 agent 在没有聊天历史的情况下安全接手，并给下一个 session 留下可验证的起点。

## 1. Session Start

1. 按 `specs/README.md` 的执行入口顺序读取上下文。
2. 检查目标 spec 状态必须为 `Ready`；否则停止并说明未满足的依赖。
3. 运行目标 spec `Starting State` 中的 gate checks。
4. 检查工作树和现有文件；用户已有改动不得覆盖、回滚或顺手整理。
5. 将目标 spec 与 `specs/README.md` 中的状态改为 `In Progress`。
6. 若发现会改变产品契约、公开接口、依赖范围或安全边界的 open design，先向用户对齐。

## 2. Execution Rules

- 一个 session 只执行一个目标 spec。
- 严守 `In Scope` / `Out of Scope`；不得提前实现后续 spec。
- 复用前序 spec 的公开接口，不在下游 session 静默改写。
- 文件 runtime 是事实来源；缓存、UI 和 agent 输出不得成为隐藏状态。
- 所有状态变化必须通过共享 storage/command 层，禁止多个调用方各自手写 JSON。
- 对任务认领、report 消费、integration job 和 knowledge apply 使用幂等键。
- 测试优先覆盖状态机、并发、失败恢复和路径隔离。
- 如果为了完成当前 spec 必须修改前序契约，停止执行，提出变更与受影响 spec 列表。

## 3. Verification Gate

标记 `Done` 前必须：

1. 逐条核对 Acceptance Criteria。
2. 实际运行 Verification 中的命令；不得只写“应当通过”。
3. 检查没有临时凭证、真实 IM 数据、session transcript、ledger 或绝对用户路径进入交付文件。
4. 检查从干净输入或 fixture 可以复现本 spec 的结果。
5. 记录未覆盖平台、已知限制和任何偏离。

## 4. Session Handoff

结束 session 前，按顺序完成：

1. 填写当前 spec 的 `Completion Record`。
2. 更新 `specs/README.md` 状态与被解锁的后继 spec。
3. 更新 `orbital/PROJECT_STATE.md`：当前完成阶段、下一步、真实 blocker。
4. 在 `orbital/DECISIONS.md` 记录跨 session 仍有效的新决定；不得记录普通实现细节。
5. 在 `orbital/LESSONS.md` 记录非显而易见的失败恢复或 gotcha。
6. 在 `orbital/INDEX.md` 登记新增的持久路径。
7. 记录工作树状态；若用户已授权 checkpoint commit，则每个完成 spec 对应一个本地 commit。

## 5. Completion Record Template

每份 spec 尾部保留以下字段，由执行 session 填写，不删除原始验收要求：

```markdown
## Completion Record

- Final status: —
- Outcome achieved:
- Files changed:
- Verification run:
- Verification result:
- Deviations from spec:
- Decisions recorded:
- Lessons recorded:
- Known limitations:
- Working tree / commit:
- Next spec readiness:
```

执行前 `Final status` 保持 `—`；结束时只允许填写 `Done` 或 `Blocked`。仍在执行时保持 spec frontmatter 的 `In Progress`，不伪造完成记录。

## 6. Blocking Policy

以下情况才算需要用户对齐：

- 角色权限或自动化边界变化；
- 文件 schema 或命令语法变化；
- 新增外部服务、真实账号或网络依赖；
- 需要破坏性操作或远程写入；
- 需求与冻结原则冲突；
- 两个可行方案会产生明显不同的产品体验。

普通代码组织、函数命名和局部测试实现由执行者自行判断。
