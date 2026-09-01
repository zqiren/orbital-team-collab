---
id: SPEC-08
title: Demo Fixture & Multi-agent Orchestration
status: Done
depends_on: [SPEC-03, SPEC-05, SPEC-06, SPEC-07]
unlocks: [SPEC-09]
---

# Outcome

把已实现能力组装为可重复、不会污染交付 repo 的单机多 agent 演示：一个任意类型 Manager、两个成员 worktree、两个独立任务、一次 IM fixture ingest，以及完整代码/进度/知识闭环。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-03、SPEC-05、SPEC-06、SPEC-07 Completion Records
- `docs/20-prd.md`
- `docs/21-architecture.md`

# Starting State

- headless CLI、Skills、event-driven Manager、knowledge compilation、IM stub、dashboard 均可独立运行。
- 当前提交 repo 不应被 demo 运行态修改。

# Frozen Decisions

- demo runtime 与 canonical demo workspace 从版本化 fixture 初始化到临时目录。
- demo 只配置一个 logical project，但命令保留 project name。
- 两个成员任务修改不同主要文件，降低主演示的偶发冲突。
- Manager agent 类型通过 runner config 选择。
- 成员上报后自动触发 Manager merge 和 knowledge compilation。

# In Scope

- sample app/fixture 与清晰可见的初始状态。
- 一个 Manager、Alice/Bob 成员、两个 Ready Tasks。
- 至少一段 fixture IM，生成 Potential Task/Open Question。
- setup/start/status/reset/demo doctor 脚本。
- 临时 Git repo、branches/worktrees、runtime、Skill 安装。
- dashboard 启动与 URL 输出。
- runner 选择/缺失依赖提示。
- live demo scenario 和 deterministic replay/fallback（仅重放事件与 UI，不冒充 live agent success）。
- 多次运行清理和隔离测试。

# Out of Scope

- 真实 IM、远程 Git、云部署。
- 要求评审者购买特定 agent；至少允许配置其已有 CLI。
- 在主演示中故意制造复杂 merge conflict。
- 自动上传或发送任何外部内容。

# Demo Story

1. setup 创建临时 canonical project 与两个 worktree。
2. dashboard 展示两个 Ready Tasks、一个 Manager 和初始 knowledge。
3. fixture ingest 产生 Potential Task/Open Question，Manager/用户 triage。
4. Alice `/team claim <name> <task>` 原子认领，`/team start <task>` 后工作。
5. Bob 看到 Alice 的任务不可认领，选择第二项。
6. 两人提交 commit/report。
7. teamd 自动串行启动 Manager Runs。
8. Manager 验证、merge、编译 knowledge。
9. dashboard 展示 Done、活动流和 PROJECT_STATE/LESSONS 变化。
10. 新成员 context 能读取合并后的最新状态。

# Safety and Repeatability

- 临时目录通过安全创建机制生成，脚本打印精确路径。
- reset/cleanup 只作用于带 demo marker 的精确临时目录。
- 不使用 repo root、`$HOME`、`~` 或宽泛 glob 作为删除目标。
- 缺少 agent CLI 时 doctor 明确报告，并允许选择其他 runner 或 replay。
- replay 必须标注模拟，不替代 live acceptance。

# Acceptance Criteria

- 从干净 clone/副本运行 setup 不需要 Orbital。
- 创建的 manager/member workspaces 指向同一 runtime。
- 两成员并行 claim/report，Manager 自动顺序处理。
- 代码、Task 和 knowledge 三层 merge 均可观察。
- fixture IM 只进入 Potential Tasks/Open Questions，未自动 claim。
- demo 可连续运行两次且第二次从干净 seed 开始。
- 交付 repo 在 demo 前后除明确输出外不被修改。

# Verification

- setup/doctor/reset integration tests。
- 临时目录 E2E，至少一次 fake runner 稳定回归。
- 至少一次真实 Manager/Member agent live rehearsal；记录实际 agent 与结果。
- 两次连续运行、runner missing、member crash、manager retry 场景。
- 检查 repo status/文件哈希未被 demo 污染。

# Deliverables

- `demo/seed/`、sample app、safe fixtures。
- orchestration/setup/doctor/reset scripts。
- live scenario 与 replay fixture。
- E2E tests。

# Handoff Checklist

- Completion Record 记录实际 live rehearsal 和精确运行命令。
- SPEC-08 Done；SPEC-09 Ready。
- 更新 PROJECT_STATE、INDEX、DECISIONS/LESSONS。

## Completion Record

- Final status: Done
- Outcome achieved: 交付完全离线、可重置的 Apollo 演示组装层。`doctor/setup/start/status/reset/replay` 从版本化 seed/sample/IM fixture 创建临时 canonical Git repo 与 Alice/Bob linked worktree，调用现有 Member Skill installer 与 worktree-bound `MemberWorkflow`；两个 `subprocess.Popen` 成员在文件 barrier 后并行 claim/start/commit/report，`teamd` 使用扩展到 integration/knowledge 两 phase 的 builtin Manager 串行完成受控代码 merge、Knowledge Proposal、独立 knowledge commit、Task/Job Done 与 `integration.completed`，最后由既有 Dashboard projection 观察。Potential Task/Open Question 始终与两个 Confirmed Tasks 分离，Promote 只生成 Draft。reset 同时验证 D14 runtime marker 与绑定精确 resolved temp root 的私有 marker，连续两次从 clean seed 重放通过；replay 强制标记 `simulated-replay` / `live_success=false`。
- Files changed: 新增 `src/orbital_team/demo_orchestration.py`、`demo/scripts/team_demo.py`、`demo/sample-app/`、`demo/im-fixtures/demo-messages.json`、`demo/replay/dashboard.json`、`tests/test_demo_orchestration.py`、`docs/37-demo-fixture-and-orchestration.md`、`orbital/PROJECT_STATE_ARCHIVE.md`；更新 `src/orbital_team/manager_proc.py`、`demo/runners/builtin.json`、`demo/seed/{seed.json,tasks.json,README.md}`、Spec Index、本 spec 与 Orbital state/index。
- Verification run: `python3 demo/scripts/team_demo.py doctor`；临时根 smoke：`python3 demo/scripts/team_demo.py setup --root <mktemp-path>` → `start` → `status` → `reset`；`python3 -m pytest -q tests/test_demo_orchestration.py`；`python3 -m pytest -q`。
- Verification result: doctor 报 builtin integration/knowledge 可用；实际 smoke 产生 2 reports、2 Done Integration Jobs、2 knowledge summaries、2 `integration.completed`，随后精确 temp root cleanup；SPEC-08 专项 7 passed in 27.29s；全量 107 passed in 111.94s（基线 100，新增 7）。
- Deviations from spec: 当前 sandbox 未完成真实 Claude/Codex 外部 agent live rehearsal：过去已验证 nested Codex provider 初始化 EPERM，且本轮不把 CLI 存在或 deterministic builtin 冒充外部 LLM agent；该项明确留 SPEC-09 在普通 provider 环境复测。Dashboard 因 sandbox 禁止 loopback `socket.bind` 未做真实 browser/socket rehearsal，本轮使用同一 `DashboardProjection` 并输出可在普通本机执行的精确 loopback argv/URL。其余 In/Out of Scope 无偏离。
- Decisions recorded: 无新冻结产品决定；沿用 D12/D13/D14/D15。builtin knowledge phase 仍只调用 SPEC-05 受控 Proposal/apply 边界，不改变冻结契约。
- Lessons recorded: 无新增通用坑；测试直接应用既有 `sandbox-processpool-semaphore`（Popen + barrier）、`sandbox-loopback-listen-eperm` 与 `manager-runner-process-tree-timeout` playbook。
- Known limitations: builtin 是稳定的真实 subprocess/domain/Git pipeline，但其知识编译策略为确定性 PROJECT_STATE entry，不等同外部 LLM 判断；外部 runner 依赖对应本地 CLI/provider；reset 成功后删除的精确临时根不可恢复；sample app 与 IM 均为 synthetic fixture；未接真实 IM、remote Git、网络服务或 push。
- Working tree / commit: 按 session 硬约束未 commit/push、未手改交付 repo `.git`；全部实现与 handoff 留工作树供主 session 复测/checkpoint。
- Next spec readiness: SPEC-09 Ready；其 clean-clone/final delivery 阶段应补普通本机 Dashboard socket/browser 与真实外部 Manager/Member agent rehearsal，并收敛最终 README。
