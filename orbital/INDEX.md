<!--format INDEX is a navigation map ONLY: '- path — one sentence' bullets under '## <area>' headings. No dates, status, decisions, or lessons here — those live in PROJECT_STATE.md / DECISIONS.md / LESSONS.md.-->
# INDEX

## 交付文档（docs/）
- README.md — Kimi 评审入口：30 秒立论、架构图、quickstart、文档导航与限制
- THIRD_PARTY_NOTICES.md — filelock/jsonschema 直接依赖的 attribution 与根 repo 许可边界
- docs/00-assignment-brief.md — 作业简报：背景、成功标准、repo 规划
- docs/01-orbital-current-state.md + docs/01b-orbital-source-notes.md — Orbital 现状盘点与源码级单人假设证据
- docs/research/ + docs/02-competitive-landscape.md — 竞品原始联网研究（claude-code/codex/adjacent）与综合分析
- docs/10-user-scenarios.md + docs/11-team-feature-directions.md — 团队画像与核心场景、方向池 F1-F7 与旗舰组合
- docs/20-prd.md + docs/21-architecture.md + docs/22-protocol.md — PRD、架构与协议契约（两层文件模型、命令语法）
- docs/30-roadmap.md — SPEC-01～09 里程碑与后续路线
- docs/31～38-*.md — 各 spec 的安装/运行/安全/验证说明与最终 clean-copy/录制指南

## 系统与目标
- orbital-src/ — Orbital 官方源码快照（只读参考，不进交付 repo）
- orbital/instructions/project_goals.md — 项目目标与规则
- AGENTS.md — Orbital 生成的子 agent 上手文件
- skills/spec-pipeline/SKILL.md — 主 session 的 spec 派发/复测/checkpoint 循环手册

## Runtime 实现（src/orbital_team/ 与仓库根）
- pyproject.toml / pytest.ini / conftest.py — package 与 `teamctl`/`teamd` console entries、pytest 收集钉住与沙箱安全 shim
- src/orbital_team/ — runtime kernel：common-dir、schema/models、atomic storage、events/idempotency、runtime lifecycle 与 CLI
- member_workflow.py / member_adapter.py — 成员状态机与 `/team` 适配（actor 从 current-worktree binding 推导）
- manager_integration.py / manager_runner.py / manager_proc.py / teamd.py — Integration Job、ManagerRunner、离线 Manager 适配与事件驱动守护
- knowledge_workflow.py — Knowledge Proposal、allowlisted canonical memory apply、独立 knowledge commit
- im_context.py — IM provider seam、fixture extraction、Potential Task/Open Question 生命周期
- dashboard.py + dashboard_static/ — loopback Dashboard：runtime 投影、actor 绑定路由与静态 UI
- demo_orchestration.py + demo/scripts/team_demo.py — 可重置 demo 编排与 doctor/setup/start/status/reset/replay 入口
- scripts/verify_clean_copy.py — disposable Git copy/venv 中验证 install、tests、CLI、demo、bind、reset 与 source isolation
- demo/seed/ + demo/runners/ + demo/sample-app/ + demo/im-fixtures/ + demo/replay/ — synthetic seed、runner manifests、示例应用、离线 IM fixtures 与 replay fallback
- skills/orbital-team-manager/ + skills/orbital-team-member/ — Manager/Member agent Skills、Claude command/hook 与安装器；src/orbital_team/skills/manager-integration.md — Manager 集成 procedure
- tests/ — 分 spec 与最终 delivery contract tests，覆盖 runtime、workflow、Manager、knowledge、IM、Dashboard、demo 与交付扫描

## 规范 Schema（schemas/）
- schemas/v1/orbital-team.schema.json + schemas/README.md — Protocol 1.0 JSON Schema bundle 与消费映射

## 实现规格（specs/）
- specs/README.md + specs/EXECUTION_PROTOCOL.md — SPEC-00～09 状态表/依赖图与每个 session 的执行协议
- specs/SPEC-00～09-*.md — 各阶段规格（文件名自释：契约 / runtime kernel / claim / adapters / manager-integration / knowledge / IM / dashboard / demo / delivery）

## Memory maintenance
- orbital/PROJECT_STATE_ARCHIVE.md — 从 live PROJECT_STATE 降级的历史完成项与旧阶段记录
