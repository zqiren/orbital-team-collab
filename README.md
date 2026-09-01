# Orbital Team Workspace

> 把“一个人与一个 coding agent 的 session”升级为“一个团队与多个异构 agent 共同维护的 Project”。

## 30 秒电梯陈述

Orbital、Claude Code 和 Codex 都擅长提升个人编码效率，但项目事实仍容易困在某个人的
session、本机 memory 或某一种 agent 里。团队同时使用多个 agent 后，最缺的不是另一个
聊天窗口，而是跨人、跨 agent、跨 session 的领取、上报、集成、恢复和项目学习协议。

Orbital Team Workspace 用两层文件模型补上这一层：高频 Tasks、Reports、Events、Runs 留在
Git common-dir 下的本地持久 runtime；代码和 Manager 编译出的 PROJECT_STATE、DECISIONS、
LESSONS、INDEX 进入可审查的 Git durable layer。Member 在独立 worktree 工作，Report 触发
短生命周期 Manager，自动完成受控 code merge、knowledge commit 和 Dashboard 投影。

这不是“再造 Claude Code/Codex”，而是把 Orbital 已经完成的 `session → project` 升维继续
推进到 `project → team`。

## 原型证明了什么

- Confirmed Tasks、Potential Tasks、Open Questions 是三种独立工作对象；IM fixture 不会自动开工。
- Alice/Bob 在两个 linked worktree 中并行 claim/start/commit/report，actor 由 worktree binding 推导。
- `report.submitted` 触发 `teamd`，Integration Job 按 Project 串行执行并可崩溃恢复、重试和幂等重放。
- ManagerRunner 可替换；默认 `builtin` runner 完全离线，通过受控 domain command merge/propose，不获得裸 Git push 权限。
- code merge 后生成 Knowledge Proposal，只 apply allowlisted canonical memory path，并创建独立本地 knowledge commit。
- Dashboard 是共享 runtime 的 loopback projection + 受控 Human 写入口，没有 Node、数据库或第二套状态机。
- replay 永久标记为 `simulated-replay` / `live_success=false`，不冒充 live success。

## 两层文件模型与事件闭环

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

Git 保存低频、可审查、随 clone 传播的 durable knowledge；runtime 保存高频、本地、可恢复的
协作状态。v1 诚实限定为单机多 worktree，跨机器 runtime 同步属于 Team Cloud 路线。

## Quickstart

前置条件：Git、Python 3.11+。不需要安装 Orbital，不需要 Node、数据库、真实 IM 账号或网络服务。

```bash
git clone https://github.com/zqiren/orbital-team-collab.git
cd orbital-team-collab

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m pytest -q
```

运行默认的完全离线双成员闭环：

```bash
python3 demo/scripts/team_demo.py doctor --runner builtin

DEMO_ROOT=$(python3 demo/scripts/team_demo.py setup \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["root"])')
python3 demo/scripts/team_demo.py start --root "$DEMO_ROOT"
python3 demo/scripts/team_demo.py status --root "$DEMO_ROOT"
```

`start` 成功时应看到两个 Done Integration Jobs、两个 knowledge summaries，以及两个 Done
seed Tasks；Promote 出来的 IM Task 仍是 Draft。

另开终端启动 Dashboard：

```bash
source .venv/bin/activate
teamctl dashboard \
  --workspace "$DEMO_ROOT/canonical" \
  --actor human:demo-manager \
  --host 127.0.0.1 \
  --port 8765
```

浏览器打开 <http://127.0.0.1:8765/?project=apollo>。停止 Dashboard 后清理精确临时根：

```bash
python3 demo/scripts/team_demo.py reset --root "$DEMO_ROOT"
```

`reset` 会验证 runtime marker 与绑定 exact resolved root 的 demo marker；成功删除不可恢复，
不要把 home、repo root 或宽泛目录当参数。

## Team Dashboard

Dashboard 仍是共享 runtime 的 loopback projection 加受控 Human 写入口；前端遵循 Orbital 的
设计语言（三级 surface ladder、azure accent、Geist 字型栈），信息层级为：

- 左侧项目列表 → 项目页顶部 Agents 实时状态条：谁在做哪个任务、Manager 是否在集成。
- **看板**：六列状态投影（待办/就绪/进行中/审核中/已阻塞/已完成）。人类唯一合法操作是把
  「待办」草稿拖入「就绪」释放给 agent 认领（等价 `task.ready`）；点击卡片打开详情抽屉
  （描述、验收标准、Report 验证证据、集成任务、阻塞问题）。其余流转全部由 Member/Manager
  事件驱动，看板只是实时投影。
- **收件箱 / 问题**：Potential Task 分诊（Promote 永远只产生 Draft），Open Question 卡片
  行内输入答案。
- **文件**：canonical 工作区的只读文件树与预览（`orbital/` 项目记忆高亮、懒加载、
  64KB 截断、路径逃逸/symlink/.git 防护）。
- Agents 条上的「+ Add member」按输入的成员 ID 生成可复制注册命令（`git worktree add` →
  `teamctl member join` → member adapter 安装）；注册后该 worktree 中的 Claude Code 会话
  即获得 `/team claim|start|report|block|status|questions|manager` 语法，身份始终来自
  worktree 绑定。
- 界面支持 English / 中文 切换（localStorage 持久化，zh* 浏览器默认中文）。

## Runner 与 replay

默认 `builtin` 是可重复的离线 scripted Manager。要使用已有外部 CLI，先检查环境：

```bash
python3 demo/scripts/team_demo.py doctor --runner codex
python3 demo/scripts/team_demo.py doctor --runner claude-code
```

CLI 文件存在不等于 provider sandbox 可运行；只有真实产生 schema result、受控 merge 与 knowledge
apply 才算 live rehearsal。`claude-code` runner 已在 macOS 上完成一次真实 rehearsal：真实成员在
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
| 作业目标与成功标准 | [Assignment Brief](docs/00-assignment-brief.md) |
| Orbital 现状与源码证据 | [现状盘点](docs/01-orbital-current-state.md) · [源码笔记](docs/01b-orbital-source-notes.md) |
| 竞品论证 | [竞品综合](docs/02-competitive-landscape.md) · [原始研究](docs/research/) |
| 用户与产品方向 | [用户场景](docs/10-user-scenarios.md) · [方向池](docs/11-team-feature-directions.md) |
| 产品契约 | [PRD](docs/20-prd.md) · [Architecture](docs/21-architecture.md) · [Protocol](docs/22-protocol.md) |
| 实施路线与边界 | [Roadmap](docs/30-roadmap.md) · [SPEC Index](specs/README.md) |
| Demo 与安全 reset | [Demo Orchestration](docs/37-demo-fixture-and-orchestration.md) |
| 最终测试、限制和录制 | [Final Verification](docs/38-final-verification.md) |

## 已知限制

- v1 是单机、单 OS 用户信任边界；runtime 不跨机器同步，Dashboard actor 不是远程认证。
- 当前自动验收使用真实 subprocess/worktree/Git/domain pipeline 的 `builtin` runner；它不是外部 LLM。
- Codex/Claude Code 的实际可用性取决于评审机器上的 CLI、登录状态与 provider sandbox。
- 最终交付验证已完成真实 loopback bind 与 HTTP GET smoke；浏览器级可视化 walkthrough 建议在普通本机复测。某些更受限的执行环境可能禁止 `socket.bind`，届时 verifier 用 `--dashboard-policy allow` 如实记录失败。
- 非 POSIX 权限与 runner 子进程树语义未完成实机验证。
- 不包含真实 IM connector、Team Cloud、SSO/RBAC、Approval Routing、Team Budget 或 remote push。

## 安全、隐私与许可

- fixture 全部 synthetic；repo 不保存真实 IM、token、transcript、ledger、tool output 或本机绝对路径。
- local runtime/run logs 由 `.gitignore` 排除，敏感文件默认用户私有权限。
- Manager 不会 push；所有 merge/knowledge commit 只发生在显式 demo/canonical 临时仓库中。
- 本作业 repo 尚未声明开源许可证，不应推断额外使用授权；第三方依赖归属见
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

