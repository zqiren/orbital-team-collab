# 30 — Orbital Team Workspace Roadmap

> 状态：M0～M7 / SPEC-00～09 已完成；Post-v1 路线保持未实现（2026-09-01）
> 原型执行索引：`specs/README.md`

## 1. 路线原则

1. 先证明 Project 协作闭环，再扩张团队控制面。
2. 每个阶段从文件冷启动、以可验证状态结束；不把 agent session 当连续性来源。
3. v1 demo 只宣称单机多 worktree，不把 Git 说成实时数据库，不把 replay 冒充 live。
4. Team Cloud、Approval Routing、Team Budget 是产品路线，不偷偷塞进自包含原型。
5. clean clone 和安全恢复优先于 UI 包装。

## 2. 原型里程碑

### M0 — Product Contract（SPEC-00）

目标：冻结角色、两层文件模型、schema、状态机、命令、事件、权限和实现边界。

交付：

- PRD：用户、范围、v1 旅程、产品/原型边界。
- Architecture：Git common-dir runtime、storage transaction、Manager pipeline、Dashboard/IM boundary。
- Protocol + JSON Schema：后续实现唯一契约。
- Roadmap：SPEC-01～09 依赖与 post-v1 边界。

退出条件：新 session 不需要新增产品决定即可开始 runtime kernel。

### M1 — File Runtime Kernel（SPEC-01）

目标：从任意 worktree 安全解析共享 runtime，提供 schema validation、lock、atomic write、operation journal、event 与 idempotency。

关键风险与验证：

- 风险：`.git`/worktree 路径差异。验证主 worktree + 两个 linked worktree 指向同一 runtime。
- 风险：多文件状态与 event crash gap。验证 Prepared operation 在每个中断点可恢复且不重复 event。
- 风险：reset 误删。验证只接受带 marker 的精确 runtime 路径。
- 风险：日志隐私。验证 runtime/log 默认当前用户私有。

演示增量：`teamctl init/status` 可从 seed 创建并读取一个 Project。

### M2 — Member Workflow（SPEC-02）

目标：实现 join、deterministic resolve、原子 claim、start、block、status、Context Pack 与 immutable Report。

关键风险与验证：

- Alice/Bob 并发 claim 同一 Ready Task，恰好一个成功。
- 歧义、已领取、依赖未完成、blocking question 均零副作用。
- Report commit/branch/worktree binding 真实可验证。
- `Claimed → Submitted` 被拒绝；同 task+commit report 幂等。

演示增量：两个终端能共享任务状态并提交结构化 Report。

### M3A — Member Skill & Adapters（SPEC-03）

目标：把 `/team` 行为映射到同一 CLI/domain 层，提供至少一个原生 slash adapter 和 agent-neutral fallback。

关键风险与验证：

- adapter 不能复制状态机或只输出 prompt。
- SessionStart 只加载 bounded context，不自动 claim。
- member run metadata 与可用 transcript/log 进入 local runtime，不泄漏到 Git。

演示增量：真实 agent session 能发现 `/team claim/start/report`。

### M3B — Event-driven Manager Integration（SPEC-04）

目标：`report.submitted` 自动创建 Job，短生命周期 Manager Run 审查、验证、merge，并产生可恢复结构化结果。

关键风险与验证：

- 同 Project integration slot 串行；跨 Project 可独立运行。
- runner crash/timeout 不重复 merge；retry 超限转 Blocked。
- 实际 merge/knowledge commit 共用 git mutation lock；Awaiting Knowledge 释放 integration slot 也不会产生并发 Git 写。
- natural-language stdout 不能伪装结构化成功。
- force push、remote push、path escape 等 guardrail 失败关闭。

演示增量：成员 Report 后无需提醒，Manager 自动把 clean diff 合入 canonical workspace。

### M4A — Manager Knowledge Compilation（SPEC-05）

目标：把 merged diff + Report 编译成受验证 Knowledge Proposal，安全 apply 到 PROJECT_STATE/DECISIONS/LESSONS/INDEX。

关键风险与验证：

- base hash 变化使 proposal Stale，不覆盖并发 memory。
- 冲突决定产生 Open Question；回答后 `knowledge.resume_requested` 启动新 run。
- Awaiting Knowledge 不占 integration slot。
-重复 report/proposal 不重复写 lesson 或 apply。

演示增量：代码合并后，Dashboard 可看到结构化 knowledge summary 和 Git layer 的真实变化。

### M4B — IM Context Stub（SPEC-06）

目标：fixture/provider contract 产生 Potential Task/Open Question，并支持 triage/promote/dismiss/duplicate。

关键风险与验证：

- ingest 幂等；只保存最小 synthetic evidence。
- Promote 原子生成 Draft，不自动 Ready/claim。
- 不接真实账号、凭证或 IM retention。

演示增量：一条 fixture 消息进入候选区，而不是未经确认启动 agent。

### M5 — Local Team Dashboard（SPEC-07）

目标：用本地 loopback UI 展示/操作三类工作对象、activity、integration、knowledge 和 run/session logs。

关键风险与验证：

- server 无数据库，重启后完全从 runtime 恢复。
- Human actor 在 server 启动时绑定；browser payload 不能冒充 Member/Manager。
- file corruption/lock timeout/runner offline/transcript unavailable 是显式错误。
- Knowledge view 只消费冻结的 change-summary schema。

演示增量：一个页面观察从 claim 到 knowledge apply 的完整闭环。

### M6 — Demo Orchestration（SPEC-08）

目标：从版本化 seed 安全创建临时 Git repo、Manager workspace、Alice/Bob worktrees、runtime、fixture 和 live/replay scenario。

关键风险与验证：

- 两次连续 setup/reset 都从干净 seed 开始。
- demo 不修改交付 repo；cleanup 只作用于带 marker 的精确临时目录。
- 至少一次真实 Manager/Member agent live rehearsal。
- runner 缺失时 doctor 明确提示；replay 全程标注 simulated。

演示里程碑：5 分钟内展示“IM 候选 → 两成员 claim/report → Manager 串行 merge → knowledge 更新 → 新成员继承”。

### M7 — E2E Hardening & Delivery（SPEC-09）

目标：从 Kimi 评审者视角完成 clean-clone、完整测试、安全扫描、README、截图/录制素材和限制声明。

关键风险与验证：

- README 命令在临时 clean copy 逐条执行。
- repo 不含 runtime、真实 IM、transcript、凭证、绝对用户路径或 Orbital API 依赖。
- schema、CLI help、PRD/architecture/protocol 与实现一致。
- 未覆盖平台或 runner 明确列为限制，不隐藏失败。

交付里程碑：30 秒理解差异、2 分钟理解闭环、5 分钟跑起 Dashboard/demo。

## 3. Spec 依赖

```text
SPEC-00 → SPEC-01 → SPEC-02 → SPEC-04 → SPEC-05 ┐
                    └→ SPEC-03 ──────────────────┼→ SPEC-08 → SPEC-09
             SPEC-01 → SPEC-06 → SPEC-07 ───────┘
                              SPEC-04 ─→ SPEC-07
```

并行只是依赖允许，不代表同一 session 混做两个 spec。每个 Completion Record 是下个阶段的实际起点。

## 4. Prototype Done 定义

- 一个 clean clone 不安装 Orbital 即可 setup 并启动 Dashboard。
- 两个 Member worktree 共享 runtime，原子 claim 不双写。
- Report 自动触发可替换 ManagerRunner；clean merge 与失败路径均有结构化证据。
- Knowledge Proposal 安全 apply，新的 agent context 能读取变化。
- IM fixture 只产生候选/问题。
- runtime 与 logs 本地持久但不进入 Git；repo 前后状态可证明未污染。
- fake runner 回归稳定，至少一次真实 agent live rehearsal 可复现。

### 最终实现证据与未覆盖项

- disposable clean-copy 可完成 editable install、完整 tests、builtin 双成员 live-scripted pipeline、knowledge、projection、replay/reset，并证明 source repo 未污染。
- builtin runner 覆盖真实 subprocess/worktree/Git/domain 闭环；replay 明确 simulated，二者均不冒充 external LLM agent。
- 当前 sandbox 未满足“external LLM agent live rehearsal”和“真实 loopback browser/socket”两条环境证据：nested Codex provider 初始化 EPERM、Claude CLI 不可用、loopback bind EPERM。普通本机复测步骤固定在 `docs/38-final-verification.md`，这些限制不扩大或隐藏 v1 产品范围。
- 根 `README.md`、Protocol/schema、SPEC Completion Records 与 `scripts/verify_clean_copy.py` 构成最终 reviewer handoff。

## 5. Post-v1 产品路线

### Phase A — Team Cloud Alpha

目标：让 local runtime 在不同成员机器间安全同步，而不是通过 Git merge 高频 JSON。

必须先解决：

- tenant/user/device identity 与 Project membership。
- object/event replication、offline queue、冲突与幂等协议。
- encryption in transit/at rest、secret boundary、regional storage。
- session/log opt-in、redaction、retention、delete/export。
- role-based Dashboard access 与 audit trail。

不变原则：Git 继续承载 code + durable knowledge/PR review；Cloud 主要同步 runtime 与 observability。

### Phase B — Approval Routing + Team Budget

- 风险 policy：操作类型、路径、金额、项目和成员规则。
- 审批路由：单审/会签/escalation、手机处理、fail-closed timeout。
- per-project/member/worker/provider 预算与超限动作。
- 跨异构 runner 的统一 usage ledger 与归因。

这两项是完整 “Git-native Team Workspace = Shared State + Approval + Budget” 旗舰组合，但不阻塞 v1 wedge 的验证。

### Phase C — Heterogeneous Worker Pool

- 成员机器/自托管/云 runner 注册、capability/cost/license routing。
- lease、heartbeat、lost-worker recovery 与 capacity policy。
- 不把 provider agent 私有 session 变成事实来源。

### Phase D — Team GA

- SSO/SCIM、RBAC、自定义 retention、audit export、data residency。
- 迁移/versioning、backup/restore、SLO、支持矩阵。
- 企业策略不能破坏 local-first 与 repo 可移植性。

## 6. 决策门

后续只有在证据出现时才扩大范围：

| Gate | 证据 | 决定 |
|---|---|---|
| G1：原子协作成立 | 并发 claim/report/integration E2E 稳定 | 进入真实团队试用 |
| G2：knowledge 有价值 | proposal 接受率、重复踩坑率、新人时间改善 | 扩展 memory compiler |
| G3：跨机器需求强 | 试用团队 runtime 手工同步成本 | 投入 Team Cloud Alpha |
| G4：治理产生付费 | 审批/预算事件频率与负责人需求 | 实现 F2/F3 |
| G5：远程异构调度必要 | runner 利用率、跨设备任务量 | 实现 Worker Pool |

## 7. 主要产品风险

| 风险 | 当前对策 |
|---|---|
| “Git-native”被质疑 runtime 不同步 | 两层模型明确写入 README/PRD；v1 限定单机，Team Cloud 放 roadmap |
| demo 与旗舰 F2/F3 不一致 | 明确 demo 验证共享状态 wedge，审批/预算是 post-v1 产品路线 |
| Manager 错误覆盖知识 | allowlist + base hash + proposal validation + Open Question |
| agent run 不可恢复 | 每次从文件冷启动；operation journal + idempotency |
| session logs 泄密 | 用户私有权限、loopback、provider-dependent、后续 retention/redaction |
| schema 在独立 spec 漂移 | v1 schema bundle 为规范源；变更必须先更新 protocol/decision |
| demo 被 replay 掩盖 | live acceptance 必须单独通过；replay 永久标注 simulated |
