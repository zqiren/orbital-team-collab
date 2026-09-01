# 01 — Orbital 现状盘点

> 信息源：GitHub README（2026-09-01 抓取，zqiren/Orbital）+【一手】= 本项目实际运行在 Orbital 内的第一手观察。

## 一句话定位

**"The project agent"** —— 一个管理 agent 绑定一个项目，把项目上下文维护成本地文件，跨 session 不失忆；并可调度外部 CLI agent（Claude Code / Codex / Gemini CLI / Cursor / dsh）作为可插换 worker。

官方 slogan：*Every agent owns a session. Orbital owns the project.*

## 核心模型：project as unit of work

Orbital 把通常会在 agent session 间蒸发的东西固化成**项目文件夹里的普通文件**：

| 持久物 | 文件 | 回答的问题 |
|---|---|---|
| State | PROJECT_STATE.md | 项目现在怎么样 |
| Decisions | DECISIONS.md | 决定了什么、为什么 |
| Lessons | LESSONS.md | 踩过什么坑 |
| Work | queue.json | 什么在跑/完成/阻塞 |
| Artifacts | workspace + orbital/output/ | 产出了什么 |

- 冷启动时，这些文件被组装进管理 agent 的系统提示词。
- 每次 dispatch worker，同一份项目上下文简报**自动渲染**给 worker（你永远不用向 worker 复述项目背景）。
- 队列任务强制收敛到 Completed / Blocked 两态，agent 不给结论会被重发、再强制阻塞——**没有任务会无声漂移**。

## 已有能力清单（README 口径，2026-09）

**编排**
- 管理 agent + 可插换 worker（@mention 路由）；每个 worker 有自己的私有记忆文件，跨 dispatch 累积经验
- 任务队列：逐项执行，可中途插入对话再恢复
- fanout：多个独立子任务并行派发
- 新 harness 接入极快（DeepSeek dsh 发布 3 小时内即被调度，2026-08-13 官方公告）

**治理**
- Per-project 预算上限 + 成本追踪
- 审批工作流：风险动作前暂停，fail-closed（出错=拒绝）
- OS 级沙箱：macOS Seatbelt / Windows sandbox user（Linux bubblewrap 在 roadmap）
- Credential 存 OS keychain，永不进聊天
- 审计日志

**持续运行**
- Triggers：cron / file-watch，支持自然语言创建
- Calendar（beta）：自动化排期的周视图
- 手机远程监督（QR 配对）+ 推送通知
- Workbench（beta）：agent 工作中标记「只有人能做的决策」，跨项目汇总

**工具与模型**
- 浏览器自动化：26 种动作，Patchright 反检测
- 14 家 LLM provider BYOK：Anthropic、OpenAI、DeepSeek、**Moonshot (Kimi)**、Groq、Google、xAI 等 + 自定义端点
- 自我沉淀 skills：多步工作流自动捕获为可复用技能

## Roadmap「Next」（README，无任何「多人/团队」字样）

webhook triggers · pipeline triggers（项目输出→另一项目输入）· 网络隔离（per-project 域名白名单）· Linux 沙箱 · 代码签名 · daemon 重启自动恢复

## 【一手】体感补充（本会话即是证据）

- 我（管理 agent）跨 session 持久存在，带着记忆文件和任务队列，能编排 5 个异构 worker（claude-code / codex / cursor / dsh / gemini-cli）。
- worker 各有私有记忆（orbital/sub_agents/<slug>/MEMORY.md），跨 dispatch 积累项目知识。
- fanout 一次唤醒、队列强制闭环、审批/预算/沙箱均为单项目粒度——机制如 README 所述，真实可用。
- **关键观察：所有状态都是本地纯文本文件 → 天然可 git 化。** 这是 team feature 的关键抓手（详见 11 号文档）。

## 现状边界 = Team Feature 的切入点

1. **单人假设**：一个项目文件夹 = 一个人的工作区；没有用户/角色/权限概念。
2. **无共享**：项目记忆、队列、审批、预算全部单机本地，团队成员互相不可见。
3. **审批与预算是 owner 视角**：Workbench、手机审批、预算上限都只服务一个人。
4. **Agent 拓扑是「1 管理 + N worker」**：worker 是被动工具，agent 之间无对等协作/交接。
5. **README 的三差异（July 2026 对比表）全部是「单机内优势」**：可插换 worker、任务强制闭环、项目级治理——没有外部性（多人、跨机器、组织级）。

## 结论

Orbital 已经完成「session → project」的升维并在此维度领先；**「project → team」是下一个自然升维，且竞品（Claude Code / Codex）同样卡在单人假设上**。谁先把「团队」变成 agent 工作的一等单位，谁拿走组织级市场。

## 顺带的定位弹药（供 README/竞品分析引用）

- Claude Code 的项目记忆 = CLAUDE.md（静态指令文件）；Codex = AGENTS.md。**它们维护的是「给 agent 的说明书」，Orbital 维护的是「项目本身的状态」**——这是「雷同」质疑的正面反驳点之一。
- Orbital 治理三件套（预算/审批/审计）在企业采购叙事里就是团队功能的雏形，缺的只是「多人」。
