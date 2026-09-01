# 01b — Orbital 源码级盘点

> 回应「你看了 Orbital 本身的项目吗」：README（docs/01）之外，本文基于官方 main 分支源码快照（2026-09-01 抓取至 `orbital-src/`，34.7MB / 1163 文件 / Python ≈202k LOC + web/ React 前端）。
> 方法：模块清单 + 关键模块精读 + 全库 grep。行号会随上游漂移，引用以文件名+模块名为准。

## 1. 架构一页

- `agent_os/`（Python daemon）+ `web/`（React 前端）+ `tests/`（unit/integration/e2e/manual 全套）。
- 关键模块：`agent/`（agent loop、tools、transports）、`daemon_v2/`（管理面 ~25 模块：agent_manager / fanout / sub_agent_manager / trigger_manager / project_store / settings_store / autonomy…）、`queue/`、`budget/`、`relay/`、`onboarding/`、`api/`（app / middleware / routes / ws）、`manifests/`（声明式 agent yaml）。
- **单一磁盘布局 owner**：`agent_os/agent/project_paths.py`（`budget/ledger.py` 注释原文 "the single owner of all Orbital on-disk layout"）——团队化的扩展点非常清晰。

## 2. 代码证据：单人假设在每一层（team feature 空档坐实）

| 层 | 证据 | 含义 |
|---|---|---|
| 任务来源 | `queue/models.py`：`Source` 枚举只有 `USER` / `UPLOAD`，无发起人/成员概念 | 共享队列需新增 requested_by / assigned_to |
| 队列存储 | `queue/store.py`：文件 CRUD + 进程内 `threading.Lock`，自称 "single source of truth" | 单机单进程锁，无跨机/多人协议 |
| 用量账本 | `budget/ledger.py`：per-workspace append-only JSONL（`{workspace}/orbital/ledger/usage.jsonl`），tokens-as-fact 四字段互斥 | 有计量事实，无「谁花的」主体维度 |
| 全库 grep | `team`/`multi-user` 全库仅 1 处命中——`daemon_v2/fanout.py` 注释（"team-lead spec" 的 join-summary 格式） | 产品代码零团队概念，与 README 单人叙事一致 |
| 用户身份 | `api/` 无用户级 auth（OAuth 代码是给 agent 连 Google connector 用的；ws.py 里是 "sub-agent login progress"） | 没有账号体系，F7 IT pack 是绿地 |
| 云侧 | `relay/` 仅 client/device 两文件；repo 根 AGENTS.md 明文 landmine："cloud relay is control, not storage" | 移动审批已出本机，但没有云存储层可承载共享状态 |

## 3. 旗舰组合的代码触点映射（PRD 落点）

- **F1 Shared Project State** → 扩展 `project_paths.py`（布局 owner）与 `queue/store.py`（进程锁升级为 git 同步层）；`queue/models.py` 自述 "new optional fields are added at the tail so existing queue.json files keep deserializing" 且带 `version` 字段——**additive 迁移路径现成**，加 `requested_by/assigned_to/approver` 不破坏旧文件。
- **F2 Approval Routing** → `agent/transports/tool_risk.py` 已有 `classify_tool()` 风险分级与 `should_auto_approve(autonomy)`（未识别工具默认 `requires_approval`——fail-closed 在代码层成立）；`relay/` 已能把审批送出本机（手机）。团队版 = 给 relay 加路由表：目的地从「owner 设备」变「按风险等级映射的成员角色」。
- **F3 Team Budget** → `budget/ledger.py` 事实层 append-only、字段互斥（uncached_input / cache_read / cache_write / output）；注释原文已预留 "derived cost views live in a later piece"（速率表/成本视图在官方计划内）。团队版 = 事件加 member/project 维度 + 速率表出成本 + `guard.py` 超限动作接审批。
- **F4 Worker Pool** → `manifests/*.yaml`（built-in-agent.yaml / claude-code.yaml）+ `agents/registry.py`——agent 定义已声明式，团队共享 worker 池有配置基础。
- **F5 Onboarding** → `onboarding/import_scanner.py` 已实现「从 `~/.claude`、`~/.codex`、Obsidian 挖掘可导入项目」（metadata-only、排序、去重、死路径过滤）——冷启动导入是既有产品行为，团队版 = 从共享 git repo 继承状态，同一模式。

## 4. Dogfooding 自证（作业加分论据）

repo 根 AGENTS.md 自述：**本仓库双职**——既是产品源码，又是 Orbital 实例的 dogfooding 工作区（用自家记忆系统管理自己的 backlog）。`BACKLOG.md` + `BACKLOG/specs/` 是 gitignored 的本地路线图。→ 论据：「项目状态文件驱动开发」在 Orbital 自己身上已被验证，而团队版要共享的正是这套状态文件。

## 5. 成熟度判断（喂给 roadmap）

- 代码注释带 "D2 schema"、"Budget Piece 1"、"backlog #34" 等字样 → 快速迭代期、模块化纪律好；schema additive 迁移是明确设计原则。
- 工程量排序依据：**F2 最小**（relay 加路由表，机制已在）→ **F1 地基最厚但改动集中**（文件态 + additive schema 都现成）→ **F3 中等**（需先补速率表/成本视图，官方已计划）→ **F7 最大**（账号体系全绿地）。此排序直接支撑 roadmap 的分期逻辑。
