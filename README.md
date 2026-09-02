# Orbital Team Workspace（Team Collab 本地 Demo）

> 让每个 agent 的上下文，沉淀成团队可复用的资产。
> 把“一个人与一个 coding agent 的 session”升级为“一个团队与多个异构 agent 共同维护的 Project”。

## 📌 主要产物 / Primary Deliverable

**评估请从这里开始：[Team Collab 设计书（`DESIGN.html`）](./DESIGN.html)** —— 设计理念、为什么必须是专职
management agent、概念模型与系统架构、本地 demo 与云端生产形态、现状校准表与路线图，全部在这一份文档里。

GitHub 不直接渲染 HTML：可[在线预览](https://htmlpreview.github.io/?https://github.com/zqiren/orbital-team-collab/blob/main/DESIGN.html)，
或 clone 后用浏览器直接打开 `DESIGN.html`。本仓库是该设计的**本地可运行 demo**（生产形态为云端团队空间 +
云端 management agent，见设计书第 07 节）。

## 它解决什么问题

团队里同时运行着许多 agent 会话：调研、需求、产出各自锁在隔离的会话与存储里，团队只能靠开会、
写文档做人肉对齐——**agent 做过的调研没人能复用，团队已有的结论 agent 也看不见。**

Wiki / Notion / Obsidian 式知识库救不了它：没有人对知识的「活性」负全责，也没有一条让知识自动生长的
路径，堆到最后就是一座过期页面的坟场。

Team Collab 的答案是三句话（详见设计书）：

1. **团队上下文是最重要的资产** —— 它长在项目文件夹里、进 Git 版本管理，不属于任何一个 agent 会话。
2. **Agent 只是智能插件** —— Claude Code、Codex 或任何 CLI agent，装上插件即可接入项目空间，共享同一份记忆。
3. **Management agent 是上下文的维护者** —— 唯一的合并者与知识编译者：把讨论沉淀为代办与知识、守卫式
   合并成员产出、每次 merge 后替换过期事实而非追加流水账。竞态、always-on 收集、触发稳定性
   （不赌成员 agent 的 prompt 遵守、不赌长任务后的 context rot）、权限管控——四个理由决定了这必须是
   专职角色，而不是让成员 agent「顺手」维护。

项目内的上下文分四类闭环流转：**讨论**（IM 原始材料 → 收件箱分诊）→ **代办**（团队任务池）→
成员执行与报告 → 守卫合并 → **知识**（现状 / 决策 / 经验 / 索引，反哺下一个任务）；**开放问题**
是旁路——阻塞在需要人类判断的地方，回答后自动解锁。

## 实现方式：插件 + 钩子 + 本地 server

整个 demo 由三块拼成，没有数据库、没有 Node 构建链、没有云端依赖：

**① 成员侧 —— Claude Code / Codex 插件与钩子。** 从面板设置页复制一条接入消息贴进任意 agent 会话，
agent 会自动建 worktree、绑定成员身份并安装插件：Claude Code 获得项目级 `/team
claim|start|report|block|status|questions|manager` 指令集，外加一个 **SessionStart hook**——每次会话
启动（含 resume/clear/compact）自动注入身份、在办任务与待答问题，断线重开不丢上下文；Codex 与其他
agent 走等价的中立 CLI（`teamctl` / dispatcher）。身份永远来自 worktree 绑定，协议在文件与命令层，
不在某家 agent 里。

**② 管理侧 —— 事件驱动的无头 management agent。** `teamd` 守护进程监听事件日志：报告一提交就转为
集成任务，并按 runner 清单唤起 headless `claude -p` 或 `codex exec`（复用本机已有 CLI 登录；system
prompt 与工具面由清单统一下发）。Management agent 审阅 → 守卫合并 / 退回 / 阻塞提问 → 把合并结果
编译进团队记忆，全程只能走受控命令，全文件知识提案带基线哈希校验。守护进程随项目创建自动启动，
面板可一键启停，也可切回 manual 模式由人粘贴管理消息驾驶。

**③ 面板 —— 本地回环 server。** `teamctl dashboard` 用 Python 标准库起一个仅监听 `127.0.0.1` 的
HTTP server，前端是三个零依赖静态文件。所有页面都是文件运行时的实时投影（每次请求重建，无第二套
状态机），写操作限定在受控命令白名单，请求来源经 Host/Origin 校验，运行日志永不离开本机。

**存储：两层文件模型。** Git 保存低频、可审查、随 clone 传播的 durable knowledge
（`orbital/PROJECT_STATE.md`、`DECISIONS.md`、`LESSONS.md`、`INDEX.md` 与工作产物）；
`<git-common-dir>/orbital-team/` 保存高频、本机、可恢复的协作状态（任务、问题、收件箱、报告、
事件、运行记录），同一仓库的所有 worktree 天然共享。

```text
Member worktrees                    Canonical workspace
Alice ─ claim/start ─ commit ─┐     ┌─ code + orbital/{STATE,DECISIONS,...}
                              ├─────┤
Bob   ─ claim/start ─ commit ─┘     └──────────────▲──────────────────────
             │ Report                              │ controlled merge/commit
             ▼                                     │
┌─────────────────────────────────────────────────────────────────────────┐
│ file-native local runtime in <git-common-dir>/orbital-team/             │
│ Tasks · Potential Tasks · Questions · Reports · Events · Jobs · Runs    │
└───────────────┬───────────────────────────────┬─────────────────────────┘
                │ report.submitted              │ read projection
                ▼                               ▼
        teamd → ManagerRunner              loopback Dashboard
                │
                └─ integration.merged → knowledge.applied
                                      → integration.completed
```

## 怎么用

前置条件：Git、Python 3.11+；如需无头 management agent，本机装好并登录过 `claude` 或 `codex` CLI
（一次登录，全局复用）。

```bash
git clone https://github.com/zqiren/orbital-team-collab.git
cd orbital-team-collab
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e .
```

1. **启动面板**：`teamctl dashboard --actor human:<你的ID>`，浏览器打开 <http://127.0.0.1:8765/>。
2. **新建项目**：左侧「+ New project」，用内置文件夹浏览器选任意本地文件夹（非 Git 文件夹会自动
   `git init` 并提交现有内容），选择 Manager runner（`claude-code` / `codex` / `manual`）——守护进程
   随项目自动启动。
3. **接入成员**：设置页填一个成员 ID，复制生成的接入消息，粘贴到一个新的 Claude Code（或 Codex）
   会话里；agent 自动完成 worktree、身份绑定与插件安装，并向成员简报工作方式。
4. **喂任务**：看板上「New draft task」建任务，把卡片拖入「Ready」放行；（收件箱可分诊 IM 沉淀出的
   候选任务——demo 中通过 fixture 摄入）。
5. **成员干活**：成员会话里 `/team claim` 认领 → 在自己的 worktree 工作、本地提交 →
   `/team report` 提交带验证证据的报告；`/team block` 上报阻塞。
6. **自动集成与知识沉淀**：守护进程把报告转为集成任务并唤起无头 management agent——合并、或退回
   修改、或阻塞并向你开一个 Open Question；每次合并后团队记忆（`orbital/` 四份文件）被自动编译更新，
   在「文件」页可见，「动态」页有全程事件与运行日志。
7. **回答问题**：「问题」页直接在卡片上作答，被挂起的任务与集成自动解锁。

### 快速体验（合成数据 demo，完全离线）

```bash
python3 -m pytest -q                       # 全量测试
python3 demo/scripts/team_demo.py doctor --runner builtin

DEMO_ROOT=$(python3 demo/scripts/team_demo.py setup \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["root"])')
python3 demo/scripts/team_demo.py start --root "$DEMO_ROOT"   # 双成员闭环：claim→report→merge→knowledge
python3 demo/scripts/team_demo.py status --root "$DEMO_ROOT"

teamctl dashboard --workspace "$DEMO_ROOT/canonical" --actor human:demo-manager
# 浏览器打开 http://127.0.0.1:8765/?project=apollo
python3 demo/scripts/team_demo.py reset --root "$DEMO_ROOT"   # 精确清理该临时根
```

`reset` 会验证 runtime marker 与绑定 exact resolved root 的 demo marker；成功删除不可恢复，
不要把 home、repo root 或宽泛目录当参数。

## Team Dashboard

- 左侧项目列表与「+ New project」：选择任意本地文件夹一键建项目（内置文件夹浏览器与最近使用；非 Git
  文件夹自动 `git init` 并提交现有内容；守护进程随项目自动启动）；跨文件夹项目注册表存于
  `~/.orbital-team/projects.json`，Manager 状态徽标常驻页头（空闲 / N 排队等待 / 集成中）。
- **看板**：六列状态投影（待办/就绪/进行中/审核中/已阻塞/已完成）。人类唯一合法操作是把
  「待办」草稿拖入「就绪」释放给 agent 认领（等价 `task.ready`）；点击卡片打开详情抽屉
  （描述、验收标准、Report 验证证据、集成任务、阻塞问题）。其余流转全部由 Member/Manager
  事件驱动，看板只是实时投影。
- **收件箱 / 问题**：Potential Task 分诊（Promote 永远只产生 Draft），Open Question 卡片
  行内输入答案。
- **文件**：canonical 工作区的只读文件树与预览（`orbital/` 项目记忆高亮、懒加载、
  64KB 截断、路径逃逸/symlink/.git 防护）。
- **设置**：成员名册（实时状态、分支、加入时间）与两类一键复制的接入消息——成员 agent 消息贴入任意
  agent 会话即自动建 worktree、`teamctl member join` 绑定身份、安装 `/team` 指令集并向用户简报用法；
  管理 agent 消息用于 manual 模式的交互式驾驶。Manager runner 可选 manual / claude-code / codex
  （含本机 CLI 安装与登录探测，headless 运行复用已有登录），守护进程（teamd）一键启停、随项目
  创建自动启动，且不随面板关闭而停止。
- 界面支持 English / 中文 切换（localStorage 持久化，zh* 浏览器默认中文）。

## 原型证明了什么

- Confirmed Tasks、Potential Tasks、Open Questions 是三种独立工作对象；IM fixture 不会自动开工。
- Alice/Bob 在两个 linked worktree 中并行 claim/start/commit/report，actor 由 worktree binding 推导。
- `report.submitted` 触发 `teamd`，Integration Job 按 Project 串行执行并可崩溃恢复、重试和幂等重放。
- ManagerRunner 可替换；默认 `builtin` runner 完全离线，通过受控 domain command merge/propose，不获得裸 Git push 权限。
- code merge 后生成 Knowledge Proposal，只 apply allowlisted canonical memory path，并创建独立本地 knowledge commit。
- Dashboard 是共享 runtime 的 loopback projection + 受控 Human 写入口，没有 Node、数据库或第二套状态机。
- 无头 `claude-code` manager 已在真实项目上完成端到端 rehearsal：审阅真实成员报告、发现口径不一致后
  主动阻塞并向人开出 Open Question——「人保留裁决权」是已发生的行为，不是设计承诺。
- replay 永久标记为 `simulated-replay` / `live_success=false`，不冒充 live success。

## Runner 与 replay

默认 `builtin` 是可重复的离线 scripted Manager。要使用已有外部 CLI，先检查环境：

```bash
python3 demo/scripts/team_demo.py doctor --runner codex
python3 demo/scripts/team_demo.py doctor --runner claude-code
```

CLI 文件存在不等于 provider sandbox 可运行；只有真实产生 schema result、受控 merge 与 knowledge
apply 才算 live rehearsal。`claude-code` runner 已在 macOS 上完成真实 rehearsal：真实成员在
worktree 中 claim/commit/report，headless `claude -p` 作为 Manager 通过受控命令完成 validation、
merge 与 knowledge proposal。两个使之可复现的细节：runner 环境透传 `USER`（macOS Keychain 凭据
按账户名解析，缺失时 CLI 报 not logged in），manifest 预授权 headless 工具集
（`--allowedTools Bash,Read,Write,Edit,Glob,Grep --strict-mcp-config`）。

缺少 agent 时可以看 replay，但输出会明确说明它只是 UI/event fallback：

```bash
python3 demo/scripts/team_demo.py replay
```

## 可重复的 clean-copy 验证

下面的脚本把当前交付文件复制到新临时目录、初始化全新 Git repo、创建隔离 venv、editable
install、运行全量 tests/CLI/demo，并确认 source repo 未被修改：

```bash
python3 scripts/verify_clean_copy.py --dashboard-policy require
```

受限 sandbox 若禁止 loopback bind，使用 `--dashboard-policy allow`；脚本仍会真实尝试 bind、记录
EPERM，并验证 Dashboard projection，不能把该结果写成 browser success。详细矩阵与录制步骤见
[最终验证与录制指南](docs/38-final-verification.md)。

## 文档导航

| 阅读目标 | 文档 |
|---|---|
| **设计书（主要产物）** | [DESIGN.html](./DESIGN.html) |
| 作业目标与成功标准 | [Assignment Brief](docs/00-assignment-brief.md) |
| Orbital 现状与源码证据 | [现状盘点](docs/01-orbital-current-state.md) · [源码笔记](docs/01b-orbital-source-notes.md) |
| 竞品论证 | [竞品综合](docs/02-competitive-landscape.md) · [原始研究](docs/research/) |
| 用户与产品方向 | [用户场景](docs/10-user-scenarios.md) · [方向池](docs/11-team-feature-directions.md) |
| 产品契约 | [PRD](docs/20-prd.md) · [Architecture](docs/21-architecture.md) · [Protocol](docs/22-protocol.md) |
| 实施路线与边界 | [Roadmap](docs/30-roadmap.md) · [SPEC Index](specs/README.md) |
| Demo 与安全 reset | [Demo Orchestration](docs/37-demo-fixture-and-orchestration.md) |
| 最终测试、限制和录制 | [Final Verification](docs/38-final-verification.md) |

## 已知限制

- 本仓库是**本地 demo**：单机、单 OS 用户信任边界；runtime 不跨机器同步，Dashboard actor 不是远程
  认证。生产形态（云端团队空间 + 云端 management agent）见设计书第 07 节——协议不变，替换存储层与
  runner 宿主。
- 讨论沉淀（IM 接入）目前仅支持 fixture 摄入；真实 IM CLI 与 always-on 定时沉淀在路线图上。
- 当前自动验收使用真实 subprocess/worktree/Git/domain pipeline 的 `builtin` runner；它不是外部 LLM。
- Codex/Claude Code 的实际可用性取决于评审机器上的 CLI、登录状态与 provider sandbox。
- 非 POSIX 权限与 runner 子进程树语义未完成实机验证。
- 不包含真实 IM connector、Team Cloud、SSO/RBAC、Approval Routing、Team Budget 或 remote push。

## 安全、隐私与许可

- fixture 全部 synthetic；repo 不保存真实 IM、token、transcript、ledger、tool output 或本机绝对路径。
- local runtime/run logs 由 `.gitignore` 排除，敏感文件默认用户私有权限。
- Manager 不会 push；所有 merge/knowledge commit 只发生在显式 demo/canonical 临时仓库中。
- 本作业 repo 尚未声明开源许可证，不应推断额外使用授权；第三方依赖归属见
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
