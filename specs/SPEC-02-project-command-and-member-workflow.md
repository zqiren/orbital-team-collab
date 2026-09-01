---
id: SPEC-02
title: /team Command & Member Workflow
status: Done
depends_on: [SPEC-01]
unlocks: [SPEC-03, SPEC-04]
---

# Outcome

实现 agent-neutral 的成员工作协议：从项目和任务查询开始，原子认领、加载上下文、推进状态，并从 Git 工作成果生成结构化 Report。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-01 Completion Record
- `docs/22-protocol.md`

# Starting State

- runtime kernel、registry、locks、events 可用。
- 目标临时 repo 可创建至少两个 worktree。

# Frozen Decisions

- 唯一匹配时 `/team claim <project> <query>` 同时 claim 和返回 context。
- 多个匹配、无匹配、已被领取或存在 blocking question 时不得改变任务状态。
- 只有 Confirmed Task 的 Ready 状态可被领取。
- Report Submitted 后其他成员仍不可领取该任务。

# In Scope

- member identity/join。
- project/task resolve：ID 精确匹配优先，之后使用确定性标题/标签匹配；v1 不要求 embedding。
- claim/start/status/block/report。
- Task Context Pack 组装。
- Git branch、commit、changed files、diff summary、验证结果收集。
- Report schema 校验。
- 状态转换、事件和幂等测试。

# Out of Scope

- Slash command adapter/Hook。
- Manager integration 与自动 runner。
- IM extraction、dashboard。
- 自动替成员修改或提交代码。

# Public Commands

```text
teamctl member join --project <name> --member <id> --agent <type>
teamctl claim --project <project-name> <task-id-or-query>
teamctl task start <task-id>
teamctl task status [task-id]
teamctl task block <task-id> --reason <text>
teamctl report submit <task-id> [--summary ...] [--validation ...]
teamctl question list --project <project-name>
```

# Context Pack

返回内容至少包括：Task、acceptance criteria、关联路径、dependencies、相关项目状态/决定/lesson 指针、Open Questions、成员/branch 信息、Report 要求。设置明确大小预算；优先返回摘要与路径，不无界内联全部 memory。

# State and Concurrency Requirements

- claim 在 project lock 内完成 resolve recheck + state write + event append。
- member 必须是 project 成员。
- branch/commit 必须属于当前 Git repo。
- report actor 必须是当前 assignee。
- Task ID 使用 `<project-slug>-T-<sequence>`，跨 project 唯一。
- `Claimed → Submitted` 非法；report 前必须显式 start 进入 In Progress。
- 同一 commit/task 重复 report 返回原 report，不生成重复提交事件。
- block/report 的非法转换给出稳定错误码。

# Acceptance Criteria

- Alice/Bob 并发认领同一 Ready Task 只有一个成功。
- 唯一标题匹配能 claim；歧义查询返回候选且不 claim。
- blocking Open Question 阻止 claim，并返回关联问题。
- 成员能获得受大小限制的 Context Pack。
- report 自动包含可验证 Git metadata，并让 Task 进入 Submitted。
- 所有动作可在 events 中追溯。

# Verification

- 状态机单元测试。
- 两进程并发 claim 测试。
- 临时 Git repo/worktree report 集成测试。
- 重复命令幂等测试。
- 非 assignee、错误 commit、blocking question、歧义查询负向测试。

# Deliverables

- member/task/report command implementation。
- Context Pack builder。
- 状态机与测试 fixtures。
- CLI usage help。

# Handoff Checklist

- Completion Record 完整记录命令与错误语义。
- SPEC-02 Done；SPEC-03 和 SPEC-04 Ready。
- 更新 PROJECT_STATE、INDEX、必要的 DECISIONS/LESSONS。

## Completion Record

- Final status: Done
- Outcome achieved: 实现 agent-neutral 的 Member workflow 与 `teamctl` 命令：当前 worktree identity join、Project/Task deterministic resolve、Draft/Ready 创建校验、原子 claim + bounded Context Pack、start/status/block/questions、Git-bound immutable Report 与完整 event/idempotency 链路。
- Files changed: 新增 `src/orbital_team/member_workflow.py`、`tests/test_member_workflow.py`、`docs/32-member-workflow.md`；扩展 `cli.py`、`errors.py`、`paths.py`、`storage.py` 与 package export；更新本 spec、Spec Index 及 Orbital memory/index。
- Verification run: `PYTHONPATH=src GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null python3 -m unittest tests.test_member_workflow -v`；`python3 -m unittest discover -s tests -v`；`python3 -m compileall -q src tests`；`python3 -m pip wheel --no-deps --no-build-isolation ...` 后在临时 venv 安装并运行 `teamctl --help`/加载 schema bundle；CLI help、依赖 import、凭证/绝对路径扫描与 `git diff --check`。
- Verification result: SPEC-02 专项 26/26、全量 50/50 通过；两个独立 Python 进程经文件 barrier 同时 claim 同一 Ready Task，仅一个成功；歧义与 blocking question 均零副作用；`Claimed → Submitted`、非 assignee、错误 commit/branch 与 schema-invalid Report 均以稳定错误拒绝；Report 的 branch/base/commit/changed files/diff/validation 通过 schema 校验；相同 task/commit 只产生一个 Report/event；wheel 可安装且包含全部 48 个 `$defs`。
- Deviations from spec: 无产品契约、命令语法、schema、依赖或范围偏离；同时实现冻结协议已列出的 Human/Manager `task create`/`task ready`，为专项 fixture 与后继 spec 提供合法 Draft → Ready 入口。当前环境缺少可选 `build` module，clean wheel 验证改用现有 `pip wheel --no-deps --no-build-isolation`，未增加依赖。
- Decisions recorded: D15（CLI member actor 由 current worktree 的唯一 join binding 推导；join 固定 named branch/repo binding，后续 mutation 不接受可冒充的 member 参数）。
- Lessons recorded: Python 3.13 沙箱禁止查询 POSIX semaphore 上限，`ProcessPoolExecutor` 初始化会报 `PermissionError`；跨进程测试改用两个 `subprocess.Popen` + 文件 barrier。
- Known limitations: 本阶段只验证 macOS/POSIX 单机 Git worktree；member branch rename/rebind lifecycle 尚未实现；slash/Hook adapter、Manager integration、自动 runner、IM 与 Dashboard 分属后继 spec；Report 只收集调用方提供的 validation evidence，不自动执行任意项目命令。
- Working tree / commit: 主 session 复测全量 50/50 通过后，已将本 spec/Index 置为 Done/Ready，并以 `feat: implement /team member workflow (SPEC-02)` 创建单一 checkpoint（hash 见 git log）；不 push。
- Next spec readiness: SPEC-03 与 SPEC-04 已标 Ready，可在独立 session 冷启动执行；SPEC-06 保持 Ready。
