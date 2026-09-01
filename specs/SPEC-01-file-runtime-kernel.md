---
id: SPEC-01
title: File Runtime Kernel
status: Planned
depends_on: [SPEC-00]
unlocks: [SPEC-02, SPEC-06]
---

# Outcome

实现一个不依赖 Orbital 的共享文件 runtime：从任意 Git worktree 定位同一 common directory，安全初始化多项目数据，提供原子存储、文件锁、事件和幂等基础。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- `specs/SPEC-00-product-contract-and-architecture.md` Completion Record
- `docs/21-architecture.md`
- `docs/22-protocol.md`

# Starting State

- SPEC-00 为 Done。
- 当前目录已是 Git repo（2026-09-01 初始化）；runtime resolver 仍须支持在任意普通 Git repo 中工作。
- schema、目录与状态机已冻结。

Gate checks：确认 SPEC-00 deliverables 存在且术语一致。

# Frozen Decisions

- 根目录已于 2026-09-01 完成 `git init`（main 分支，remote `origin` 已配置，见 DECISIONS D10）；本阶段不得 push。
- runtime 位于 `git rev-parse --git-common-dir` 所指目录下的 `orbital-team/`。
- `demo/seed/` 是版本化初始化输入；runtime 本身不提交。
- storage library 是 CLI、teamd 和 dashboard 的唯一写入口。

# In Scope

- 初始化/检测 Git repo。
- shared runtime path resolver。
- project registry 与 project runtime 初始化。
- JSON 原子替换、JSONL append、锁、幂等记录。
- schema validation 与 typed models。
- `teamctl init`、`teamctl status`、`teamctl reset --runtime-only`。
- 并发和损坏恢复测试。

# Out of Scope

- Task 命令和业务状态转换。
- Agent Skill、Manager runner、dashboard、IM extraction。
- 删除工作代码或执行 destructive Git reset。

# Implementation Requirements

- 优先使用 repo 内可运行、依赖最少的实现；新增依赖必须在决定中说明。
- 写入采用 lock + temp file + atomic replace；不得原地截断 JSON。
- JSONL 事件必须单行、带 event ID、project slug、actor、timestamp、schema version。
- stale lock 行为明确且测试覆盖。
- 从 manager workspace 和两个 worktree 解析出的 runtime root 必须相同。
- `reset --runtime-only` 只删除精确解析出的 `orbital-team/` runtime，并要求显式确认参数或 demo marker；不得接受宽泛路径。

# Public Interfaces

```text
teamctl init --project <name> --workspace <path> [--seed <path>]
teamctl status [--project <name>]
teamctl reset --runtime-only --project <name>
```

storage 模块至少提供：registry、project store、event append/read、lock、idempotency guard。

# Acceptance Criteria

- 一个普通 repo 初始化后产生完整 runtime。
- 两个 Git worktree 读写同一个 project runtime。
- 并发写测试不会产生无效 JSON 或重复 event ID。
- 中断写入不会破坏最后一个有效状态。
- 重复 init 幂等且不覆盖已有数据。
- runtime 不进入 `git status` 的版本化文件列表。

# Verification

- 运行本 spec 新增的全部单元测试。
- 创建临时 Git repo 与两个 worktree，验证 path resolver。
- 并发执行事件 append 与同一 JSON store 更新。
- 在临时 repo 中测试 reset，验证 repo/工作文件未被删除。

# Deliverables

- runtime/storage 源码与测试。
- `teamctl` 最小入口。
- 初始 seed/schema 目录。
- 安装/运行依赖声明。

# Handoff Checklist

- 填写 Completion Record。
- SPEC-01 Done；SPEC-02 与 SPEC-06 Ready。
- 记录实际 runtime path、测试命令和平台限制。
- 更新 PROJECT_STATE、INDEX；非显而易见的锁/路径 gotcha 进入 LESSONS。

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
