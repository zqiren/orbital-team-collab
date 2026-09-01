# 11 — Team Feature 方向池与优先级

> 上游：docs/02（四条全行业空白）、docs/10（场景优先级）。本文是方向池 + 优先级判断，PRD 从推荐组合展开。

## 1. 设计原则（先立规矩再列功能）

1. **延伸不推翻**：project as unit 不变，team 是 unit 的共享维度——「session→project 已完成，project→team 是下一次升维」，不是推倒重来。
2. **local-first 不破坏**：采用两层文件模型。Git 只同步经编译的 durable knowledge、配置和代码；高频 tasks/events/reports/run logs 留在本地 runtime，由 Team Dashboard 读取。Git 不是运行时数据库，跨机器实时协调留给后续 Team Cloud。
3. **治理已有，缺的是多人**：预算/审批/沙箱/审计机制已存在，产品化方向是「多人路由」，不是新建机制。
4. **组合即护城河**：竞品各有单点（Copilot 控制面、Devin 共享 credits、Cursor 共享 rules），无人拥有「git 化状态 × 异构编排 × 团队治理」组合（docs/02 第 5 节）。

## 2. 方向池

### F1 Shared Project State（旗舰）——「git 化的团队项目记忆」
- 一句话：Manager 把项目运行中值得长期保留的学习编译进 PROJECT_STATE / DECISIONS / LESSONS / INDEX / instructions，经 Git 共享并可走 PR 评审；高频协调对象仍留在本地 runtime。
- 为什么是 Orbital：状态天生是纯文本（docs/01 一手观察）；竞品的共享全是平台内黑盒资产（Cursor "shared team context"、Devin Knowledge、Copilot Spaces）。
- 对位空白：空白 1（docs/02 第 4 节）。
- 风险：跨机器的 live task board 在 v1 不会仅靠 Git 自动同步——v1 诚实限定为单机多 worktree；后续 Team Cloud 同步 runtime。canonical knowledge 的 Git 冲突由 Manager 显式仲裁，不静默覆盖。

### F2 Approval Routing（旗舰）——「跨人审批流转」
- 一句话：Workbench 从 owner 待办升级为团队风险队列：按操作类型/项目/金额路由审批人，手机批/驳，超预算自动上浮。
- 为什么是 Orbital：审批系统已 fail-closed（README），缺的只是路由表；竞品审批全部弹给操作者本人。
- 对位空白：空白 3。
- 风险：审批疲劳——需要分级（自动放行/单审/会签），呼应 Factory 把 "autonomy level" 做成组织配置的先例。

### F3 Team Budget（旗舰）——「跨异构 agent 的统一预算」
- 一句话：per-project / per-member / per-worker 预算分配 + 14 家 provider 统一计量 + 超限动作可配置（暂停/降级/请示）。
- 为什么是 Orbital：per-project 预算已存在（单人版）；BYOK 多 provider 是独家计量位置——Claude Code 只能算 Claude 的账，Codex 只能算 Codex 的账。
- 对位空白：空白 3。对位竞品：Devin 共享 credits 池（但仅 Devin）、Cursor pooled usage（仅 Enterprise）。

### F4 Heterogeneous Worker Pool（随旗舰）——「团队共享的异构 worker 池」
- 一句话：团队内所有 CLI agent（成员本机的 + 云端 worker）进入同一可调度池，队列按能力/成本/license 派发。
- 为什么是 Orbital：单机异构调度已验证（dsh 3 小时接入案例）；全行业唯一。
- 对位空白：空白 2。依赖 F1（需要共享队列状态）。

### F5 Onboarding Protocol（演示钩子）——「冷启动继承」
- 一句话：clone = 继承 durable knowledge；setup 从版本化 seed 初始化本地 runtime；新成员的 agent 首次冷启动从五类知识文件装配项目上下文（含“你最该知道的三件事”摘要）。
- 为什么是 Orbital：纯产品化包装，机制已有（冷启动组装进 system prompt）。
- 定位：小而妙，**demo 的最佳载体**（可见、可感、十秒讲清）。

### F6 Team Observability（后置）——「一屏看清团队的 agent 运营」
- 一句话：v1 本地 Team Dashboard 展示谁的 agent 在跑什么、任务进度、integration 与 run/session logs；跨机器汇总、成本和审批视图随 Team Cloud/F2/F3 后置。
- 对位竞品：Cursor usage analytics、Codex Analytics（Enterprise）、Devin；需要 F1-F3 的数据先行。

### F7 Org IT Pack（GA 前清单，不做差异化叙事）
- SSO/SCIM/审计导出/域名管控。跟随项：竞品全有，写进 roadmap 的 GA 条件，不进旗舰叙事。

## 3. 优先级矩阵（1–5 分）

| 方向 | 空白度（竞品没有） | 用户价值 | 现成地基 | 依赖 | 总评 |
|---|---|---|---|---|---|
| F1 Shared Project State | 5 | 5 | 5 | — | **旗舰 1** |
| F2 Approval Routing | 4 | 5 | 4 | — | **旗舰 2** |
| F3 Team Budget | 4 | 4 | 4 | — | **旗舰 3** |
| F4 Worker Pool | 5 | 4 | 4 | F1 | 随旗舰二期 |
| F5 Onboarding | 4 | 4 | 5 | F1 | **demo 载体** |
| F6 Observability | 3 | 3 | 2 | F1–F3 | 后置 |
| F7 IT Pack | 1 | 3 | 1 | — | GA 条件 |

## 4. 推荐旗舰组合（供 PRD 展开）

**「Git-native Team Workspace」= F1 + F2 + F3**，一张图讲清：

> Manager 把团队运行中值得长期保留的学习编译进 Git（F1 durable layer）→ 本地 tasks/events/reports/run logs 驱动实时协作（F1 runtime layer）→ 后续 Team Cloud 让 runtime 跨机器同步，并叠加风险审批路由（F2）和统一预算闸门（F3）。v1 demo 只证明单机端到端闭环，不把 roadmap 能力伪装成已实现。

叙事钩子（回应「雷同」质疑）：Claude Code 把团队功能卖给了 IT 部门（SSO/审计/限额），Orbital 把团队功能还给项目本身——**协作的最小单位不是组织架构树上的部门，而是同一个项目文件夹**。

北极星指标（草案）：**周跨成员项目动作数**（一周内，由成员 A 发起、被成员 B 的 agent 继承/接管/审批的项目状态读写与任务派发次数）。该指标同时校验共享真实性（跨人）与编排有效性（动作闭环）。

## 5. 明确砍掉的方向

- v1 自建云同步/云存储服务（会扩大 demo 范围且掩盖 local-first 主线）——当前用 Git 传播 durable layer；Team Cloud 作为跨机器 runtime 同步的后续路线，而非本期交付。
- agent 对等社交网络 / 自由组队（Claude agent teams 已证明 session 级组队用不起来：one team per session、no resume）——保持「1 管理 + N worker + 多人监督」拓扑。
- 团队版 prompt 市场（Cursor marketplace / Devin Playbooks 已拥挤，且非状态层）。
