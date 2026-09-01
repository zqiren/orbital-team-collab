---
id: SPEC-01
title: File Runtime Kernel
status: Done
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
- runtime 根目录和新建的敏感 run/session log 文件默认仅当前 OS 用户可读写；不得依赖进程 umask 恰好安全。
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
- 权限测试确认其他 OS 用户默认不可读取 runtime/log 文件（平台不支持 POSIX mode 时明确记录等价边界）。

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

- Final status: Done
- Outcome achieved: 实现自包含 Python file runtime kernel：Git common-dir resolver、多 project registry/runtime 初始化、Draft 2020-12 schema validation、typed models、私有权限、跨进程锁、revisioned atomic JSON store、去重 JSONL event log、可恢复幂等 operation journal，以及 `teamctl init/status/reset --runtime-only`。
- Files changed: 新增 `pyproject.toml`、`src/orbital_team/`、`tests/test_runtime_kernel.py`、`demo/seed/`、`docs/31-file-runtime-kernel.md`；更新 `.gitignore`、Spec Index、本 spec 与 Orbital memory/index。
- Verification run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`；单独复跑 13 项 worktree/concurrency/interruption/lock/idempotency/reset/permission/git-status 高风险矩阵；构建并在临时 venv 安装 wheel；校验 4 个 seed store；`compileall`、依赖 import 审计、凭证/绝对路径扫描、`git diff --check`。
- Verification result: 完整测试 24/24 通过，高风险矩阵 13/13 通过；临时 repo 的 manager workspace + 两个 linked worktree 解析和读写同一 runtime；40 个唯一 event + 8 路同 event 并发只落一份，40 次同 store 更新得到 revision 40；中断 replace 保留旧 JSON；reset 保留 repo/工作文件；POSIX `0700/0600` 通过；wheel 内含并可加载全部 48 个 `$defs`，seed 4/4 有效。
- Deviations from spec: 实现与验证无范围或冻结契约偏离；为落实协议 §17，非 demo reset 使用附加安全参数 `--yes`，带版本化 demo marker 的 runtime 可使用公开接口原形。唯一未完成项是当前沙箱拒绝创建 `.git/index.lock`，无法创建获授权的 checkpoint commit。
- Decisions recorded: D14（`src/orbital_team` 单 package、schema wheel data、runtime/seed safety marker 与下游共享 storage API）。
- Lessons recorded: filelock stale 文件不等于持锁、common-dir reset 的精确路径校验，以及 `$defs` fragment 不得继承 schema bundle 顶层 `oneOf`。
- Known limitations: 实际权限/删除锁验证平台为 macOS POSIX；非 POSIX 只保留 best-effort 私有创建并未在本 session 实测；原型 event 去重读取全量 JSONL，超大日志索引/compaction 留给后续生产化。
- Working tree / commit: 主 session 复测 24/24 通过后，已将本 spec/Index 置为 Done/Ready，并以 `feat: implement file runtime kernel (SPEC-01)` 创建单一 checkpoint（hash 见 git log）；不 push。
- Next spec readiness: SPEC-02 与 SPEC-06 已标 Ready，可在独立 session 冷启动执行。
