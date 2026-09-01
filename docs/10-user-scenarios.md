# 10 — 目标用户与核心场景

> 上游：docs/01（Orbital 现状）、docs/02（竞品空白）。本文回答：Team Feature 给谁做、解决什么场景。
> 场景中的竞品痛点全部有研究证据（指针到 docs/research/）。

## 1. 目标用户画像

### 画像 A：多 agent 混用的创业工程团队（3–15 人）——核心画像
- 已每人购买 Claude Code / Codex / Cursor 中至少一档，各用各的，格式与习惯不一。
- 痛点：项目上下文散落在各人各 agent 的 session 里；张三的 agent 踩过的坑，李四的 agent 再踩一遍（证据：Claude auto memory "machine-local"，不跨机器）。
- 付费方：tech lead / CTO。

### 画像 B：要「放开用 agent 但不能失控」的工程负责人（20–100 人公司）
- 关心的不是单点功能，是：预算花在哪、高危操作谁批、审计有没有、出事能不能追。
- 现状：Codex/Claude 的治理能力压在 Enterprise 档（audit logs、Analytics API、RBAC），中小团队拿不到（证据：codex.md 第 5 节空白 6）。
- 付费方：平台工程 / Infra 负责人。

### 画像 C：项目交接者与新成员
- 接手别人项目 = 接手一堆散落的 session、私聊记录、口头约定。
- 现状：没有任何工具能交付「项目的 agent 历史状态」；Claude Code 的任务编排状态 session 结束即删（"never uploaded"）。

## 2. 核心场景

### S1 新成员第一天（对应画像 C）——「冷启动继承」
- **现状**：新人读 wiki、问人、翻旧 PR，三天才能让 agent 干活不闯祸；新人的 agent 对项目历史一无所知。
- **Team Feature 后**：clone 项目仓库 = 继承全部项目状态。新人（或新人的 agent）冷启动时，管理 agent 从 PROJECT_STATE / DECISIONS / LESSONS 组装完整上下文：干到哪、为什么这么决策、踩过什么坑。
- **为什么只有 Orbital 能做**：状态天生就在项目文件夹里（docs/01 核心观察：纯文本 → git 化），不需要迁移任何黑盒数据。

### S2 混编战队（画像 A）——「按强项与成本路由的异构 worker 池」
- **现状**：每人一个厂牌 agent，深推理用 Claude、快速跑用 Codex、长上下文用 Gemini——靠人肉切换、人肉传上下文（"你成了 agent 之间搬运上下文的实习生"——Orbital README 原话）。
- **Team Feature 后**：团队共享一个 worker 池：同一队列里 Claude Code、Codex、Gemini CLI、Cursor 按任务特征与预算被派发；谁的 license、哪台机器跑，对任务透明。
- **证据（空白）**：Claude Code worker 只能 Claude 系（sub-agents 文档 model 字段）；Codex 只能 spawn Codex 系；全行业无第二家异构编排（docs/02 第 3 节）。

### S3 越权拦截（画像 B）——「跨人审批流转」
- **现状**：审批永远弹给"正在跑 agent 的那个人"（Claude Code："Permission prompts are passed through to you"）；初级成员的 agent 想跑数据库 migration，没人拦得住，也没人事后知道。
- **Team Feature 后**：审批按规则路由——高危操作（migration / 删文件 / 外发数据）自动路由给项目负责人，手机一键批/驳；预算超限自动上浮审批。Workbench 从「owner 待办」升级为「团队风险队列」。
- **证据（空白）**：两家的审批都是单用户会话内交互，无代理审批机制（docs/02 第 3 节）。

### S4 这个月烧了多少（画像 A/B）——「团队预算与成本可见性」
- **现状**：Claude 只有 org/user 级 spend cap；Codex 是计划级 credits；"给这个任务池 $50、超了自动暂停并请示"无处可设。
- **Team Feature 后**：per-project / per-member / per-worker 预算分配；超限动作可配置（暂停/降级模型/请示）；BYOK 多 provider 统一计量（Orbital 已接 14 家 provider，这是异构编排的天然红利——竞品的计量只能算自家的账）。

### S5 人走了，项目还在（画像 C）——「交接即 git transfer」
- **现状**：员工离职 = 项目上下文随他的 `~/.claude/` 一起蒸发；agent teams 的 task list "never uploaded"。
- **Team Feature 后**：项目状态文件随 repo 归属转移，下一任（和下一任的 agent）无缝继续。队列里未完成的任务、决策的理由、踩坑记录全部保留。

### S6 夜里跑批，早上验收（画像 A/B）——「团队队列 + 触发器 + 分角色看板」
- **现状**：Orbital 已有 triggers 与队列，但队列、看板、审批都是 owner 单人视角。
- **Team Feature 后**：团队共享队列夜间排空；早上一屏看清：谁的项目跑了什么、花了多少、哪三项等人审批。管理层看预算，工程师看进度。

## 3. 场景优先级

| 场景 | 用户强度 | 竞品空白度 | Orbital 现成地基 | 优先级 |
|---|---|---|---|---|
| S1 冷启动继承 | 高（每团队每新人） | 高 | 高（状态已在文件里） | ★★★ 旗舰 |
| S3 跨人审批 | 高（治理刚需） | 高 | 高（审批系统已 fail-closed） | ★★★ 旗舰 |
| S4 团队预算 | 中高 | 中高 | 高（per-project 预算已有） | ★★★ 旗舰 |
| S2 异构 worker 池 | 中高 | 极高（独家） | 高（单机异构调度已有） | ★★ 随旗舰 |
| S5 交接 | 中（低频高价值） | 高 | 高 | ★★ 顺带成立 |
| S6 团队看板 | 中 | 中 | 中（需多人化） | ★ 后置 |

## 4. 反模式（明确不做）

- 不做「团队版聊天室」：协作对象是项目状态，不是人聊人。
- 不先做 SSO/SCIM：那是跟随项（竞品全有），不是差异化；PRD 里仅作为 GA 前的企业清单。
- 不把 team feature 做成云托管 IDE：local-first 是身份，git 是同步层而不是云数据库。
