# 周边玩家与团队级 Agent 协作趋势研究

> 任务：核实「周边玩家」现状与「团队级 agent 协作」赛道卡位情况，为 Orbital Team Feature 规划提供论据。
> 时间基准：2026-09-01（所有来源均为当日抓取，另有页面内标注的自更新日期）。
> 方法说明：当日搜索引擎（Google）被 reCAPTCHA 拦截，关键词扫描（multi-user AI agent collaboration 等）未能执行；本文全部结论基于官方来源直接抓取（定价页 / changelog / 官方文档 / GitHub README），引用处逐条标注。凡未逐页读到的细节标注「据文档索引」或「未核实」。

---

## TL;DR

1. **团队功能已是 coding agent 厂商的标配**：Cursor / Devin / Factory 三家都把「团队计划 + 管理员控制 + 用量分析」做成正式计费层级，且都出现了**团队共享预算/额度池**（Devin 共享 on-demand credits、Cursor Enterprise pooled usage、Factory Teams 共享 Droid Computers 时长）。
2. **「共享 agent 上下文」已进入头部厂商的功能命名**：Cursor Teams 明确写出 "Cloud agents and automations with **shared team context**" 和 "Team marketplace for internal rules, skills, and plugins"（官方定价页原文）。
3. **通用（非编码）企业 agent 平台品类已成型**：LangSmith Fleet 官方对比页（2026-05-05 更新）把 LangSmith Fleet / Claude Cowork / Amazon Quick / Google Workspace Studio / Microsoft Copilot 列为同一品类，核心要素为：多人共享 agent + RBAC + **集中审批 inbox** + spend limits + 审计。
4. **编排框架正在向「自托管、团队共享」收敛**：Devin Outposts（自托管 worker 认领队列）、OpenHands Agent Canvas（自托管控制中心、**团队共享 Agent Server**）、GitHub Copilot（单一控制面管理含第三方 Claude Code/Codex 在内的多 agent）。
5. **没有人做 Orbital 的形状**：所有玩家的「共享」对象是平台内资产（rules/skills/plugins/Spaces/Fleet agents），没有一个产品把「**可版本化的项目状态文件**（人类与异构 agent 共读写）+ 异构 CLI agent 编排 + 团队级队列/审批/预算」组合成产品。这是 Orbital Team Feature 的正面空间；但多方从不同方向逼近，窗口存在但有限。

---

## 1. Cursor

来源：cursor.com/pricing、cursor.com/changelog（均 2026-09-01 抓取）。

### 计划结构（官方定价页原文要点）
- Hobby（免费）：Limited Agent requests、Composer 访问。
- Individual $20/mo（Pro / Pro+ / Ultra 三档）：Extended limits on Agent、frontier models、Grok Bot、**MCPs, skills, and hooks**、**Cloud agents**、Bugbot（usage-based billing）。
- **Teams $40/user/mo**（Standard / Premium 两档），官方列出的团队功能：
  - **Centralized team billing and administration**（集中计费与管理 = admin 能力）
  - **Team marketplace for internal rules, skills, and plugins**（团队内规则/技能/插件市场 = 共享 rules 的产品化）
  - **Cloud agents and automations with shared team context**（云端 agent 与自动化带**共享团队上下文**）
  - **Agentic code reviews with Bugbot**（Bugbot 已从「找 bug 机器人」升级为 agentic code review）
  - **Usage analytics to understand team behavior**（团队用量分析）
  - Team-wide privacy mode、SAML/OIDC SSO
- Enterprise（custom）：在 Teams 之上加 **Pooled usage**（池化用量 = 团队级预算维度）、SCIM、repository/model/MCP 访问控制、**auto-run / browser / network controls**（自动化与网络策略 = 审批管控的组织级形态）、audit logs + service accounts、AI code tracking API。

### 最新版本状态
- 官方 changelog 最新条目日期 **2026-08-27**：Cloud Agents 不再要求连接 GitHub 等第三方 SCM，可先直接 prompt、把产物存入 **Cursor Origin repo**（Cursor 自带仓库），支持浏览器内 live preview（port-forward）与 Vercel 一键发布。
- 具体版本号 changelog 页未展示，**未核实**。

### 对 Orbital 的含义
- Cursor 的团队化深度在 IDE 厂商里最高：共享 rules（marketplace）、共享上下文（shared team context）、管理面（billing/admin/analytics）、审批管控（auto-run/network controls）俱全——但它全部**绑定 Cursor 自家 agent 与平台内资产**，共享的是 Cursor 私有格式的配置，不是可版本化、跨 agent 的项目状态。

---

## 2. OpenClaw

来源：github.com/openclaw/openclaw README（2026-09-01 抓取）。

### 定位
- 官方一句话："Your assistant, on your devices, in your chats"——**开源个人 AI 助手**，跑在用户自己的设备上，通过一个 **Gateway**（本地控制面：sessions、tools、events、channel connections）连接模型、工具、消息渠道（WhatsApp / Telegram / Slack / Discord / Google Chat / Signal / iMessage 等）与配套 app（语音、Canvas、摄像头、屏幕）。
- 由 Peter Steinberger 与社区为「Molty（太空龙虾助手）」开发，OpenClaw Foundation（非营利）维护，MIT 协议。npm 全局安装，Node 22.22.3+/24.15+/25.9+。

### 团队 / 多用户能力
- README 原文："for a single operator **or for a team whose members trust each other**: the same gateway runs as a personal assistant on one laptop **or as a shared team deployment, and configuration is the only difference**."
- 即：多用户在技术上可行（同一 Gateway 作为团队共享部署），但官方把它框定为**互信小组的部署形态**，产品上没有团队计划、没有管理台/角色/计费。
- 安全文档明确警告：入站消息按不受信输入处理；DM 渠道默认对未知发送者做 pairing 审批（`openclaw pairing approve`）；"Read the security guide, exposure runbook, and sandboxing guide **before connecting other users or exposing the Gateway remotely**" —— 把「连接其他用户」与沙箱、暴露风险并列，说明多用户不是一等能力。

### 对 Orbital 的含义
- OpenClaw 是「个人 agent + 自托管 Gateway + 消息渠道监督」路线，与 Orbital 的「项目级编排」定位不同；它列进 Orbital README 的对比对象，更多因为同为「本地 Gateway + 手机/聊天监督」形态。其团队叙事停在「配置即可共享」，恰好反衬：**没有人为共享多用户 agent 做真正的产品层（角色/审批/预算/状态共享）**。

---

## 3. 其他玩家：Devin / Windsurf / Factory / GitHub Copilot

### 3.1 Devin（Cognition）——本赛道团队化最深者

来源：docs.devin.ai/llms.txt（全站文档索引，2026-09-01）、docs.devin.ai/admin/billing/self-serve.md（全文，2026-09-01）。企业功能细节除 self-serve 页全文外，其余**据文档索引**（页面标题 + 官方一句话描述），未逐页通读。

- 定位："Devin is the AI software engineer, built to help ambitious engineering teams crush their backlogs"——从一开始就是团队叙事。
- **自助计划**（self-serve 页原文）：Free / Pro $20（1 人）/ Max $200（1 人）/ **Teams $80/月起、成员数不限**。明确写 "Pro and Max plans are individual plans… cannot be shared"。
  - **Full seat $40/月**：含 Pro 等值配额 + Devin Desktop；**Flex seat 免费、数量不限**：从团队共享额度池扣。
  - **On-demand credits 团队共享、无个人余额**："credits are shared across all members, with no per-member balance"；Automations 与 Devin Review 都从共享池扣费——这是「团队共享 agent 预算」的最直接产品化。
  - 管理员可设 auto-reload 阈值与 session 消费上限（Settings > Usage）。
  - 旧 ACU 计划已迁移（Core → Free，ACU → on-demand credits 等值）。
- **团队/组织级能力**（据文档索引，2026-09-01）：
  - 组织治理：Understanding Organizations、Custom Roles & RBAC、SSO（Okta/Entra/SAML/OIDC）、SCIM、IdP Group Integration、IP Access Lists、audit（Trust Center）。
  - **用量治理**：Usage policies "per-user ACU limits"（用量分层 + IdP 组映射 + 个人覆盖 + 追加申请）；**Devin Coach**（发送前标记低效 prompt、给管理员成效分析）；Personal Analytics（个人查看自己的 ACU 消耗）。
  - **编排**：**Dynamic Workflows**（用确定性 Python 脚本编排多个 Devin session：fan out、阶段间管道、断点续跑）；**Devin Outposts**（**自托管 worker**：orchestration guide 明确 "watch the queue, claim sessions, provision machines"，含 fleet API——与 Orbital「队列 + worker 认领」架构同形，但 worker 只能是 Devin）；Devin CLI subagents（前台/后台）。
  - **组织知识/资产共享**：Knowledge（组织上下文共享，"onboarding a new employee"）、Skills（SKILL.md 提交进仓库）、**Plugin marketplace**（org/enterprise 级插件分发 + policy controls、team marketplace quickstart）、Playbooks（组织级 prompt 库）、Security Profiles（绑定 org/automations/session 的网络/MCP/git 访问限制）。
  - 集成与入口：Slack / Teams / Linear / Jira / GitHub / GitLab / Bitbucket；Automations（Slack、GitHub、Linear、schedule、webhook 触发）；Auto-triage（常驻 Devin 监听 Slack 自动分诊 bug）；Devin CLI 可从 Claude Code、Codex 或任意 coding agent **hand off 任务到云端 Devin**。
- **与 Windsurf 的关系**：docs.devin.ai 存在 "Legacy Windsurf Auth"（用 legacy Windsurf 企业账号登录 Devin CLI）与 "Controls"（把 Devin CLI 与 Cascade 并列，"not yet implement all of the same features and controls"）；Pro 计划说明中 Devin Desktop 链接指向 windsurf.com。可判定 Windsurf 已并入 Cognition 产品线（Devin Desktop 寄于 windsurf.com 域名下）。Windsurf 自身的 Teams/Enterprise 计划细节：windsurf.com 直接抓取被浏览器人机验证拦截，**未核实**。

### 3.2 Factory（droid）

来源：factory.ai/pricing（全文，2026-09-01）。

- 个体：Pro $20/mo（Desktop / CLI / SDK、cloud & local background agents、billing 与 usage statistics、**Agent-readiness dashboard**）；Plus $100/mo（~5x 用量、**Droid Computers**：Factory 托管的云端电脑供远程 Droid 使用）；Max $200/mo（~10x、early access）。
- **Teams $60/mo 每团队 + $40/mo 每席**：全团队 Pro 功能、≤10 席集中计费、**Droid Computers 10 hrs/mo 团队共享**（又一个「团队共享资源池」案例）。
- **Business**：≤150 席、SSO、SAML/SCIM、Zero Data Retention、审计日志与活动轨迹、**Basic admin controls（model selection、autonomy level、model access controls、org-level deny lists、network policy）**。
  - 注意 **"autonomy level" 被列为组织级管理项**——在 admin 控制面里直接管理 agent 的自主程度（即审批强度），这是各家中把「审批策略」摆到组织管理面上最显眼的一例。
- **Enterprise**：不限成员、专属算力（partitioned inference pool）、**Sub-organizations**、full admin controls、CMEK、data residency、**on-prem 部署选项**、TAM/CE/SLA。

### 3.3 GitHub Copilot——「异构 agent 团队管理」最近的巨头动向

来源：github.com/features/copilot（2026-09-01 抓取）。

- 个人计划：Free / Pro $10 / Pro+ $39 / Max $100（credits 制）；Pro 起含 **Cloud agent 与 code review**、**第三方 agent（Claude Code 与 Codex）**访问权。
- 团队相关官方表述（原文要点）：
  - "Manage agent-driven work from one place"：GitHub Copilot app（桌面工作区）——从 GitHub 发起、**跨多个 agent 跟踪进度**、review 变更、merge 完成的工作。
  - "Assign tasks to agents like Copilot, **Claude by Anthropic, and OpenAI Codex**, and let them plan, explore, and execute work autonomously in the background."（明确的多 agent 任务指派 + 后台自主执行）
  - **Copilot Spaces**："Scale knowledge and keep teams consistent by creating a **shared source of truth** that includes context from your docs and repositories."（团队共享知识/上下文）
  - Governance："Track activity with detailed audit logs and enforce governance by managing agents from a **single control plane**"；MCP 服务器 allow lists。
- Business/Enterprise 计划的功能明细页未抓取，**未核实**（FAQ 仅列出三者差异问题标题）。

### 3.4 Windsurf

- 直接证据获取失败（windsurf.com/pricing 被浏览器人机验证拦截，2026-09-01），官网内容**未核实**。
- 间接证据（docs.devin.ai，2026-09-01）：存在 Legacy Windsurf Auth 页与「Devin CLI vs Cascade（Windsurf 的 agent）controls」页，且 Devin Desktop 部署在 windsurf.com 域名——Windsurf 已被 Cognition（Devin 母公司）整合进统一产品线，独立团队计划现状不明。

---

## 4. 趋势扫描（2025–2026）

说明：搜索引擎当日被 reCAPTCHA 拦截，以下为官方来源直接核实；无法覆盖全部长尾，结论按可得证据给出。

### 4.1 「多人共享 agent + 集中审批 + 预算」已成正式品类
LangSmith Fleet 官方对比页《Agent platform comparison》（docs.langchain.com，**页面自注 Last updated May 5, 2026**）把五家列为同一「enterprise agent platform」品类：**LangSmith Fleet / Claude Cowork / Amazon Quick / Google Workspace Studio / Microsoft Copilot**。该页给出的品类共同要素与差异：
- 共同：RBAC、audit trail、SCIM、human-in-the-loop、sub-agents、MCP client、scheduled runs。
- **Fleet 的差异化主张**（原文要点）：唯一自托管 + 唯一代码导出（导出为 MIT 协议的 Deep Agents）；**"centralized inbox for reviewing, editing, and approving actions"——并声称 "No other platform in this comparison offers a single centralized approvals inbox spanning all agents"**（跨全部 agent 的集中审批收件箱）；workspace 级 spend 管理；持久 memory 文件 + **agent 可自我更新指令/工具** + **memory 写入审批门**。
- **Claude Cowork** 在该对比页的定位："delegate open-ended tasks to Claude from the desktop for personal knowledge work"、本地存储优先——即 Anthropic 把团队/个人 agent 分工为 Claude Code（编码）+ Cowork（桌面通用工作），Team/Enterprise 计划含共享 Projects、组织级 skills 部署、**user and organizational level spend controls**（anthropic.com/pricing，2026-09-01）。
- **含义**：到 2026 年中，「多人共享的 agent 平台（含审批 inbox、预算、审计）」已经是被厂商明文对表竞争的品类——Orbital 的「审批/预算/手机监督」不再是独创，独创在**对象**（见结论）。

### 4.2 编排框架的「团队化 / 自托管共享」动向
- **Devin Outposts**（docs.devin.ai，2026-09-01）：自托管 worker + fleet API + 编排器指南（watch the queue → claim sessions → provision machines）。**与 Orbital 的队列-认领架构同形**，但生态封闭（worker 只能是 Devin），且定位企业私有化部署。
- **OpenHands → Agent Canvas**（github.com/All-Hands-AI/OpenHands，2026-09-01）：开源项目已转型为「self-hosted developer control center for coding agents」，多后端（OpenHands、Claude Code、Codex、Gemini CLI、ACP）+ automations，README 明确："**share an Agent Server with your team** for agents doing code review and dependency updates, then have your personal agents running on your laptop"——开源阵营已出现「团队共享 agent 服务器 + 个人 agent 混合」叙事，是最接近 Orbital 形状的 OSS 项目。
- **GitHub Copilot**（见 3.3）：单一控制面管理含第三方的多 agent + Spaces 共享知识 + 审计，是平台巨头从「代码托管 → agent 团队管理面」的自然延伸。
- **Claude Agent SDK**（github.com/anthropics/claude-agent-sdk，2026-09-01）：Claude Code SDK 已更名 Claude Agent SDK，定位纯开发者 SDK；README 未见团队/多用户功能——框架层的团队化由上层平台（Cowork / Fleet）承担，而非 SDK 层。
- **LangChain**：LangGraph Platform 已并入 LangSmith 文档体系（docs.langchain.com 现以 LangSmith 为主体，含 Agent Server API 与 Fleet）；**Deep Agents Code**（终端 coding agent，Deep Agents SDK 之上）具备 AGENTS.md、subagents、approval modes（Manual/Auto/YOLO）、remote sandboxes——但均为单机/单人维度，团队功能在 Fleet 侧。

### 4.3 反向信号：单人假设仍是主流默认
- Cursor/Devin/Factory/Copilot 的团队功能集中在**计费、权限、审计、共享资产分发**；「协作」停留在各用各的 agent + 共享平台内资产。
- Devin 官方甚至明文强调 Pro/Max "cannot be shared across multiple users"——「多人共用一个 agent 及其上下文/队列」在 coding agent 主流产品中仍被当作需要专门计划（Teams $80 起）来闸住的形态，而非默认能力。

---

## 5. 赛道结论

### 5.1 谁卡位最深
- **Devin / Cognition——综合最深**：唯一把「团队共享预算池（credits）+ 组织级用量政策（per-user ACU 限额/分层/IdP 组映射）+ 组织知识/插件治理（Knowledge / Plugin marketplace）+ 编排（Dynamic Workflows、Outposts 自托管 worker 队列）」全链路产品化的 coding agent 厂商；且主打叙事就是 "engineering teams"。
- **Cursor——「共享上下文/资产」维度最深**：team marketplace（rules/skills/plugins）+ "shared team context"（cloud agents）+ Bugbot agentic review + 用量分析 + auto-run/network 管控；但所有共享都发生在 Cursor 平台内部格式里。
- **Factory——组织级审批策略最直白**：把 "autonomy level"（agent 自主度）列为 admin 控制项，等于把「审批强度」变成组织配置；Teams 档的共享 Droid Computers 时长是轻量共享预算形态。
- **巨头平台线（Anthropic Cowork / LangSmith Fleet / Microsoft Copilot / Amazon Quick / Google Workspace Studio）**：把「多人共享 agent + RBAC + 集中审批 inbox + spend limits + 审计」做成了通用工作场景的品类，模型/生态各自锁定；Fleet 的「跨 agent 集中审批收件箱」与「memory 写入审批门」值得 Orbital 直接对标。
- **GitHub Copilot**：离 Orbital 最近的巨头动向——第三方 agent（Claude Code/Codex）纳入同一控制面 + Spaces 共享知识；但控制面管理的是「review/merge 工作流」，非队列/预算/沙箱的完整运营面。

### 5.2 谁都没做透的空白（Orbital 的空间）
1. **团队级「项目状态/记忆」共享**：所有玩家的共享对象是平台内资产（Cursor rules/plugins、Devin Knowledge/plugins、Copilot Spaces、Fleet agents）。没有一家把「**以文件形式存在、可版本化（git）、人类与多个异构 agent 共读写**的项目状态层」产品化——这正是 Orbital 的 PROJECT_STATE / DECISIONS / LESSONS / queue.json。Cursor 的 "shared team context" 是黑盒；Devin 的 Knowledge 是组织级 prompt 资产；Copilot Spaces 是检索型知识库。
2. **异构 agent 编排 × 团队运营面**：Orbital 允许一个管理 agent 调度 Claude Code / Codex / Gemini CLI / Cursor 等任意 CLI agent，并叠加队列/审批/预算/沙箱。现状对照：Devin Outposts 的队列-认领**只编排 Devin**；Fleet 的审批 inbox 只管 Fleet 平台内 agent；Copilot 控制面偏 review/merge。**「多厂牌 agent 同队列 + 团队多人监督 + 统一预算」的组合没有直接对位产品**。
3. **预算作为团队一等公民**：Devin（共享 credits 池 + per-user 限额）、Cursor（Enterprise pooled usage）、Fleet（workspace 级 spend）都做了「钱」的团队维度，但都绑定自家用量计量；「跨异构 agent 的统一预算/审批/沙箱策略」无人覆盖。
4. **时间窗证据**：多方正从不同方向逼近同一空间——Cursor（shared team context）、Devin（Outposts + Dynamic Workflows）、OpenHands（team-shared Agent Server）、Copilot（多 agent 控制面）、Fleet（审批 inbox）。说明「团队级 agent 协作」是公认方向；Orbital 的差异化必须落在「git 化项目状态 + 异构编排 + 团队审批/预算」的**组合**，而非任何单一功能点。

---

## 6. 来源列表（全部为官方来源）

| # | 来源 | URL | 抓取/标注日期 | 备注 |
|---|------|-----|--------------|------|
| 1 | Cursor 定价页 | https://cursor.com/pricing | 2026-09-01 | Teams/Enterprise 功能全文 |
| 2 | Cursor Changelog | https://cursor.com/changelog | 2026-09-01 | 最新条目 2026-08-27（Cloud Agents 免 SCM、Origin repo） |
| 3 | OpenClaw GitHub | https://github.com/openclaw/openclaw | 2026-09-01 | README 全文 |
| 4 | Devin 文档索引 | https://docs.devin.ai/llms.txt | 2026-09-01 | 全站页面索引（企业功能多数引于此，标「据文档索引」） |
| 5 | Devin 自助计划 | https://docs.devin.ai/admin/billing/self-serve.md | 2026-09-01 | Teams/共享 credits/seat 机制全文 |
| 6 | Devin 用量政策 | https://docs.devin.ai/enterprise/features/usage-policies.md | 2026-09-01（索引） | per-user ACU limits |
| 7 | Devin Outposts | https://docs.devin.ai/cloud/outposts/overview.md 及 orchestration.md | 2026-09-01（索引） | 自托管 worker/队列认领 |
| 8 | Devin CLI 企业控制 | https://docs.devin.ai/cli/enterprise/team-settings.md、controls.md、windsurf-auth.md | 2026-09-01（索引） | 含 Legacy Windsurf Auth（Windsurf 并入证据） |
| 9 | Factory 定价页 | https://factory.ai/pricing | 2026-09-01 | Teams/Business/Enterprise 全文 |
| 10 | Anthropic 定价页 | https://www.anthropic.com/pricing | 2026-09-01 | Team/Enterprise 功能、Claude Cowork/Code 归属 |
| 11 | LangSmith Fleet 对比页 | https://docs.langchain.com/langsmith/fleet/comparison.md | 2026-09-01 抓取；页面自注 2026-05-05 更新 | 五平台品类对比表 |
| 12 | LangChain 文档索引 | https://docs.langchain.com/llms.txt | 2026-09-01 | Fleet 章节结构、LangGraph Platform 并入、Deep Agents Code |
| 13 | OpenHands GitHub | https://github.com/All-Hands-AI/OpenHands | 2026-09-01 | Agent Canvas README（team-shared Agent Server） |
| 14 | Claude Agent SDK GitHub | https://github.com/anthropics/claude-agent-sdk | 2026-09-01 | Claude Code SDK 更名 |
| 15 | GitHub Copilot 功能页 | https://github.com/features/copilot | 2026-09-01 | 多 agent 控制面、Spaces、第三方 agent |
| 16 | Windsurf 定价页 | https://windsurf.com/pricing | 2026-09-01 | **抓取失败**（浏览器人机验证），细节未核实 |
| 17 | Devin Enterprise 计费 | https://docs.devin.ai/admin/billing/enterprise.md | 2026-09-01（索引） | org 与 per-user ACU limits |

### 未核实事项清单
- Windsurf 自身 Teams/Enterprise 计划与功能明细（官网拦截）。
- Cursor 具体版本号（changelog 页不展示版本号）。
- GitHub Copilot Business/Enterprise 计划功能明细（仅抓到个人计划与团队能力表述）。
- Devin 企业页细节均「据文档索引」（页面标题 + 官方一句话），未逐页通读。
- 搜索引擎关键词趋势扫描（multi-user AI agent collaboration / agent team workspace / shared agent memory）当日被 reCAPTCHA 拦截未执行——如需补全，建议另日重试或换用直接抓取厂商博客。
