<!--format PROJECT_STATE is what is true NOW: current focus, in-progress work, blockers, next steps. Overwrite stale lines; never append dated history. Every line must be understandable without this session's context: concrete names, no unexplained shorthand, no cross-references by list number. [user] flag — one judgment per line: does this need the user (their decision, their action, or something they'd be sorry to miss — including things they assigned to themselves)? If yes, insert [user] after the list marker of the line where the fact already lives: `- [user] <text>` or `3. [user] <text>`. Flagging marks a line, never creates one: one fact = one entry, never duplicated into another section. A dated commitment needing no decision is `[due:YYYY-MM-DD]` (shows on the calendar). Machine attributes (id, created, touched, resolved) live in a daemon-managed mem-comment on the next line — never write or edit these comments; leave them exactly where they are. Never auto-decide: spending money, sending external messages as the user, or irreversible/destructive acts are always surfaced, whatever the autonomy setting. Write timeless ("due Jul 28", never "tomorrow"). A line whose mem-comment carries resolved:<date> is settled — on consolidation rewrite it as the completed fact or drop it; never re-open or re-flag it. CLOSE THE LOOP THE SAME TURN: the moment the user answers a flagged line, decides it, or does it, remove the [user] flag from that line in this turn — rewrite the line as the settled fact (`- Chose option A.`) and leave the mem-comment alone. You are the only reader who can see both the flag and the user's answer; consolidation runs later, sees a truncated window, and cannot do this for you. A flagged line you leave behind after it is answered keeps nagging the user for something they already gave you. Never flag a question you asked during this session — flag the decision that is still genuinely open, written so someone who was not here can act on it.-->
# PROJECT_STATE

## 当前阶段
Team Workspace 的跨 session 实现计划已拆为 SPEC-00～SPEC-09；SPEC-00 Product Contract & Architecture 已 Ready，后续每个 spec 在独立 session 执行。

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
- orbital-src/ — Orbital 官方 main 源码快照（git clone 被沙箱挡，改 tarball，见 LESSONS）

## 核心结论（已锚定）
- Orbital = 1 人 × N agents；竞品「团队功能」= 卖给 IT 的治理；全行业空白 = git 化项目状态 × 异构编排 × 团队治理的组合，窗口 6–12 个月
- 源码层佐证：queue Source 枚举仅 USER/UPLOAD、进程内锁、账本无主体维度、api 无用户级 auth——单人假设从产品到代码一致
- 旗舰组合：Git-native Team Workspace = F1 Shared Project State + F2 Approval Routing + F3 Team Budget；F5 做 demo 载体；代码触点已映射（docs/01b 第 3 节）
- demo 方向已收敛为自包含的 file-native Team Workspace：不依赖 Orbital 安装/API；Manager/Member 是 agent-neutral 角色；成员用 `/project` 原子认领并上报，文件事件自动启动短生命周期 Manager Run 完成代码与知识合并
- 工作系统包含 Confirmed Tasks、Potential Tasks、Open Questions；IM v1 只留 provider stub/fixture，Potential Task 经 triage 后才能成为可领取任务

## 下一步
1. 新 session 执行 SPEC-00，产出 docs/20-prd.md、docs/21-architecture.md、docs/22-protocol.md、docs/30-roadmap.md 并冻结公开契约；须逐条回答 SPEC-00 内「Design Review Notes (2026-09-01)」列出的 8 个 open questions（最重要：git-native 叙事与本地 runtime 的分层解释）
2. SPEC-00 完成后按 specs/README.md 依赖图逐个 session 执行 SPEC-01～SPEC-09
3. 用户已确认采用单 repo、自包含文件协议和事件驱动 Manager 的 demo 方向；最终推送/发送仍需用户单独授权
4. [user] 工作区已 git init 并连接 remote github.com/zqiren/orbital-team-collab（空仓库），首个本地 commit 已就绪；是否推送到远端需用户授权（一句「推吧」即可执行 `git push -u origin main`）
  <!--mem id:380ae9 created:2026-09-01 touched:2026-09-01-->

## 阻塞
无
