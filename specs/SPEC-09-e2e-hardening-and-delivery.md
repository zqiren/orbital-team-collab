---
id: SPEC-09
title: End-to-end Hardening & Delivery
status: Done
depends_on: [SPEC-08]
unlocks: []
---

# Outcome

从 Kimi 评审者视角完成 clean-clone 验证、跨模块修复、产品文档收敛和 repo 整理，使单个 repo 能在不安装 Orbital 的情况下被理解、运行和评审。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- 所有前序 Completion Records，重点 SPEC-08
- `docs/00-assignment-brief.md`
- `docs/20-prd.md`
- `docs/21-architecture.md`
- `docs/22-protocol.md`

# Starting State

- SPEC-08 E2E live scenario 已至少成功一次。
- 所有核心能力均已实现；本 spec 不再扩张产品范围。

# Frozen Decisions

- 最终 repo 自包含且不依赖 Orbital runtime/API。
- README 先讲产品差异和 demo，再链接深层研究。
- replay 必须明确标注，不能替代 live proof。
- 不提交真实 runtime、凭证、IM、agent transcripts 或用户路径；这些运行数据可留在本地 runtime 供 Dashboard 查看。

# In Scope

- clean clone/install/setup/run 全链路验证。
- 修复前序集成缺陷和文档不一致。
- 根 README 电梯陈述、架构图、quick start、demo script、限制。
- PRD/roadmap 与实现状态对照。
- 竞品/场景文档导航收敛。
- 截图、短 GIF 或录屏脚本/素材（按可行环境）。
- repo ignore、license/attribution、依赖锁定、命令帮助。
- 安全/隐私扫描与最终测试矩阵。
- 标记所有 specs Completion/最终状态。

# Out of Scope

- 新增未在 SPEC-00 冻结的旗舰功能。
- 真实 IM connector、远程服务、SSO、预算、审批。
- GitHub checkpoint push 按 DECISIONS D10 的 standing authorization 执行；发送给 Kimi 仍需用户另行明确授权。
- 隐藏失败测试或用 replay 冒充 live run。

# Reviewer Journey

README 必须让评审者在以下层级获得信息：

1. 30 秒：问题、Orbital 差异、Team Workspace 一句话。
2. 2 分钟：Manager/Member、文件协议、事件闭环图。
3. 5 分钟：安装前置、setup、dashboard、agent windows、demo script。
4. 深入：PRD、architecture、protocol、spec history、竞品证据。

# Acceptance Criteria

- 在全新目录 clone/copy 后，按 README 命令可以完成 setup 和 dashboard 启动。
- 在具备至少一个受支持 Manager runner 和成员 agent 的环境中可完成 live flow。
- 缺少 agent 时 doctor 给出准确替代/安装提示，replay 可展示 UI 但标注模拟。
- README、PRD、architecture、protocol 与实际命令/schema 一致。
- 所有自动测试、build、lint 和安全检查通过，或有明确非伪装限制。
- repo 不包含 runtime、凭证、真实 IM、session/ledger/tool output 或绝对用户路径。
- Kimi 不需要下载 Orbital 即可评审。

# Verification

- 使用临时 clean copy 执行 README 全部命令。
- 运行完整测试矩阵、frontend build/lint、CLI help/smoke。
- live rehearsal + replay rehearsal。
- `rg` 扫描绝对路径、token/key pattern、Orbital API 依赖和过时命令。
- 核对每份 spec Completion Record 和 Index 状态。

# Deliverables

- 根 `README.md`。
- 最终校准 `docs/20-prd.md`、`docs/21-architecture.md`、`docs/22-protocol.md`、`docs/30-roadmap.md`。
- screenshots/recording assets 或可复现 capture instructions。
- 整理后的 repo ignore/dependency/license files。
- 最终测试与限制说明。

# Handoff Checklist

- Completion Record 填写最终 clean-run 证据。
- SPEC-09 Done，所有 spec index 状态准确。
- PROJECT_STATE 标记交付准备状态与任何仍需用户执行的外部动作。
- INDEX 完整，DECISIONS/LESSONS 无矛盾。
- 按 DECISIONS D10 commit/push；不得未经单独授权 send 给 Kimi/其他外部对象。

## Completion Record

- Final status: Done
- Outcome achieved: 从 Kimi 评审者视角完成根 README 电梯陈述、两层文件模型/事件图、可执行 quickstart、文档导航、限制与许可说明；新增 disposable clean-copy verifier，在全新临时 Git repo + 隔离 venv 中执行 editable install、完整 tests、CLI help、builtin 双成员 live-scripted demo、status/replay/reset、Dashboard bind 探测、source fingerprint 与 clean status；收敛全部 spec 状态、最终验证/录制指南、ignore 与隐私/凭证/绝对路径扫描。
- Files changed: 新增 `README.md`、`THIRD_PARTY_NOTICES.md`、`docs/38-final-verification.md`、`scripts/{__init__.py,verify_clean_copy.py}`、`tests/test_delivery_contract.py`；更新 `.gitignore`、`docs/{00-assignment-brief.md,20-prd.md,21-architecture.md,22-protocol.md,30-roadmap.md,37-demo-fixture-and-orchestration.md}`、Spec Index/本 spec，以及 Orbital state/index；从版本化 memory 文档中移除本机绝对路径与个人 email。
- Verification run: 收尾 session 实测：`python3 -m pytest -q`（根工作树全量）；`python3 -m pytest -q tests/test_delivery_contract.py`；`python3 scripts/verify_clean_copy.py --dashboard-policy allow`；真实 loopback HTTP smoke（`create_dashboard_server` + `urllib` 请求 `/` 与 `/api/bootstrap`，随后 demo reset）；README/docs/specs 全量相对链接检查；`rg` 扫描用户绝对路径、用户名、email 与 secret/token/key 模式；`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git status/diff/check-ignore` 审计。
- Verification result: 接手基线为 `1 failed, 111 passed`（失败源：交付扫描测试误扫 `.gitignore` 已排除的机器管理 runtime——`orbital/output/` 与新编排器写入 `orbital/sub_agents/dsh/` 的 `.yml`/session 文件；修复扫描/copy/gitignore 三处共同的排除边界，未弱化断言）。修复后根工作树全量 `112 passed in 111.55s`；clean-copy verifier `ok:true`：copy 内 `112 passed in 111.81s`，builtin demo 40 events、2 个 Done Integration Jobs、2 份 knowledge summaries、IM Promote Task 保持 Draft，replay 明确 simulated，reset 后 copy `git status` 干净且 source fingerprint 未变化。本 session loopback bind 真实成功（随机端口）并完成真实 socket 上的 `GET /`（200，4157 bytes）与 `GET /api/bootstrap`（200，actor 绑定 JSON）；交付树 0 死链，无用户路径/用户名/email/secret 命中。
- Deviations from spec: 首轮执行者（dsh）中途终止，其自报「112/112」在当时不实（实测 1 failed/111 passed）；本 record 由收尾 session 以独立实测重写。默认 builtin runner 是真实 subprocess/worktree/受控 Git/domain 闭环的 live-scripted Manager，明确不是 external LLM agent；external Codex/Claude Code rehearsal 未完成，如实记为 limitation。先前记录的 loopback bind EPERM 在收尾环境未复现，bind+HTTP smoke 真实通过；浏览器级可视化 walkthrough 仍留普通本机。无 Node frontend build，静态 HTML/CSS/ES modules 以 package data + 测试/安全扫描交付。
- Decisions recorded: 无新增冻结产品决定；D10 补记 `orbital/sub_agents/*/` 白名单（只版本化 MEMORY.md，其余 harness runtime 一律忽略）。根 repo 未声明开源许可证、不推断使用授权，第三方 attribution 见 `THIRD_PARTY_NOTICES.md`。
- Lessons recorded: delivery-scan-runtime-allowlist——交付边界三处（`.gitignore`、delivery 扫描测试、clean-copy `_ignored`）必须表达同一份机器 runtime 清单；sub_agents 用 MEMORY.md 白名单而非枚举扩展名；此类失败先判定命中文件是否属于交付集，修排除范围而非弱化断言。
- Known limitations: v1 仍为单机/POSIX 信任边界；external Codex/Claude Code live rehearsal 与浏览器级可视化 walkthrough 需在具备登录 agent CLI/浏览器的普通本机复测；非 POSIX 权限与 runner 进程树未实测；没有真实 IM、remote Git 同步、Team Cloud、SSO/RBAC、Approval/Budget；README 的 clone URL 在用户 push origin 前尚不可用；本作业 repo 未声明开源许可证。
- Working tree / commit: 全部 SPEC-09 改动（dsh 产出 + 收尾修复）保持未 commit、未碰 `.git`；最终 checkpoint 由主 session 复测后执行。
- Next spec readiness: SPEC-00～09 全部 Done，无后继 spec。剩余动作：主 session 最终 checkpoint；用户决定 push 与向 Kimi 发送（需单独授权）；可选补充 external agent 与浏览器可视化证据。
