---
id: SPEC-05
title: Manager Knowledge Compilation
status: Done
depends_on: [SPEC-04]
unlocks: [SPEC-08]
---

# Outcome

在 integration 成功后，由同一条事件驱动 pipeline（正常路径可复用当前 run，恢复路径启动新的短生命周期 Manager Run）把成员报告和 merged diff 编译成受验证的 Knowledge Proposal，并安全更新 PROJECT_STATE、DECISIONS、LESSONS、INDEX。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-04 Completion Record
- `AGENTS.md` 的 memory write semantics
- `docs/22-protocol.md`

# Starting State

- `integration.merged`/Awaiting Knowledge 状态可用。
- ManagerRunner 可启动 agent 并返回结构化结果。
- canonical memory 文件存在。

# Frozen Decisions

- 语义判断由 Manager Agent + Manager Skill 完成。
- 确定性脚本负责 pack、proposal、validation、apply 和幂等。
- merge 失败不得 apply knowledge。
- 事实冲突或缺失决策创建 Open Question，不静默覆盖。
- 每份 proposal 只能 apply 一次。
- Awaiting Knowledge 不占用 integration slot；冲突问题回答后由 `knowledge.resume_requested` 恢复。

# In Scope

- `orbital-team-manager` Skill 的 knowledge rules。
- Knowledge Pack builder。
- Knowledge Proposal 格式与状态。
- proposal diff/patch 生成、验证、apply 和 allowlisted local knowledge commit。
- PROJECT_STATE/DECISIONS/LESSONS/INDEX 专属校验规则。
- v1 自动 apply allowlist 只包含上述四个文件；`orbital/instructions/` 可读但不可由 Manager 自动修改。
- integration → knowledge 事件链、retry 与 idempotency。
- knowledge change summary 给 dashboard。

# Out of Scope

- 通用 AI 记忆系统或向量数据库。
- 自动回答 Open Question。
- 无上限地内联历史 session/IM。
- 修改 machine-managed runtime、session、ledger、tool-results。

# Knowledge Classification Rules

- PROJECT_STATE：当前仍为真的项目事实、进行中工作、blocker、下一步；覆盖陈旧事实，不写流水日志。
- DECISIONS：已经落地且跨 session 有效的决定与理由；冲突时 supersede，不保留两份现行真相。
- LESSONS：可复用的非显而易见 gotcha/playbook；去重，保持完整性。
- INDEX：一行一路径的导航；不放状态、日期、决定或长摘要。
- 普通实现细节、临时调试、重复 report 不进入 canonical memory。

# Pipeline

```text
integration.merged
→ knowledge.prepare <report-id>
→ Knowledge Pack
→ Manager semantic compile
→ Knowledge Proposal patches + summary
→ knowledge.validate
→ knowledge.apply
→ knowledge.applied
→ Task Done / Job Done
```

apply 前记录原文件哈希；若文件已变化，proposal 进入 Stale/Blocked 并重新编译，不覆盖并发更新。

实际 memory apply/commit 复用 SPEC-04 的 git mutation lock；Runner 不能直接执行裸 `git commit`，只能提交结构化 Proposal 给受控 domain command。

知识冲突创建的 Open Question 必须关联 job/proposal；Task 保持 Integrating。`question.answered` 产生 `knowledge.resume_requested`，恢复 run 重新校验 proposal 基线并在必要时重编。成功 summary 使用 `docs/22-protocol.md` 冻结的 knowledge change summary schema。

# Acceptance Criteria

- 两个成员报告能收敛成不重复、不矛盾的 canonical memory。
- PROJECT_STATE 不退化为 session changelog。
- 重复 lesson 不会重复追加。
- 新资产能正确进入 INDEX，删除/移动反映准确。
- 输入与已有 DECISIONS 冲突时创建 Open Question 或显式 supersede。
- 文件在 proposal 后被修改会阻止旧 proposal apply。
- 成功 apply 后 Task 与 Integration Job 才最终进入 Done。
- knowledge change 只 stage allowlisted memory path 并生成独立本地 commit；no-change 不生成空 commit；绝不 remote push。
- knowledge change summary 可被 dashboard 读取。

# Verification

- 使用 deterministic fixtures 覆盖四类 memory 的正/负分类。
- 重复 report、冲突决定、stale proposal、重复 apply 测试。
- 使用实际 Manager Agent 对至少两份模拟报告做受控 smoke，并人工检查 diff。
- 检查未触碰 machine-managed runtime paths。

# Deliverables

- `skills/orbital-team-manager/`。
- pack/proposal/validate/apply commands。
- knowledge schema、fixtures 和测试。
- event/job extension。

# Handoff Checklist

- Completion Record 记录 agent smoke 的实际 diff 和已知语义限制。
- SPEC-05 Done；若 SPEC-03/06/07 均 Done 则 SPEC-08 Ready。
- 更新项目 memory 与 index；将真正的新编译 gotcha 写入 LESSONS。

## Completion Record

- Final status: Done
- Outcome achieved: 接通 SPEC-04 的 Awaiting Knowledge 边界：`teamd` 启动 phase-aware 短生命周期 Manager knowledge run，生成/校验 Knowledge Proposal，经 project + Git mutation lock 原子 apply 四个 allowlisted canonical memory 文件并创建独立本地 knowledge commit；no-change 不造空 commit；dirty/stale/conflict、Open Question resume、commit 后崩溃恢复、Task/Job Done 与 `integration.completed` 均通过共享 domain/storage 状态机闭环。
- Files changed: 新增 `src/orbital_team/knowledge_workflow.py`、`skills/orbital-team-manager/{SKILL.md,agents/openai.yaml}`、`tests/test_knowledge_workflow.py`、`docs/34-manager-knowledge-compilation.md`；扩展 `storage.py`、`manager_runner.py`、`teamd.py`、`cli.py`、`__init__.py`、`pyproject.toml`、三个 `demo/runners/*.json` manifest，以及本 spec/index/handoff memory。
- Verification run: `python3 -m pytest -q tests/test_knowledge_workflow.py`；`python3 -m pytest -q`；`python3 -m compileall -q src tests`；`PYTHONPATH=src python3 -m orbital_team manager knowledge --help`；skill-creator `quick_validate.py skills/orbital-team-manager`；`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git diff --check`；本机 Codex 0.144.5 真实启动探测（45 秒硬上限）。
- Verification result: SPEC-05 专项 8/8、全量 70/70 通过（基线 62，真实新增 8）；临时 Git fixture 验证只 stage allowlist、knowledge commit 的唯一 parent 为 source merge commit、no-change HEAD 不变、dirty Blocked、stale 拒绝覆盖、重复 apply 仅一个 commit/summary/completed event、commit 后 finalize 崩溃可重入，以及 injected knowledge-only runner 端到端只执行一次。Skill 校验和 compileall/diff-check 通过。
- Deviations from spec: 无产品契约、schema、依赖或范围偏离。实际外部 Manager Agent 双 Report semantic smoke 未完成：Codex CLI 存在但嵌套 sandbox 在 in-process app-server 初始化阶段返回 EPERM；Claude CLI 不可用。未把 deterministic runner 冒充外部 agent smoke。
- Decisions recorded: 无新增产品决定；实现遵循 D11–D15，尤其 D13 的独立 commit/no-change/dirty workspace/controlled Git 边界。
- Lessons recorded: Knowledge Change Summary 的冻结 identity 字段是 `summary_id` 而非通用对象的 `id`；共享 immutable store 必须显式配置 schema identity field，不能绕开 storage 层手写 JSON。
- Known limitations: 外部 agent 的跨两份 Report 语义去重与冲突判断受当前 provider sandbox/CLI 环境阻塞；确定性 domain、Git、恢复与 teamd fixtures 已覆盖，Skill 明确定义 PROJECT_STATE/DECISIONS/LESSONS/INDEX 分类规则。非 POSIX runner 进程树终止仍沿用 SPEC-04 的直接进程 fallback，未在本 session 实测。
- Working tree / commit: 实现、测试和 handoff 完成并保持未提交；按用户硬约束未 commit/push、未写 `.git`。起始 checkpoint 为用户提供的 `6e30a89`（实现层）与 `fae75d7`（记忆层）。
- Next spec readiness: SPEC-05 已 Done；SPEC-08 仍等待 SPEC-03、SPEC-06、SPEC-07，因此保持 Planned。下一执行顺序为 SPEC-03 → SPEC-06 → SPEC-07。
