---
id: SPEC-03
title: Member Skill & Agent Adapters
status: Planned
depends_on: [SPEC-02]
unlocks: [SPEC-08]
---

# Outcome

把 member CLI 封装为可复制、可由不同 agent 使用的协作能力；Claude Code 成员可用 `/team` 原生命令，其他 agent 可通过同一 Skill 协议或 CLI 获得等价行为。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-02 Completion Record
- `docs/22-protocol.md`

# Starting State

- `teamctl claim/report/block/status/questions` 已实现并验证。
- Context Pack 和稳定错误语义可用。

# Frozen Decisions

- `/team` 是产品级行为协议，不要求所有 agent 具备相同 UI 实现。
- Skill 教 agent 遵守协议；CLI 执行确定性状态变化。
- Hook 只负责加载/提醒，不负责认领、report 或 merge。
- demo 优先支持 Claude Code 成员窗口；Manager agent 类型不受此限制。

# In Scope

- `orbital-team-member` Skill 及必要 supporting references/scripts。
- Claude Code 项目级 Skill/Plugin adapter，暴露：
  - `/team claim <project-name> <task-id-or-query>`；
  - `/team start <task-id>`；
  - `/team report <task-id>`；
  - `/team block <task-id> ...`；
  - `/team status ...`；
  - `/team questions <project-name>`。
- SessionStart context summary hook；不得自动 claim。
- SessionStart 注册本地 member run；adapter 若能取得 provider session ID、transcript/log path 或 lifecycle event，则持续回写 runtime `runs/`，否则至少记录 actor、agent type、started/last-seen time 和 task/branch 关联。
- agent-neutral install/link mechanism。
- identity selection 与成员配置。
- Skill 触发、参数解析和失败提示测试。

# Out of Scope

- Manager Skill/runner。
- 为每一种 agent 编写完整 adapter。
- 修改 agent 全局配置而不经过显式安装动作。
- 将真实凭证写入 repo。

# Skill Contract

Skill 必须要求成员：

1. 先通过命令认领再工作；
2. 不直接修改 canonical project memory；
3. 不绕过 blocking questions；
4. 在独立 branch/worktree 工作；
5. 运行验证并 commit；
6. 用 Report 提交 summary、validation、knowledge candidates 和 risks；
7. 非法/歧义状态先反馈，不擅自修改 runtime JSON。

# Adapter Requirements

- adapter 将用户输入稳定转换到 `teamctl`，不得复制状态机逻辑。
- SessionStart 输出只含项目摘要、身份、当前领取任务、待回答问题和入口提示，并有严格长度上限。
- run/session 记录只写用户私有的 local runtime，不提交 Git；adapter 不得伪造 provider 未暴露的完整 transcript。
- 安装脚本支持从交付 repo 内的 canonical skill 位置创建复制或链接；行为明确可回滚。
- agent 不支持 slash 时，文档给出自然语言和 CLI 等价入口。

# Acceptance Criteria

- 新 Claude Code session 能发现 `/team`。
- `/team claim Apollo apollo-T-0001` 调用已有原子 claim，不是仅生成提示文本。
- SessionStart 能显示最新 project/member 摘要但不改变 Task。
- Team Dashboard 能看到 member run 的基础状态；支持的 adapter 还能打开其本地 transcript/log，未支持时明确显示 unavailable。
- start/report 命令能完成 SPEC-02 的同一状态转换，并拒绝跳过 start 的 Report。
- Skill 中没有将 Manager 固定为 Codex 或其他 agent。
- 不安装 Skill 时 CLI 仍可独立工作。

# Verification

- Skill schema/metadata validation。
- 在临时项目安装 adapter 并启动/模拟 Claude hook input。
- 参数解析测试：精确 ID、带空格 query、report/block/status/questions。
- 检查 Hook 重复执行幂等且不 claim。
- 使用至少一种非 Claude 路径验证 CLI fallback 文档成立。

# Deliverables

- `skills/orbital-team-member/`。
- agent adapter/install files。
- Skill/Hook tests 或 fixture。
- 面向成员的最小使用说明（放在 Skill/reference 或主 README 指针，不创建重复文档）。

# Handoff Checklist

- Completion Record 记录已实际验证的 agent/version 与未覆盖平台。
- SPEC-03 Done；若其他依赖完成则更新 SPEC-08 readiness。
- 更新 INDEX、PROJECT_STATE、必要的 LESSONS。

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
