# 02 — 竞品综合分析：Orbital vs Claude Code vs Codex vs 周边玩家

> 综合自 docs/research/ 三份原始研究（claude-code.md / codex.md / adjacent.md，全部 2026-09-01 联网核实，附来源 URL）。
> 本文只放支撑判断的事实，完整证据链在 research/ 目录。

## 1. 正面回答「Orbital 和 Claude Code / Codex 太像了」

**表层层级——确实趋同，但那是 2026 年的 table stakes：**

多端形态（CLI/IDE/Desktop/Web/手机）、subagent 编排、记忆文件、MCP、沙箱、审批、hooks/triggers——三家全有。

**结构层级——根本不同：**

| 维度 | Claude Code / Codex | Orbital |
|---|---|---|
| 工作单元 | session（个人的一次对话） | project（一个文件夹 + 五类状态文件） |
| 状态归属 | `~/.claude/`、`~/.codex/`（机器私有） | 项目目录内（PROJECT_STATE / DECISIONS / LESSONS / queue.json） |
| worker 池 | 只能自家模型（Claude 系 / Codex 系） | 任意 CLI agent（Claude Code、Codex、Gemini CLI、Cursor、dsh…） |
| 任务闭环 | session 结束编排状态即丢（agent teams 明文 "never uploaded"、"no project-level equivalent"） | queue.json 强制 Completed/Blocked 收敛，可跨天续跑 |
| 记忆 | auto memory machine-local，不跨机器共享 | 项目内纯文本文件，天然可 git 化 |

一句话反驳：**它们的「项目记忆」是给 agent 的说明书（CLAUDE.md / AGENTS.md——描述"该怎么干活"）；Orbital 的项目记忆是项目本身的状态（记录"干到了哪、为什么这么干"）。** 形似神不似。

## 2. 单机维度对比（2026-09）

| 能力 | Orbital | Claude Code | Codex |
|---|---|---|---|
| 异构 worker 调度 | ✅ 任意 CLI agent | ❌ 仅 Claude 系模型 | ❌ 仅 Codex 系 |
| 跨 session 项目状态 | ✅ 五类文件 + 冷启动组装 | ⚠️ CLAUDE.md + auto memory（machine-local） | ⚠️ AGENTS.md + Memories（Limited） |
| 任务队列与强制闭环 | ✅ queue.json，Completed/Blocked 收敛 | ❌（agent teams 实验性，session 级） | ❌（并行 cloud tasks 为个人任务列表） |
| 项目级预算 | ✅ per-project | ❌ org/user 级 | ❌ 计划级 credits |
| 审批系统 | ✅ fail-closed + 手机审批 | ✅ 单 session permission prompts | ✅ 档位审批 + Guardian 自动审 |
| 沙箱 | ✅ Seatbelt/sandbox user（bwrap 在 roadmap） | ✅ sandbox | ✅ Seatbelt/bwrap/Windows |
| 手机监督 | ✅ 多 worker 队列 + 审批 | ⚠️ Remote Control（本人 session） | ✅ mobile remote control（云端任务） |
| 浏览器自动化 | ✅ 26 动作反检测 | ✅ Claude in Chrome | ✅（2026-08 扩展） |
| Worker 记忆 | ✅ 每 worker 独立记忆文件 | ⚠️ subagent memory 三档目录 | ❌ 未核实 |

单机维度 Orbital 领先项清晰（异构调度、队列闭环、项目预算），但 codex.md 的警告必须正视：**Codex 正快速吃掉「单机编排」叙事（subagents 默认开启 + proactive delegation + Guardian）**。差异空间在单机维度会被挤压，必须升维。

## 3. 团队协作维度对比（本作业的核心表）

| 能力 | Orbital 现状 | Claude Code | Codex | Cursor | Devin | GitHub Copilot |
|---|---|---|---|---|---|---|
| 团队共享项目状态/记忆 | ❌ 单机文件 | ❌ machine-local | ❌ | ⚠️ "shared team context"（黑盒） | ⚠️ Knowledge（平台资产） | ⚠️ Spaces（检索型知识库） |
| 异构 worker 编排 | ✅ 但单人 | ❌ | ❌ | ❌ | ❌ Outposts 仅编排 Devin | ⚠️ 控制面含第三方，但偏 review/merge 工作流 |
| 跨人任务队列 | ❌ | ❌ | ❌ | ❌ | ⚠️ Outposts 自托管队列（Devin 专用） | ❌ |
| 跨人审批流转 | ❌ 单 owner | ❌ 审批只弹给操作者本人 | ❌ | ⚠️ org 级 auto-run 策略 | ⚠️ 用量政策（非审批路由） | ❌ |
| 团队/项目级预算 | ⚠️ per-project 单人 | ❌ org/user 级 | ❌ 计划级 | ⚠️ Enterprise pooled usage | ✅ 团队共享 credits 池 | ❌ |
| 团队可观测性 | ❌ | ❌ Agent view 单人视角 | ⚠️ Analytics（Enterprise 档） | ✅ usage analytics | ✅ | ⚠️ |
| IT 治理（SSO/审计/RBAC） | ❌ | ✅ Team/Enterprise | ✅（深档在 Enterprise） | ✅ | ✅ | ✅ |

**读法**：右五列是厂商做给 IT 部门的「采购功能」；Orbital 现状是「单人全功能」。表中对角线空档——**把编排/治理能力从单人扩展到团队**——没有直接对位产品。

## 4. 全行业共同空白（Team Feature 的空间）

四条结构性空白（证据指针见 research/adjacent.md 第 5 节）：

1. **团队共享、可版本化的项目状态层**：所有厂商的"共享"对象都是平台内资产（Cursor rules/skills/plugins、Devin Knowledge、Copilot Spaces、Fleet agents）——没有一家把「以文件形式存在、可 git 版本化、人类与多个异构 agent 共读写」的项目状态层产品化。这正是 Orbital 的 PROJECT_STATE / DECISIONS / LESSONS / queue.json。
2. **异构 agent 编排 × 团队运营面的组合**：Devin Outposts 的队列-认领与 Orbital 架构同形但生态封闭；Fleet 的审批 inbox 只管自家 agent；Copilot 控制面偏 review/merge。「多厂牌 agent 同队列 + 多人监督 + 统一预算」无对位产品。
3. **跨异构 agent 的统一预算与审批**：Devin/Cursor/Fleet 都做了"钱"的团队维度，但都绑定自家用量计量。
4. **跨人、跨机器、跨 session 的持久任务队列**：Claude Code agent teams 明文 "never uploaded"、"no project-level equivalent of the team config"。

**最接近的三个身影**（答辩时要主动提）：GitHub Copilot 多 agent 控制面（巨头 + 已纳第三方 agent）、Devin Outposts（架构同形）、OpenHands Agent Canvas（team-shared Agent Server，OSS 最接近）。但三者分别缺：运营面深度 / 异构性 / 治理产品化。

## 5. 威胁与时间窗

- 品类已成型：LangSmith Fleet 官方对比页（2026-05-05 更新）已把「多人共享 agent + RBAC + 集中审批 inbox + spend limits + 审计」列为正式品类（Claude Cowork / Amazon Quick / Google Workspace Studio / Microsoft Copilot 同台）——Orbital 的审批/预算/手机监督**不再是独创，独创在共享对象**。
- 多方正从不同方向逼近同一空间（Cursor shared team context、Devin Outposts、OpenHands、Copilot 控制面）——窗口存在但有限，估计 6–12 个月。
- 结论：Orbital 的差异化必须落在「git 化项目状态 × 异构编排 × 团队治理」的**组合**，不能赌任何单一功能点。

## 6. 给本作业的结论

1. 「雷同」的解法不是功能对表，而是升维：竞品的团队功能 = 卖给 IT 的治理；Orbital Team Feature = 让「project as unit」变成「project as the team's shared unit」。
2. 竞品文档级空白明确（第 4 节四条），且 Orbital 一手机制（纯文本状态、队列闭环、审批、预算、异构调度）恰好是补空白的现成地基。
3. 立论成立，进入场景与方向池（docs/10、docs/11）。
