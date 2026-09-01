---
id: SPEC-03
title: Member Skill & Agent Adapters
status: Done
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

- Final status: Done
- Outcome achieved: 交付 agent-neutral `orbital-team-member` Skill、确定性 `/team` parser/dispatcher、Claude Code 项目级 command + bounded SessionStart hook、显式 copy/link/uninstall installer，以及共享 schema-valid member Run 记录。所有 mutation 仍调用现有 `teamctl`/`MemberWorkflow`；adapter 拒绝 `--member`/`--actor`/`--workspace` 冒充，SessionStart 只读取 binding/Task/Question 并记录 run/seen event，绝不 claim。
- Files changed: 新增 `src/orbital_team/member_adapter.py`、`skills/orbital-team-member/`（Skill metadata、installer、Claude command/hook assets）、`tests/test_member_adapters.py`；扩展 `member_workflow.py` 的 read-only worktree binding summary、`storage.py` 的共享 `RunRecordStore`、`pyproject.toml` wheel data，以及本 spec/index/handoff memory。
- Verification run: `python3 -m pytest -q tests/test_member_adapters.py`；`python3 -m pytest -q`；`python3 -m compileall -q src tests skills/orbital-team-member`；skill-creator `quick_validate.py skills/orbital-team-member`；`PYTHONPATH=src python3 -m orbital_team.member_adapter --help`；临时目录中执行 Claude copy install/uninstall、generic link install/uninstall 与 provider JSON hook entrypoint；`python3 -m pip wheel --no-deps --no-build-isolation` 并检查 wheel payload；`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git diff --check`。
- Verification result: SPEC-03 专项 11/11、全量 81/81 通过（基线 70，真实新增 11）；带空格 query、report/block/status/questions/manager grammar 均映射为无 shell argv；真实临时 worktree fallback claim/start/report 的 actor 为 binding 对应的 `member:alice`，Bob worktree 与显式身份参数均无法冒充；跳过 start 的 Report 仍由 SPEC-02 状态机拒绝。重复 SessionStart 只有一个 Run/started event、Task 无变化、summary ≤4096 bytes、私有 log 为 0600；Claude/generic 安装均可回滚且保留既有 settings。Wheel 包含 module、Skill、metadata、installer 与 assets。
- Deviations from spec: 无冻结命令、身份、schema、依赖或状态机偏离。未改全局 agent 配置；只有显式 installer 动作写目标项目配置。Manager Skill/runner、Dashboard 与其他 provider 的完整原生 adapter 均未进入本 spec。
- Decisions recorded: 无新增产品决定；实现遵循 D11、D14、D15。
- Lessons recorded: 无新增 durable gotcha；沿用沙箱 ProcessPool、pytest EPERM、外部 runner 限制等既有 workaround。
- Known limitations: 当前环境无 Claude CLI，无法启动真实 Claude session 验证 UI 中的 `/team` discovery；Codex 嵌套 app-server 仍受 EPERM，故使用 injected/真实 subprocess fallback 与模拟 Claude Hook JSON 验证适配语义。Claude command/settings frontmatter 未由 Claude CLI 本体校验。Provider 未给 transcript path 时 Run 明确保存 `transcript=null`；member last-seen 由幂等 `run.seen` lifecycle event 表示。
- Working tree / commit: 实现、测试和 handoff 完成并保持未提交；按用户硬约束未 commit/push、未写 `.git`。起始 checkpoint 为用户提供的 SPEC-05 实现层 `ed5c52e` 与记忆层 `4e50161`。
- Next spec readiness: SPEC-03 已 Done；SPEC-08 仍等待 SPEC-06 与 SPEC-07，保持 Planned。下一项为 SPEC-06，完成后 SPEC-07 可转 Ready。
