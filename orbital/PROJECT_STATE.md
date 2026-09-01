<!--format PROJECT_STATE is what is true NOW: current focus, in-progress work, blockers, next steps. Overwrite stale lines; never append dated history. Every line must be understandable without this session's context: concrete names, no unexplained shorthand, no cross-references by list number. [user] flag — one judgment per line: does this need the user (their decision, their action, or something they'd be sorry to miss — including things they assigned to themselves)? If yes, insert [user] after the list marker of the line where the fact already lives: `- [user] <text>` or `3. [user] <text>`. Flagging marks a line, never creates one: one fact = one entry, never duplicated into another section. A dated commitment needing no decision is `[due:YYYY-MM-DD]` (shows on the calendar). Machine attributes (id, created, touched, resolved) live in a daemon-managed mem-comment on the next line — never write or edit these comments; leave them exactly where they are. Never auto-decide: spending money, sending external messages as the user, or irreversible/destructive acts are always surfaced, whatever the autonomy setting. Write timeless ("due Jul 28", never "tomorrow"). A line whose mem-comment carries resolved:<date> is settled — on consolidation rewrite it as the completed fact or drop it; never re-open or re-flag it. CLOSE THE LOOP THE SAME TURN: the moment the user answers a flagged line, decides it, or does it, remove the [user] flag from that line in this turn — rewrite the line as the settled fact (`- Chose option A.`) and leave the mem-comment alone. You are the only reader who can see both the flag and the user's answer; consolidation runs later, sees a truncated window, and cannot do this for you. A flagged line you leave behind after it is answered keeps nagging the user for something they already gave you. Never flag a question you asked during this session — flag the decision that is still genuinely open, written so someone who was not here can act on it.-->
# PROJECT_STATE

## 当前阶段
用户指示（2026-09-01）把剩余 spec（SPEC-03～09，含 demo）由 claude-code 派发子 agent 跑完，主 session 逐 spec 复测 + checkpoint commit。pytest 环境修复：根目录 pytest.ini（testpaths/pythonpath=src）+ conftest.py EPERM shim，基线全量绿；SPEC-04（关键路径）由 claude-code 编排执行中。

## 已完成（2026-09-01）
- orbital/instructions/project_goals.md — 项目目标
- docs/00-assignment-brief.md — 作业理解、成功标准、repo 规划草案
- docs/01-orbital-current-state.md — Orbital 现状盘点（README 抓取 + 一手体感）
- docs/01b-orbital-source-notes.md — 源码级盘点（main tarball：单人假设逐层坐实 + 旗舰功能代码触点映射）
- docs/research/claude-code.md、codex.md、adjacent.md — fanout 三 worker 联网核实（全部 2026-09-01，含来源 URL）
- docs/02-competitive-landscape.md — 「雷同」反驳 + 团队维度对比表 + 四条全行业空白
- docs/10-user-scenarios.md — 画像 A/B/C + 场景 S1–S6 + 优先级
- docs/11-team-feature-directions.md — 方向池 F1–F7 + 优先级矩阵 + 旗舰组合
- specs/README.md、specs/EXECUTION_PROTOCOL.md — 十阶段依赖图、统一执行与 handoff 协议
- specs/SPEC-00～SPEC-09 — 从产品契约、文件 runtime、成员/Manager 工作流、IM stub、看板到 E2E 交付的独立 session specs
- docs/20-prd.md、docs/21-architecture.md、docs/22-protocol.md、docs/30-roadmap.md — 已冻结的 Team Workspace PRD、架构、协议与路线图
- schemas/v1/orbital-team.schema.json — Protocol 1.0 规范 schema bundle（48 个 `$defs`）
- src/orbital_team/、pyproject.toml — Python 3.11+ 单 package runtime/storage 与 `teamctl init/status/reset`
- tests/test_runtime_kernel.py — 24 项 Git common-dir、并发、崩溃恢复、幂等、reset、路径 guard 与权限测试
- demo/seed/、docs/31-file-runtime-kernel.md — 版本化 Apollo 初始化输入与 SPEC-01 安装/运行说明
- src/orbital_team/member_workflow.py、tests/test_member_workflow.py、docs/32-member-workflow.md — worktree identity、Task resolve/原子 claim、bounded Context Pack、成员状态机、Git-bound Report 与 26 项专项测试
- orbital-src/ — Orbital 官方 main 源码快照（git clone 被沙箱挡，改 tarball，见 LESSONS）

## 核心结论（已锚定）
- Orbital = 1 人 × N agents；竞品「团队功能」= 卖给 IT 的治理；全行业空白 = git 化项目状态 × 异构编排 × 团队治理的组合，窗口 6–12 个月
- 源码层佐证：queue Source 枚举仅 USER/UPLOAD、进程内锁、账本无主体维度、api 无用户级 auth——单人假设从产品到代码一致
- 旗舰组合：Git-native Team Workspace = F1 Shared Project State + F2 Approval Routing + F3 Team Budget；F5 做 demo 载体；代码触点已映射（docs/01b 第 3 节）
- demo 方向已收敛为自包含的 file-native Team Workspace：不依赖 Orbital 安装/API；Manager/Member 是 agent-neutral 角色；成员用 `/team claim` 原子认领并上报，文件事件自动启动短生命周期 Manager Run 完成代码与知识合并
- 产品采用两层文件模型：Git 版本化 durable knowledge/config/code/demo seed；tasks/events/reports/jobs/run logs 持久化在本地 runtime、由 Team Dashboard 读取但不提交，未来 Team Cloud 负责跨机器同步
- SPEC-00 的 8 个 design review questions 已全部收敛：入口 `/team`；其余采用 DECISIONS D11 的默认契约
- 实现边界已冻结为 Python 3.11 单一 domain/storage package + JSON Schema/filelock + 无 Node/DB 的 loopback Dashboard；代码 merge 用 `integration.merged`，knowledge commit 后才 `integration.completed`
- durable knowledge apply 生成独立本地 Git commit（no-change 不造空 commit）；所有 merge/commit 经 git mutation lock 与受控 domain command，绝不 remote push
- 工作系统包含 Confirmed Tasks、Potential Tasks、Open Questions；IM v1 只留 provider stub/fixture，Potential Task 经 triage 后才能成为可领取任务

## 下一步
1. 剩余 spec 由 claude-code 编排执行，顺序 SPEC-04 → 05 → 03 → 06 → 07 → 08 → 09（每 spec 单独派发，主 session 验证后 checkpoint）；SPEC-04（teamd、Integration Job、ManagerRunner、受控 merge）已派发
2. SPEC-03 必须复用 `MemberWorkflow`/`teamctl` 并由 current worktree join binding 推导 actor，不复制状态机或接受可冒充的 member payload；SPEC-04 从 `report.submitted` 和 immutable Report 冷启动
3. 每个 spec 完成后由主 session 复测并本地 checkpoint commit，发送给 Kimi/其他外部对象仍需单独授权
4. checkpoint 历史：SPEC-00 `902a870`、SPEC-01 `06691b4`、SPEC-02 `83cbf6e`；子 agent 沙箱可能无法写 `.git/index.lock`，实现后由主 session 复测并 commit；git 命令仍须加 `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null`（见 LESSONS）
5. Push 由用户在本机终端执行 `cd /Users/keanezhou/Desktop/Agent-collaboration && git push -u origin main`（2026-09-01 用户决定暂缓：拒绝提供 PAT，沙箱无 gh/ssh/keychain 凭据）；后续 spec 完成同样先本地 commit，push 一并交给用户
  <!--mem id:380ae9 created:2026-09-01 touched:2026-09-01-->

## 阻塞
- 无实现阻塞；SPEC-04 执行中（claude-code 编排），其余按派发顺序排队。
- 已完成的 checkpoint（`902a870`、`06691b4`、`83cbf6e`）均未 push 到 origin/main；沙箱内无 HTTPS 凭据，由用户在自己终端决定 push 节奏。
