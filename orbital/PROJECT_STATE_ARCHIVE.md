# PROJECT_STATE_ARCHIVE.md (trimmed content, read-on-demand)

## [trimmed 2026-09-01]

- src/orbital_team/knowledge_workflow.py、skills/orbital-team-manager/、tests/test_knowledge_workflow.py、docs/34-manager-knowledge-compilation.md — durable knowledge 分类、Proposal 校验、受控独立 commit/no-change、dirty/stale/block/resume、幂等恢复与 8 项专项测试
- src/orbital_team/member_adapter.py、skills/orbital-team-member/、tests/test_member_adapters.py — worktree-bound `/team` adapter、Claude SessionStart/member Run、agent-neutral install/fallback 与 11 项专项测试
- src/orbital_team/im_context.py、demo/im-fixtures/、tests/test_im_context.py、docs/35-im-context-and-potential-task-stub.md — 离线 IM provider/ContextItem fixture、evidence extraction、Potential Task/Open Question triage 与 10 项专项测试
- src/orbital_team/dashboard.py、dashboard_static/、tests/test_dashboard.py、docs/36-team-dashboard.md — shared runtime projection、actor-bound Human routes、无构建链 UI、敏感日志 guard 与 9 项专项测试
- orbital-src/ — Orbital 官方 main 源码快照（git clone 被沙箱挡，改 tarball，见 LESSONS）
## 核心结论（已锚定）
- Orbital = 1 人 × N agents；竞品「团队功能」= 卖给 IT 的治理；全行业空白 = git 化项目状态 × 异构编排 × 团队治理的组合，窗口 6–12 个月
- 源码层佐证：queue Source 枚举仅 USER/UPLOAD、进程内锁、账本无主体维度、api 无用户级 auth——单人假设从产品到代码一致
- 旗舰组合：Git-native Team Workspace = F1 Shared Project State + F2 Approval Routing + F3 Team Budget；F5 做 demo 载体；代码触点已映射（docs/01b 第 3 节）
- demo 方向已收敛为自包含的 file-native Team Workspace：不依赖 Orbital 安装/API；Manager/Member 是 agent-neutral 角色；成员用 `/team claim` 原子认领并上报，文件事件自动启动短生命周期 Manager Run 完成代码与知识合并
- 产品采用两层文件模型：Git 版本化 durable knowledge/config/code/demo seed；tasks/events/reports/jobs/run logs 持久化在本地 runtime、由 Team Dashboard 读取但不提交，未来 Team Cloud 负责跨机器同步
- SPEC-00 的 8 个 design review questions 已全部收敛：入口 `/team`；其余采用 DECISIONS D11 的默认契约
- 实现边界已冻结为 Python 3.11 单一 domain/storage package + JSON Schema/filelock + 无 Node/DB 的 loopback Dashboard；代码 merge 用 `integration.merged`，knowledge commit 后才 `integration.completed`
- durable knowledge apply 生成独立本地 Git commit（no-change 不造空 commit）；所有 merge/commit 经 git mutation lock 与受控 domain command，绝不 remote push
- 工作系统包含 Confirmed Tasks、Potential Tasks、Open Questions；IM v1 只留 provider stub/fixture，Potential Task 经 triage 后才能成为可领取任务
## 下一步
1. 剩余 spec 逐 spec 执行：下一项 SPEC-08（Ready），之后 SPEC-09；每个 spec 由主 session 复测后 checkpoint
2. SPEC-08 使用已完成的 Member/Manager/IM/Dashboard primitives 组装可重置 demo fixture 与多 worktree orchestration，不复制状态机或引入真实 IM/provider 账号
3. 每个 spec 完成后由主 session 复测并本地 checkpoint commit，发送给 Kimi/其他外部对象仍需单独授权
4. checkpoint 历史：SPEC-00 `902a870`、SPEC-01 `06691b4`、SPEC-02 `83cbf6e`、SPEC-04 实现层 `6e30a89`/记忆层 `fae75d7`、SPEC-05 实现层 `ed5c52e`/记忆层 `4e50161`、SPEC-03 `cbe716a`、SPEC-06 `97be555`；SPEC-07 按本 session 硬约束保持未提交，待主 session 复测 checkpoint；git 只读命令仍须加 `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null`（见 LESSONS）
5. Push 由用户在本机终端进入 `<workspace>` 后执行 `git push -u origin main`（2026-09-01 用户决定暂缓：拒绝提供 PAT，沙箱无 gh/ssh/keychain 凭据）；后续 spec 完成同样先本地 commit，push 一并交给用户
  <!--mem id:380ae9 created:2026-09-01 touched:2026-09-01-->
## 阻塞
- SPEC-07 无实现 blocker；当前 sandbox 禁止 loopback listen socket，因此 routes 使用同一 BaseHTTPRequestHandler 的内存 HTTP transport 验证，真实 `teamctl dashboard` socket/browser smoke 留普通本机复测。
- 已完成的 checkpoint（`902a870`、`06691b4`、`83cbf6e`）均未 push 到 origin/main；沙箱内无 HTTPS 凭据，由用户在自己终端决定 push 节奏。
