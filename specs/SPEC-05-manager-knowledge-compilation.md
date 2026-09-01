---
id: SPEC-05
title: Manager Knowledge Compilation
status: Planned
depends_on: [SPEC-04]
unlocks: [SPEC-08]
---

# Outcome

在 integration 成功后，由同一个事件驱动 Manager Run 把成员报告和 merged diff 编译成受验证的 Knowledge Proposal，并安全更新 PROJECT_STATE、DECISIONS、LESSONS、INDEX。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-04 Completion Record
- `AGENTS.md` 的 memory write semantics
- `docs/22-protocol.md`

# Starting State

- `integration.completed`/Awaiting Knowledge 状态可用。
- ManagerRunner 可启动 agent 并返回结构化结果。
- canonical memory 文件存在。

# Frozen Decisions

- 语义判断由 Manager Agent + Manager Skill 完成。
- 确定性脚本负责 pack、proposal、validation、apply 和幂等。
- merge 失败不得 apply knowledge。
- 事实冲突或缺失决策创建 Open Question，不静默覆盖。
- 每份 proposal 只能 apply 一次。

# In Scope

- `orbital-team-manager` Skill 的 knowledge rules。
- Knowledge Pack builder。
- Knowledge Proposal 格式与状态。
- proposal diff/patch 生成、验证和 apply。
- PROJECT_STATE/DECISIONS/LESSONS/INDEX 专属校验规则。
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
integration.completed
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

# Acceptance Criteria

- 两个成员报告能收敛成不重复、不矛盾的 canonical memory。
- PROJECT_STATE 不退化为 session changelog。
- 重复 lesson 不会重复追加。
- 新资产能正确进入 INDEX，删除/移动反映准确。
- 输入与已有 DECISIONS 冲突时创建 Open Question 或显式 supersede。
- 文件在 proposal 后被修改会阻止旧 proposal apply。
- 成功 apply 后 Task 与 Integration Job 才最终进入 Done。
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
