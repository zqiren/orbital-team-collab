---
id: SPEC-09
title: End-to-end Hardening & Delivery
status: Planned
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
