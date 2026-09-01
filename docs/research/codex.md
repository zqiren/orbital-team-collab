# OpenAI Codex 产品现状盘点（截至 2026-09-01）

> 用途：为 Orbital Team Feature 规划提供竞品依据。本文所有信息均于 **2026-09-01 联网核实**，
> 优先官方来源（developers.openai.com、github.com/openai/codex）。查不到的标「未核实」，不做臆测。
> 来源列表见文末，正文以 [S1]–[S12] 标注。

---

## 0. 一句话定位

**Codex 是 OpenAI 的「全能 coding agent」：本地 CLI/IDE/桌面 app + 云端并行任务 + GitHub/Slack/Linear 集成，2026 年已从单机助手演进为带 subagent 编排、自动审批审查（Guardian）、企业治理（audit/RBAC）的个人效率工具——但编排单元仍是「一个人 × 多个 Codex 实例」，团队协作停留在 code review 与 admin 治理层，没有跨人、跨 CLI、跨项目的任务编排与共享项目状态。** [S1][S5][S7][S10]

---

## 1. 产品形态与定价

### 1.1 产品形态（四端 + 集成）

| 形态 | 现状 | 来源 |
|---|---|---|
| Codex CLI | 本地终端 agent，开源 Apache-2.0（github.com/openai/codex，120k stars）；安装：curl 脚本 / `npm i -g @openai/codex` / `brew install --cask codex`；最新版 **0.152.0**（releases 页最新，具体发布日期未核实） | [S3][S12] |
| IDE 扩展 | VS Code / Cursor / Windsurf 扩展 + Xcode、JetBrains 原生集成；可读打开的文件/选区作上下文；可从 IDE 一键把任务转交云端（"Continue in: Work locally / Cloud"） | [S3][S10] |
| 桌面 app（`codex app` / ChatGPT 桌面端） | 独立桌面应用；review pane、PR 上下文侧栏、Security workbench 等均以桌面 app 为载体 | [S3][S9][S6] |
| Codex Web / 云端任务 | chatgpt.com/codex：云端并行任务（cloud chats），从 Web/GitHub/GitLab/Linear/Slack 发起；隔离容器内运行 | [S3][S4] |
| GitHub 集成 | PR 内 `@codex` 委派任务、automatic PR reviews（计入独立 Code Review 用量桶） | [S2] |
| Slack / Linear / GitLab 集成 | Slack、Linear 为正式 cloud integration；**GitLab 支持 2026-08-17–21 那周进入 beta，面向所有 ChatGPT 计划** | [S2][S1] |
| Codex Security（衍生产品） | 应用安全 agent：插件/CLI/SDK（@openai/codex-security）+ 云端扫描（research preview），面向安全与工程团队 | [S6] |
| ChatGPT Work（新表面） | pricing 页明示 "ChatGPT Work and Codex share usage"（共用定价/credits/限额）；subagents 文档称 "ChatGPT Work and Codex can run subagent workflows"；即 ChatGPT 主产品的工作场景与 Codex 融合。产品细节未核实 | [S2][S7] |

### 1.2 定价与用量（官方 pricing 页，2026-09-01 抓取）

计划档位：**Free $0 / Go $8/mo / Plus $20/mo / Pro（5x $100 或 20x $200 /mo）/ Business / Enterprise / API key 按量**。[S2]

- **默认模型**：GPT-5.6 家族三档——**Sol**（主力）、**Terra**（快/省）、**Luna**（高速轻量）；另有 GPT-5.5 / GPT-5.4 / GPT-5.4-mini 旧档；Pro 独占 **GPT-5.3-Codex-Spark**（research preview）。[S2]
- ** cyber 变体**：Daybreak Blue / Daybreak Red（GPT-5.6 派生），需 **Trusted Access for Cyber** 审批才能用，Red 定价 312.5/31.25/1875（in/cached/out 每 1M tokens，credits 计）。[S2]
- **本地用量限额**（每 5 小时窗口，local messages，Plus / Pro5x / Pro20x / Business）：Sol 10–100 / 50–500 / 200–2,000 / 10–100；Terra 25–200 / 125–1,000 / 500–4,000 / 25–200；Luna 250–2,000 / 1,250–10,000 / 5,000–40,000 / 250–2,000。[S2]
- **credits 计费**：云端任务等消耗 credits；GPT-5.6 平均 5–30 credits/条消息；Sol 促销定价「至少持续到 2026-11-21」。[S2]
- **Code Review 独立计量**：GitHub 上跑的 review（@codex、自动 review）计入单独的 Code Review 用量，不占通用额度；本地 review 计入通用额度。[S2]
- **各计划 Codex 权益**（功能矩阵，Business/Enterprise 列部分单元格在抓取中无法精确对齐，存疑处标未核实）：
  - Codex cloud chats：Plus / Pro / Business ✓（Enterprise 列未核实）
  - AGENTS.md、Skills、Worktrees & Git 工具、沙箱/审批控制、SSH remote：全计划 ✓（含 API key 模式）
  - Subagents and custom agents：Plus / Pro / Business ✓
  - Plugins：全计划 ✓；**Plugin sharing（团队共享插件）：Business ✓**；plugin marketplaces 有 Installed / OpenAI Curated / **Workspace** / **Shared with me** 作用域 [S2][S5]
  - Memories：全计划 **Limited\***（有地域限制）
  - GitHub issue/PR 委派（@codex）、GitHub code review、Slack/Linear cloud integration：Plus / Pro / Business ✓
  - **requirements.toml 托管配置、云端配置策略（cloud-managed config policies）、SAML SSO/MFA/workspace 用户管理：Business ✓**
  - **workspace RBAC 与自定义角色、SCIM/EKM/域名验证、企业留存与数据驻留、Analytics dashboard、Analytics API、Compliance API & audit logs、Codex Security（连接 GitHub 仓库）：Enterprise ✓**
  - Sites：Business ✓（FAQ 称 eligible plans 公测期含 Sites；各档边界未逐格核实）
  - Mobile remote control：Plus / Pro / Business ✓（Enterprise 列未核实）
  - Free / Go 两档的 Codex 具体权益：**未核实**（pricing 页矩阵以 Plus 起列）。

---

## 2. 单机核心能力

### 2.1 记忆与上下文

- **AGENTS.md**：项目级指令文件；CLI 内 `/init` 生成；官方功能矩阵列为独立能力项（全计划可用）；支持仓库内分层嵌套（pricing 页 FAQ 提到 nesting AGENTS.md）。[S2][S5]
- **Session resume**：`codex resume` 重开最近会话，或跨本地 chats 搜索找回旧工作；SDK 侧 `resumeThread(threadId)`；0.152.0 修复了 resumed thread 恢复工作目录的问题。[S5][S8][S12]
- **Memories（跨会话记忆）**：功能矩阵存在，全计划但标 **Limited\***（地域限制）。细节（记忆共享、作用域）**未核实**。[S2]
- **Skills / Plugins**：可复用指令打包为 skills；plugins 连接外部工具（marketplace 1751 个可用，示例截图装了 GitHub/Gmail/Calendar/Drive 等）；插件目录支持 per-repo 配置合并（0.151.0）。[S5][S12]

### 2.2 沙箱与审批（官方 security 页，信息量最大的一页）

- **双层控制**：sandbox mode（技术上能做什么）+ approval policy（何时必须问人）。[S11]
- **沙箱实现**：macOS Seatbelt（sandbox-exec）、Linux bwrap+seccomp、Windows 原生沙箱或 WSL2（0.115 起 WSL1 不再支持）；可 `codex sandbox` 本地测试策略。[S11]
- **默认策略**：默认**关网络**、写权限限当前 workspace；git 仓库默认 Auto（workspace-write + on-request 审批），非 git 目录默认 read-only；`.git`、`.agents`、`.codex` 在可写根内强制只读。[S11]
- **审批档位**：untrusted / on-request / never / granular（细粒度：sandbox 升权、规则、MCP elicitation、request_permissions、skill 脚本分别设交互或自动拒绝）；`--dangerously-bypass-approvals-and-sandbox`（--yolo）全放开。[S11]
- **网络隔离**：network_proxy 域名 allowlist（精确/通配/deny 优先）、本地回环默认禁、DNS rebinding 防护、SOCKS5/Unix socket 细粒度控制。[S11]
- **Auto-review（Guardian）**：`approvals_reviewer = "auto_review"` 把符合条件的审批请求交给一个 **reviewer agent** 自动审（查数据外传、凭据探测、安全弱化、破坏性操作；低/中风险放行、关键风险拒绝、高风险需用户授权）；桌面 app 显示 Reviewing/Approved/Denied/Aborted/Timed out 状态；默认 reviewer policy 开源在 codex 仓库，**企业可用 guardian_policy_config 在托管配置里替换租户策略段**。releases 显示 Guardian 是 0.15x 系列的持续建设重点。[S11][S12]
- **云端两阶段运行时**：cloud 容器分 setup 阶段（可联网装依赖，secrets 仅此阶段可用）与 agent 阶段（默认离线）。[S11]
- **OTel 遥测**：默认关闭、opt-in；导出会话/审批决定/工具结果等结构化事件到企业自己的 collector，供审计合规。[S11]

### 2.3 SDK / 非交互模式

- `codex exec`：非交互模式，进 CI 流水线（旧的 `--full-auto` 已 deprecated 并告警）。[S11]
- **TypeScript SDK**（@openai/codex-sdk，Node 18+）与 **Python SDK**（openai-codex，3.10+，stable）：start/continue/resume 线程、按 turn 设 sandbox（read_only / workspace_write / full_access）；底层是 app-server JSON-RPC；定位「把 Codex 嵌进 CI/CD、自建 agent、内部工具」。[S8]
- `codex mcp-server` 已 deprecated（MCP server guide 保留给存量集成）。[S8]
- MCP：`codex mcp` 增删查 MCP server；0.152.0 支持 package 风格命名与 per-tool output_token_limit。[S5][S12]
- 其他单机能力：`codex --image` 带图、`codex --search` 联网搜索（默认 cached 索引，防 prompt injection）、`codex cloud` 从终端提交/取回云端任务、`codex completion` shell 补全、多仓库 review pane、Dev Containers 参考部署。[S5][S9][S11]

---

## 3. 多 agent 能力

### 3.1 本地 subagents（默认开启）

- **机制**：Codex 可把独立子任务并行派给 subagent，各自有 agent thread（可点开检查过程），完成后汇总回主线程；官方明确动机是对抗 context pollution / context rot。[S7]
- **触发**：直接要求（"spawn two agents"）或 AGENTS.md / skill 指令请求；0.15x 已有 "proactive multi-agent delegation"（模型目录驱动主动委派）。[S7][S12]
- **内置 agent**：`default`（通用兜底）、`worker`（执行向）、`explorer`（重读探索）。[S7]
- **自定义 agent**：TOML 文件放 `~/.codex/agents/`（个人）或 `.codex/agents/`（项目级）；必填 name/description/developer_instructions，可选 model、model_reasoning_effort、sandbox_mode、mcp_servers、skills.config；例：pr_explorer（read-only + gpt-5.3-codex-spark）+ reviewer（gpt-5.6-terra high effort）+ docs-researcher（挂 docs MCP）。[S7]
- **编排控制**：`[agents]` 配置：enabled、max_concurrent_threads_per_session、default_subagent_model、default_subagent_reasoning_effort、interrupt_message；**编排由 Codex 自己做**（spawn、路由追问、等待、收线）。[S7]
- **边界**：subagents 继承父会话 sandbox/permission；可对单个自定义 agent 覆盖（如 read-only）。官方建议并行只读任务放心用，**并行写代码要谨慎**（冲突与协调成本）。[S7]
- **成本**：每个 subagent 独立消耗 model/tool tokens；0.151.0 起「nested subagent token usage 计入 root goal 预算」——存在 goal 级 token 预算概念，但公开文档未见跨会话/跨项目的预算管理界面（未核实）。[S7][S12]

### 3.2 云端并行任务

- cloud chats 可并行跑多个任务，各自在隔离容器；从 Web / GitHub / GitLab / Linear / Slack 发起；任务完成后可 review 摘要/diff、追问、一键开 PR。[S4]
- **环境（Environments）**：每个任务绑定一个环境（依赖、工具、env vars、secrets），环境配置有 **Sharing: Workspace** 列——即可共享给整个 ChatGPT workspace（团队级复用，创建人标注）。[S4]
- 终端与云打通：`codex cloud` 浏览/提交/apply 到本地仓库。[S5]

### 3.3 能力边界（worker 是谁？上下文能否复用？）

- **worker 只能是 Codex 系**：subagent 是「Codex 会话的配置层」（换模型/换指令/换沙箱），不是异构 agent；官方文档无任何接入第三方 CLI（Claude Code / Gemini CLI 等）作为 worker 的能力。SDK 能"build your own agent"，但那是把 Codex 嵌入自研工具，不是多 CLI 编排。[S7][S8]
- **跨 session 复用**：会话级 resume / SDK resumeThread / AGENTS.md（项目级静态指令）/ Memories（Limited，细节未核实）。没有看到「团队共享的可执行项目状态」概念。[S5][S8][S2]
- **跨项目编排**：未发现。编排范围 = 单会话（max_concurrent_threads_per_session）；云环境按仓库配置。管理一个 agent 跨多个 repo/项目调度任务的机制未见于文档（未核实，倾向无）。[S7][S4]
- ChatGPT Work 侧也能跑 subagent workflows（ChatGPT 与 Codex 融合的编排表面），细节未核实。[S7]

---

## 4. 团队协作现状（Team/Business/Enterprise）

| 能力 | 状态 | 证据 |
|---|---|---|
| 共享云端环境 | **有**：Environments 配置 Sharing: Workspace，团队共用同一套任务运行环境（deps/tools/secrets） | [S4] |
| 共享插件 | **有**：Plugin sharing（Business ✓），plugin marketplace 有 Workspace / Shared with me 作用域 | [S2][S5] |
| Code review 流程 | **有，且是主打团队功能**：@codex PR 委派、automatic PR reviews（独立用量桶）、本地 review pane、PR 反馈侧栏、Security Review（PR 级安全深审） | [S2][S9][S6] |
| Admin 管理 | **Business**：SAML SSO、MFA、workspace 用户管理、requirements.toml 托管配置、云端配置策略（统一管控沙箱/审批/网络/工具） | [S2][S11] |
| 企业治理 | **Enterprise**：workspace RBAC 与自定义角色、SCIM/EKM/域名验证、留存与驻留、Analytics dashboard、Analytics API、**Compliance API & audit logs**、Codex Security 扫描连接仓库 | [S2] |
| 审计 | 本地：OTel 自建 collector 审计遥测（默认关）；云端/组织级：Enterprise audit logs + Compliance API | [S11][S2] |
| 团队共享记忆 | **无**：AGENTS.md 是 repo 内文件（随 git 共享，但属项目配置而非 agent 记忆）；Memories 为个人维度（Limited\*），无团队级记忆/决策库证据 | [S2] |
| 共享任务队列 | **无直接对应物**：cloud chats 是个人任务列表（chats/reviews/security/archive 分区）；Linear/Slack/GitHub 集成=从工作系统拉事件建任务，而非团队内分配/认领/审批流转 | [S4] |
| 手机监督 | **有**：Mobile remote control（Plus/Pro/Business ✓）——移动端远程控制 Codex 任务 | [S2] |
| 用量/预算管理 | 账户级：credits、5 小时窗口限额、Code Review 独立桶、rate-limit banner（0.152.0）；**团队/子团队/项目级预算分配：未核实（倾向无公开功能）** | [S2][S12] |

---

## 5. 团队场景空白（每条附证据）

1. **异构 worker 编排缺失**：团队想「Claude Code 干 X、Gemini CLI 干 Y、Codex 干 Z」——Codex subagents 只能 spawn Codex 自身（配置层=模型+指令+沙箱），文档无第三方 CLI worker 概念。证据：[S7]（custom agent = config layer，builtin default/worker/explorer 均为 Codex）。
2. **无共享项目状态 / 决策库**：多人在同一项目上使用 Codex，上下文同步靠 git 里的 AGENTS.md + 各自本地 chats；无「项目级、跨人、跨会话的结构化状态文件」（对标 PROJECT_STATE/DECISIONS 类机制）。证据：[S5]（resume 是个人本地 chats 搜索）、[S2]（Memories 个人 Limited）。
3. **无跨人审批流转**：审批策略是单用户会话内的（untrusted/on-request/never/granular + auto_review 自动审）；没有「A 的 agent 触发高危操作 → 路由给 B/C 审批」的团队工作流。证据：[S11]（approvals 全部面向 "you"）。
4. **无跨项目/跨仓库的编排层**：cloud 环境按 repo 配置，subagent 并发上限挂在单个 session；一个管理者 agent 统筹多 repo/多项目任务队列的机制未见。证据：[S4][S7]。
5. **团队用量/预算管理粗粒度**：限额与 credits 都是账户/计划级；未见按团队、项目或任务类型分配预算、设 cap、超限审批的管理面。证据：[S2]（用量表与 rate card 均按计划档）。goal 级 token 预算仅存在于单次运行内部（[S12] #41183）。
6. **治理深度压在 Enterprise 档**：audit logs、Analytics API、RBAC 自定义角色全在 Enterprise；Business 只有 SSO/用户管理/托管配置。中小团队（如 20 人 startup）拿不到审计与合规 API。证据：[S2] 功能矩阵。
7. **编排只在「任务内」不在「流程上」**：@codex/自动 review 覆盖了 PR 流程，但从「需求 → 任务拆分 → 指派 → 执行 → 审批 → 合入」的端到端团队流程没有产品化承载（Linear/Slack 集成只是事件入口，不是流程引擎）。证据：[S4]（集成定位为发起任务的渠道）。
8. **本地执行与云端治理割裂**：OTel/托管配置面向企业自建 collector；普通团队对「多台机器上跑的本地 Codex 实例」没有统一监控/暂停/干预面（Mobile remote control 针对云端任务；本地多机编排未见）。证据：[S2][S11]。

---

## 6. 对 Orbital 的启示

1. **Codex 正快速吃掉「单机编排」叙事**：subagents 默认开启 + proactive delegation + Guardian 自动审批 + goal 级 token 预算——Orbital 在单机单项目维度的差异空间正被挤压；Orbital 的答辩重心应放在 **Codex 结构性不做的事**（见第 5 节），而非单点功能对比。
2. **异构 worker 是最硬的差异**：Codex 只能编排 Codex；Orbital 的管理 agent 可调度 Claude Code/Codex/Gemini CLI/Cursor 任意 CLI worker——这是现有文档层面 Codex 完全没有的能力，且是「项目级编排」的自然延伸。
3. **「共享项目状态」是真空地带**：Codex 的团队故事 = 共享环境 + 共享插件 + code review；Orbital 的 story = 共享的**项目状态文件**（PROJECT_STATE/DECISIONS/queue.json 天然 git 化，多 agent 多人可读写）。两者不重叠，可直接作为 PRD 支柱。
4. **审批要打「跨人流转」**：Codex 把审批做成单用户会话内交互（外加自动审）；Orbital 的审批队列可定位为团队级风险控制面（路由、代办、预算门）。
5. **警惕 Mobile remote control**：Codex 已有移动端远程控制（Plus/Pro/Business），Orbital 的「手机监督」卖点需精确表述为「对多 worker 队列与审批的监督」而非「远程看 agent」本身。
6. **定价参照系**：Plus $20 已含 cloud tasks + subagents + @codex review；Orbital 若做团队功能，Business 档（SSO + 托管配置 + 共享插件）是 Codex 团队能力的基准线，audit/RBAC 是 Enterprise 护城河——Orbital 的机会是用「本地优先 + git 化状态」把治理能力下放到普通团队。
7. **注意 ChatGPT Work 融合趋势**：Codex 用量与 ChatGPT Work 合并计费、subagent workflows 互通、Gmail/Slack/GitHub 事件触发定时任务——OpenAI 在把 agent 编排并入 ChatGPT 主入口；Orbital 的差异化必须依赖 IDE/CLI 之外的位置（项目管理层），而不是做一个「更好的 Codex」。

---

## 7. 来源列表（均于 2026-09-01 抓取）

| # | URL | 内容 | 抓取日期 |
|---|---|---|---|
| S1 | https://developers.openai.com/codex | Codex 总览 + What's new（2026-08-24~28、08-17~21 条目：浏览器支持扩展、app events 定时任务、GitLab beta） | 2026-09-01 |
| S2 | https://developers.openai.com/codex/pricing | 计划/限额/credits/功能矩阵/FAQ | 2026-09-01 |
| S3 | https://github.com/openai/codex | README：CLI/IDE/app/Web 四端、安装、登录方式、License | 2026-09-01 |
| S4 | https://developers.openai.com/codex/cloud | cloud tasks、environments（Sharing: Workspace）、集成入口 | 2026-09-01 |
| S5 | https://developers.openai.com/codex/cli | CLI 功能全景（v0.143.0 截图、skills/plugins、subagents、codex cloud/mcp） | 2026-09-01 |
| S6 | https://developers.openai.com/codex/security | Codex Security（插件/CLI/SDK/云扫描/Trusted Access for Cyber） | 2026-09-01 |
| S7 | https://developers.openai.com/codex/subagents | subagent workflows、内置/自定义 agent、[agents] 配置、编排与边界 | 2026-09-01 |
| S8 | https://developers.openai.com/codex/sdk | TypeScript/Python SDK、app-server、sandbox presets、mcp-server deprecated | 2026-09-01 |
| S9 | https://developers.openai.com/codex/code-review | 本地 review pane、多仓库 review、PR 上下文、inline comments | 2026-09-01 |
| S10 | https://developers.openai.com/codex/ide | IDE 扩展（VS Code/Cursor/Windsurf/Xcode/JetBrains）、本地/云端切换 | 2026-09-01 |
| S11 | https://developers.openai.com/codex/sandbox | 沙箱实现、审批档位、network_proxy、Auto-review(Guardian)、OTel、Managed configuration | 2026-09-01 |
| S12 | https://github.com/openai/codex/releases | 0.152.0 / 0.151.0 release notes（Guardian、subagent token budget、plugin catalogs 等）；具体发布日期未核实 | 2026-09-01 |

**未核实清单**（诚实边界）：各 release 具体发布日期；Free/Go 档 Codex 权益明细；Enterprise 档部分功能矩阵单元格；Memories 功能细节与团队共享性；ChatGPT Work 产品细节；跨项目编排是否存在（倾向无，未见即记「未见」）；goal 级 token 预算的管理界面。
