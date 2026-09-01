# Claude Code 产品现状盘点(截至 2026-09)

> 研究方法:官方一手来源联网核实(抓取日期均为 2026-09-01),包括 code.claude.com 文档站、anthropic.com 定价页、GitHub anthropics/claude-code README 与 CHANGELOG。逐条标注来源;查不到的标「未核实」,不做臆测。抓取时 CHANGELOG 最新版本为 v2.1.252。

## 一句话定位

Claude Code 是 Anthropic 的 agentic coding 工具:以 terminal CLI 为核心、向 IDE/Desktop/Web/Mobile/Slack/GitHub 多端铺开的**单人多 session 编码 agent**,企业侧提供 SSO/审计/成本管控等「IT 采购友好」功能,但产品使用单元仍是「1 个人 + N 个自己的 session」,不含多人共享的项目级 agent 编排。(来源:code.claude.com/docs/en/overview、code.claude.com/pricing,2026-09-01)

## 产品形态与定价

### 形态(全部已核实,来源 docs/en/overview + code.claude.com/pricing,2026-09-01)

| Surface | 状态 | 说明 |
|---|---|---|
| Terminal CLI | GA,主力形态 | native install(`curl claude.ai/install.sh`);**npm 安装已 deprecated**;macOS/Linux/Windows/WSL;支持 Bedrock/Vertex/Foundry/Claude Platform on AWS 等第三方 provider 与自定义 ANTHROPIC_BASE_URL gateway |
| IDE 扩展 | GA | VS Code、JetBrains 官方扩展;官网还提及 Cursor、Devin Desktop 可接入 |
| Desktop app | GA | Pro/Max/Team/Enterprise 可用;含 scheduled tasks、computer use(可操作本机 App/浏览器) |
| Web | GA | Claude Code on the web(云 session);配合 GitHub 连接(/web-setup);cloud session 同样出现在 desktop/mobile app 中 |
| Mobile | GA | Claude iOS/Android app 可继续/发起 cloud session;Remote Control 支持手机监督本地 session |
| GitHub / GitLab | GA | @claude on GitHub、GitHub Actions、GitLab CI/CD、GitHub Code Review bot、/install-github-app |
| Slack | GA | 从 Slack 路由 bug 报告到 PR |
| Chrome | GA(research 演进中) | Claude in Chrome 浏览器操作,走 Claude Code 权限检查 |
| Agent SDK | GA | 以 SDK 形式把 Claude Code 嵌入自建 agent 工作流 |

同一引擎跨端:CLAUDE.md、settings、MCP servers 在所有 surface 通用(来源:docs/en/overview,2026-09-01)。

配套机制:Remote Control(手机接 管 本地 session)、Channels(Telegram/Discord/iMessage/webhook 事件注入 session)、Routines(定时/API/事件触发例程,v2026-04-14 博客)、`claude --cloud`(本地任务转云端续跑)。

### 定价(来源:anthropic.com/pricing + code.claude.com/pricing,2026-09-01 抓取)

| 档位 | 价格 | Claude Code 可用性 |
|---|---|---|
| Free | $0 | 不含 |
| Pro | $17/月(年付 $200 一次付)或 $20/月 | 含,适合「short coding sprints in small codebases」 |
| Max 5x | $100/月 | 含 |
| Max 20x | $200/月 | 含 |
| Team | **每 seat 价格未核实**(2026-09-01 抓取的 pricing 页未展示具体数字,官网 FAQ 有「Team or Enterprise plan premium seat」表述) | 需 premium seat |
| Enterprise | 定制价,**未核实** | premium seat;也支持 Console/API 按 token 计费 |

其他已核实定价事实:
- Console/API 账号:按标准 API token 计价(来源:code.claude.com/pricing FAQ,2026-09-01)。
- Fast mode(Opus 5 高速档):$10/$50 per Mtok,research preview(来源:code.claude.com/pricing FAQ)。
- Sonnet 5 标准 list price:$2/$10 per Mtok(来源:CHANGELOG v2.1.243 更新说明)。
- 数据驻留 workspace:推理加收 1.1× premium(来源:CHANGELOG v2.1.239)。
- seat-based Enterprise 订阅默认模型为 Opus 5(来源:CHANGELOG v2.1.252)。
- 1M 上下文窗口档位存在(Opus,「1M context」提示与 auto-compact 阈值条目,CHANGELOG v2.1.252/v2.1.243)。

## 单机核心能力

### 记忆体系(来源:code.claude.com/docs/en/memory,2026-09-01)

- **CLAUDE.md** 四级 scope:managed policy(`/Library/Application Support/ClaudeCode/CLAUDE.md` 等,组织级、用户不可排除)、user(`~/.claude/CLAUDE.md`)、project(`./CLAUDE.md`,git 共享)、local(`CLAUDE.local.md`,gitignore)。支持 `@path` import(最深 4 跳)、`.claude/rules/` 目录(可用 frontmatter `paths:` 做路径 scoped 规则)、`claudeMdExcludes` 排除 monorepo 里别的团队的文件、managed settings 里 `claudeMd` key 直接内联组织级指令。
- **Auto memory**(默认开启):Claude 自己写的跨 session 笔记,分 user/feedback/project/reference 四类;存储在 `~/.claude/projects/<project>/memory/`(MEMORY.md 索引 + topic 文件,索引只加载前 200 行/25KB);同一 git repo 的所有 worktree 共享;**明确标注 machine-local,不跨机器、不跨云端环境共享**。
- 兼容:CLAUDE.md 可 `@AGENTS.md` 导入;`/import` 命令(v2.1.213+)可从 Cursor、Copilot、Devin、Windsurf、Cline 等迁移指令与配置。

### Hooks、MCP、Skills(来源:docs/en/memory、docs/en/sub-agents、CHANGELOG,2026-09-01)

- Hooks 事件:PreToolUse/PostToolUse/Stop/SessionStart/SubagentStart/SubagentStop/Notification/InstructionsLoaded,新增 PreModelSwitch/PostModelSwitch(v2.1.251);组织可用 managed settings 强制。
- MCP:`.mcp.json` 项目配置;subagent frontmatter 可内联专属 MCP server;企业侧有 allowedMcpServers/deniedMcpServers 策略与 managed MCP;支持 stdio/http/sse/ws 与远程 OAuth。
- Skills:SKILL.md 格式,可被 subagent frontmatter `skills:` 预载,可组织级部署(pricing 表「Organization wide skills deployment」行);plugin marketplace 支持管理员统一安装(changelog v2.1.246 telemetry 条目)。

### Subagents(来源:code.claude.com/docs/en/sub-agents,2026-09-01)

- 每个subagent独立 context window + 自定义 system prompt + 工具白/黑名单 + 独立 permission mode;结果摘要返回主对话。
- 定义文件(Markdown + YAML frontmatter)五级优先:managed settings(组织级)> `--agents` CLI flag > `.claude/agents/`(项目,git 共享)> `~/.claude/agents/`(个人)> plugin。字段含 tools/disallowedTools/model/permissionMode/maxTurns/skills/mcpServers/hooks/**memory**(user/project/local 三档持久记忆)/background/effort/isolation: worktree 等。
- Built-in:Explore(只读检索)、Plan、General-purpose;Explore 自 v2.1.198 继承主对话模型(cap Opus)。
- 默认后台运行;`isolation: worktree` 给 subagent 独立 git worktree(带防逃逸检查)。
- Task tool 已更名 Agent tool(v2.1.63),主线程可用 `claude --agent <name>` 把整个 session 变成某 subagent 角色。

### CI/CD 与自动化(来源:docs/en/overview + CHANGELOG,2026-09-01)

- GitHub Actions / GitLab CI/CD 自动化 PR 评审与 issue triage;GitHub Code Review 提供「每个 PR 自动评审」;`/ultrareview` 云端深度评审;self-hosted runner 支持企业自托管执行环境。
- headless/SDK:`-p` 非交互模式、`--input-format stream-json`、Agent SDK、`--restricted` 受限模式(v2.1.248:去命令执行工具、锁死文件工具在工作目录内、拒绝 bypassPermissions)。
- Workflow tool + dynamic workflows(官方博客 2026-05-28):单任务编排数十至上百个并行 subagent 并自检结果。
- Routines(/loop 等,官方博客 2026-04-14):定时/API/事件触发长跑任务,`/usage` 有 Loops breakdown。
- 其他值得记录的近期能力:Agent view(2026-05-11 博客,「管理你所有 session 的一个界面」)、computer use(2026-03-23 博客)、auto mode(分类器自动放行工具调用)、sandbox、/fork(复制对话分支)、git worktree 并行、/teleport(session 迁移)。

## 多 agent 能力与边界

Claude Code 的多 agent 光谱(由轻到重,来源:docs/en/sub-agents + docs/en/agent-teams,2026-09-01):

1. **Subagents**:单 session 内委派,结果返回主对话,token 成本低。
2. **Fork**:复制当前对话上下文开新分支(subagent 唯一能继承父对话历史的形态)。
3. **Background agents / sessions**:多个独立 session 并行,`claude agents` 面板统一查看(2026-05-11 Agent view 博客)。
4. **Cross-session messaging**(SendMessage/ListAgents):**同一台机器**上的 session 互发消息,socket 收件箱,v2.1.248 起覆盖 Bedrock/Vertex/Foundry。
5. **Agent teams**(实验性,默认关闭,需 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`):lead session + N 个 teammate(各自完整 Claude Code 实例),共享 task list(pending/in progress/completed + 依赖)+ mailbox(`~/.claude/teams/{team}/inboxes/{agent}.json`,本地 JSON 文件);支持 in-process 或 tmux/iTerm2 split panes;hooks 有 TeammateIdle/TaskCreated/TaskCompleted。
6. **Dynamic workflows**:Workflow tool 大规模并行 subagent 编排。

**能力边界(逐条已核实):**

- **Worker 只能 Claude 系模型**:subagent/teammate 的 model 字段只接受 sonnet/opus/haiku/fable/claude-* 或 inherit(sub-agents 文档「Choose a model」);CLI 本体虽支持 Bedrock/Vertex/Foundry,但那只是 Claude 模型的不同托管渠道,不是异构 agent——**不能把 Codex/Gemini CLI/Cursor 的 agent 当 worker 调度**(docs/overview 的「third-party providers」指的是 API 供应商,不是别家 agent)。
- **上下文复用靠文件不靠 session**:teammate 不继承 lead 对话历史,只加载 CLAUDE.md/MCP/skills + spawn prompt(agent-teams 文档「Context and communication」);跨 session 知识沉淀靠 CLAUDE.md、auto memory(machine-local)与 subagent memory 三档目录;没有「把 session A 的对话状态交接给 session B」的机制。
- **Agent teams 硬限制**(agent-teams 文档「Limitations」):in-process teammates 无法 /resume;**one team per session**(不能跨 session 复用一个 team);**no nested teams**(teammate 不能再 spawn teammate);lead 固定不可转移;in-process teammate 的 subagent 不能后台;`-p`/SDK 非交互模式不能组队。
- **一切编排状态是本机临时文件**:team config 在 session 结束即删除,task list 「persists locally and is never uploaded」,且「There is no project-level equivalent of the team config」——没有项目级、更没有团队级的持久编排层。

## 团队协作现状(Team/Enterprise 计划)

已核实能力(来源:anthropic.com/pricing Team & Enterprise 对比表 + CHANGELOG,2026-09-01):

- **身份与管理**:SSO + domain capture、SCIM、role-based access、central billing & administration、Enterprise desktop app 批量部署。
- **审计与合规**:audit logs、usage analytics、compliance API、HIPAA-ready、custom data retention controls。
- **成本管控**:user 与 org 两级 spend controls(pricing 表);Enterprise `modelPricing` managed setting 可用合同价计算成本(v2.1.243);`/usage-credits` 让成员向 admin 申请提高用量上限(v2.1.248,AWS Marketplace 计费企业同样适用);spend limit bar 在 /usage 展示(v2.1.251)。
- **集中配置**:managed settings(强制登录方式、permissions.deny、sandbox、MCP 策略、availableModels 白名单、organization-wide CLAUDE.md、组织级 subagent、org-wide skills deployment、管理员代装 plugin)。
- **云端 session**:Claude Code on the web / desktop / mobile 的 cloud session;企业可 self-hosted runner 自托管执行环境;`claude --cloud` 本地任务上云。
- **代码评审 bot**:GitHub Code Review、/ultrareview、GitHub Actions / GitLab CI 集成。
- **共享记忆/上下文**:**无团队共享的 agent 记忆**——auto memory 明确 machine-local;团队共享上下文唯一途径是 git 里的 CLAUDE.md/.claude/rules/ 与组织级 managed CLAUDE.md(手写指令,非 agent 积累)。claude.ai 的「Project sharing and collaboration」行在 pricing 对比表中存在,但各档位勾选值未在抓取文本中显示,**未核实**。

## 团队场景空白(附证据)

以下每条都是 Claude Code 2026-09 现状中**未被覆盖**的「多人协作使用 agent」需求:

1. **团队共享的 agent 记忆 / 项目状态不存在**。证据:memory 文档原文「Auto memory is machine-local. All worktrees and subdirectories within the same git repository share one auto memory directory. **Files are not shared across machines or cloud environments.**」(code.claude.com/docs/en/memory,2026-09-01)。张三的 agent 在项目里积累的踩坑与决策,李四的 agent 永远看不到,只能靠人肉把结论写进 CLAUDE.md。
2. **无跨人、跨 session 的持久任务队列**。证据:agent-teams 文档「Teams and tasks are stored locally under a session-derived name」「The task list directory persists locally and **is never uploaded**」「**There is no project-level equivalent of the team config**」(code.claude.com/docs/en/agent-teams,2026-09-01)。任务编排状态跟随单次 session 生灭,无法把「待办队列」交给同事或第二天继续。
3. **编排是单机粒度,cross-session messaging 限于同一台机器**。证据:CHANGELOG v2.1.248「cross-session messaging (SendMessage / ListAgents) between sessions **on the same machine**」;agent-teams Limitations「One team per session」「No nested teams」(2026-09-01)。两个团队成员的 agent 之间没有任何通信信道。
4. **worker 不能异构**。证据:sub-agents 文档 model 字段仅接受 Claude 模型别名/ID(sonnet/opus/haiku/fable/claude-*)(code.claude.com/docs/en/sub-agents,2026-09-01)。一个项目里同时调度 Claude Code + Codex + Gemini CLI 分工(不同模型不同强项/成本)在 Claude Code 体系内无法表达。
5. **审批流面向操作者本人,没有「他人审批」工作流**。证据:sub-agents 文档「Permission prompts are passed through to you」;agent-teams「Teammate permission prompts appear in the lead session」(2026-09-01)。权限审批始终弹给跑 agent 的那个人;无法把高危操作路由给项目负责人审批。Remote Control 只是**本人**用手机接管,**未核实**存在任何代理审批机制。
6. **成本管控是 org/user 粒度,无 project/task 级预算**。证据:pricing 表 spend controls 仅「User and organizational level」;CHANGELOG 中 spend limit、modelPricing、usage-credits 均为 org/账号层(2026-09-01)。没有「给某个任务池分配 $50、超了自动暂停并请示」的预算编排。
7. **无团队级 agent 运行视图**。证据:Agent view 官方描述是「One place to manage **all your** Claude Code sessions」(code.claude.com/pricing,2026-05-11 博客摘要)——单人视角;企业有 usage analytics(消费分析)但**未核实**存在「团队谁在跑什么 agent、进度如何」的编排 dashboard。

## 对 Orbital 的启示

1. **Claude Code 的「团队功能」= 企业 IT 功能,不是协作功能**。SSO/审计/成本/集中配置解决「公司如何安全地把工具发给员工」,不改变使用单元是「1 人 + N session」。Orbital Team Feature 应卡位后者:「一个项目的多个人 + 多个 agent 如何共享状态、分工、互相监督」——这正是 Claude Code 结构性缺失的一层(空白 1/2/3)。
2. **异构 worker 是 Anthropic 商业上不会做的事**。Claude Code 只能调度 Claude 模型(空白 4);Orbital「任意 CLI agent(Claude Code/Codex/Gemini CLI/Cursor)当 worker」是真实的、对手难以跟进的差异化。
3. **「本地纯文本状态」路线已被对方间接验证**:Claude Code 的 mailbox/task list/team config 全是本地 JSON/markdown 文件,但被锁在 `~/.claude/` 且 session 生灭、never uploaded——他们到了文件化这一步却没走 git 化/项目化。Orbital 把 PROJECT_STATE/DECISIONS/LESSONS/queue.json 放进项目目录、天然 git 化,等于把 Claude Code 自己验证过的形态补上「持久 + 共享 + 可版本化」三块。
4. **审批与预算是可产品化的差异点**:Claude Code 有 permission prompt(单 session)与 org spend cap(粗粒度),但没有审批队列与任务级预算(空白 5/6)。Orbital 已有审批 + 预算机制,应包装成「团队 agent 治理」而非单机安全设置。
5. **写作业时的攻防预演**:面试官可能问「Anthropic 迭代很快,agent teams 不是已经在做多 agent 了?」——回答:agent teams 是单 session 内的临时编排(实验性、no resume、one team per session、never uploaded),它解决「一个人的任务并行」,不解决「一个团队的 agent 协作」;Orbital 的差异在持久层(项目状态 git 化)与治理层(审批/预算/异构调度),这两个维度在 Claude Code 2026-09 的公开能力中有明确证据空白。

## 来源列表

| # | 来源 | URL | 抓取日期 |
|---|---|---|---|
| 1 | Claude Code 文档总览(产品形态、surface、集成矩阵) | https://code.claude.com/docs/en/overview | 2026-09-01 |
| 2 | Anthropic 定价页(个人档价格、Team & Enterprise 功能表) | https://www.anthropic.com/pricing | 2026-09-01 |
| 3 | Claude Code 官网产品/定价页(Individual 档价格、FAQ、新功能时间线) | https://code.claude.com/pricing | 2026-09-01 |
| 4 | anthropics/claude-code README(定位、安装、plugins) | https://github.com/anthropics/claude-code | 2026-09-01 |
| 5 | CHANGELOG(v2.1.239–v2.1.252:cross-session messaging、usage-credits、modelPricing、cloud sessions、agent teams 修复等) | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md | 2026-09-01 |
| 6 | Subagents 文档(机制、scope、model 边界、memory 字段) | https://code.claude.com/docs/en/sub-agents | 2026-09-01 |
| 7 | Memory 文档(CLAUDE.md 四级 scope、auto memory machine-local) | https://code.claude.com/docs/en/memory | 2026-09-01 |
| 8 | Agent teams 文档(实验性、架构、限制) | https://code.claude.com/docs/en/agent-teams | 2026-09-01 |

未核实项汇总:Team 计划每 seat 具体价格;Enterprise 具体定价;claude.ai「Project sharing and collaboration」各档位归属;是否存在代理审批(他人代批)机制;是否存在团队级 agent 运行 dashboard。
