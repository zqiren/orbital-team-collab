# Orbital Team Workspace — Spec Index

本目录把 Team Workspace 原型拆成可在独立 session 中完成的实现阶段。每个 spec 都必须从可验证的前置状态开始，以可运行、已验证、可交接的状态结束；执行者不需要读取此前聊天记录。

## 执行入口

开始任何 spec 前，完整阅读：

1. `AGENTS.md`
2. `orbital/PROJECT_STATE.md`
3. `orbital/DECISIONS.md`
4. `orbital/LESSONS.md`
5. `specs/EXECUTION_PROTOCOL.md`
6. 当前 spec
7. 所有直接依赖 spec 的 `Completion Record`

## 状态定义

- `Planned`：已定义但依赖未满足。
- `Ready`：所有依赖均已完成，可以开启新 session。
- `In Progress`：当前有 session 正在执行。
- `Done`：验收、验证和 handoff 全部完成。
- `Blocked`：无法在当前权限或既定设计内继续；Completion Record 必须说明原因。

## Spec Map

| ID | 标题 | 阶段 | 状态 | 直接依赖 | 解锁 |
|---|---|---|---|---|---|
| [SPEC-00](SPEC-00-product-contract-and-architecture.md) | Product Contract & Architecture | Contract | Done | — | SPEC-01 |
| [SPEC-01](SPEC-01-file-runtime-kernel.md) | File Runtime Kernel | Runtime | Done | SPEC-00 | SPEC-02, SPEC-06 |
| [SPEC-02](SPEC-02-project-command-and-member-workflow.md) | `/team` Command & Member Workflow | Runtime | Done | SPEC-01 | SPEC-03, SPEC-04 |
| [SPEC-03](SPEC-03-member-skill-and-agent-adapters.md) | Member Skill & Agent Adapters | Agent UX | Done | SPEC-02 | SPEC-08 |
| [SPEC-04](SPEC-04-event-driven-manager-integration.md) | Event-driven Manager Integration | Manager | Done | SPEC-02 | SPEC-05, SPEC-07 |
| [SPEC-05](SPEC-05-manager-knowledge-compilation.md) | Manager Knowledge Compilation | Manager | Done | SPEC-04 | SPEC-08 |
| [SPEC-06](SPEC-06-im-context-and-potential-task-stub.md) | IM Context & Potential Task Stub | Discovery | Done | SPEC-01 | SPEC-07, SPEC-08 |
| [SPEC-07](SPEC-07-team-dashboard.md) | Tasks / Potential Tasks / Open Questions Dashboard | UI | Done | SPEC-04, SPEC-06 | SPEC-08 |
| [SPEC-08](SPEC-08-demo-fixture-and-orchestration.md) | Demo Fixture & Multi-agent Orchestration | Demo | Done | SPEC-03, SPEC-05, SPEC-06, SPEC-07 | SPEC-09 |
| [SPEC-09](SPEC-09-e2e-hardening-and-delivery.md) | End-to-end Hardening & Delivery | Delivery | Done | SPEC-08 | — |

## Critical Path

```text
SPEC-00 → SPEC-01 → SPEC-02 → SPEC-04 → SPEC-05 ┐
                    └→ SPEC-03 ──────────────────┼→ SPEC-08 → SPEC-09
             SPEC-01 → SPEC-06 → SPEC-07 ───────┘
                              SPEC-04 ─→ SPEC-07
```

## 冻结的产品原则

- 交付 repo 自包含；不依赖 Orbital 安装、daemon 或本地 API。
- 文件是唯一事实来源；本地进程和界面只是文件协议的执行器或投影。
- Manager 是角色，不绑定 Codex、Claude、Gemini 或其他 agent。
- 成员通过 `/team claim <project-name> <task-id-or-query>` 原子完成任务匹配、认领和上下文加载。
- 成员必须显式 `/team start <task-id>` 后才能 report；不允许 `Claimed → Submitted`。
- Git 版本化 durable project knowledge、配置、代码和 demo seed；协调 runtime 与 run/session logs 持久化在本机并由 Dashboard 读取，但不提交到 Git。
- 工作系统包含 Confirmed Tasks、Potential Tasks 和 Open Questions 三类独立对象。
- Potential Task 必须经 Promote 才能成为可领取的 Confirmed Task。
- Blocking Open Question 会阻止任务被领取。
- 成员 report 事件自动触发新的 Manager Agent Run；不依赖长期交互 session。
- Manager 先集成代码，再编译 canonical project knowledge；两步分别记录和恢复。
- 第一版 IM 能力只实现 provider contract 与 fixture，不接真实用户账号。

## 状态维护规则

- 某 spec 开始时，将其状态改为 `In Progress`。
- 某 spec 完成时，将其状态改为 `Done`，并把所有依赖均已满足的后继 spec 改为 `Ready`。
- 不得只更新本索引而不填写目标 spec 的 `Completion Record`。
- 若实现偏离冻结产品原则，必须先向用户对齐并在 `orbital/DECISIONS.md` 记录新决定。
