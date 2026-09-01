<!--format INDEX is a navigation map ONLY: '- path — one sentence' bullets under '## <area>' headings. No dates, status, decisions, or lessons here — those live in PROJECT_STATE.md / DECISIONS.md / LESSONS.md.-->
# INDEX

## 交付文档（docs/）
- docs/00-assignment-brief.md — 作业简报：背景、成功标准、repo 规划、风险
- docs/01-orbital-current-state.md — Orbital 现状盘点（README 实证 + 一手体感）
- docs/01b-orbital-source-notes.md — Orbital 源码级盘点（单人假设的代码证据 + 旗舰功能触点映射）
- docs/research/ — 竞品原始联网研究（claude-code.md / codex.md / adjacent.md，含来源与日期）
- docs/02-competitive-landscape.md — 竞品综合分析（综合 research/：雷同质疑反驳 + 团队维度对比表 + 四条空白）
- docs/10-user-scenarios.md — 目标团队画像（A/B/C）与六个核心场景 + 优先级
- docs/11-team-feature-directions.md — 方向池 F1-F7 + 优先级矩阵 + 旗舰组合（F1+F2+F3）与北极星
- docs/20-prd.md — Team Workspace PRD：两层文件模型、角色、v1 范围、用户旅程、安全边界与成功指标
- docs/21-architecture.md — Git common-dir runtime、transaction/recovery、Manager pipeline、knowledge commit、Dashboard/IM/Team Cloud 边界
- docs/22-protocol.md — 规范对象、状态转换、`/team`/`teamctl`、ManagerRunner、错误码、事件与权限契约
- docs/30-roadmap.md — SPEC-01～09 实现里程碑、验证风险、Prototype Done 与 Team Cloud/F2/F3 后续路线

## 系统与目标
- orbital-src/ — Orbital 官方 main 源码快照（2026-09-01 tarball，只读参考，不进交付 repo）
- orbital/instructions/project_goals.md — 项目目标与规则（本次作业的 mission）
- AGENTS.md — Orbital 生成的子 agent 上手文件（项目记忆系统说明）

## 后续交付（规划中）
- README 电梯陈述、可运行 demo — 按 SPEC-01～SPEC-09 分阶段交付

## Runtime 实现
- pyproject.toml — Python 3.11+ package、`teamctl` console entry 与 jsonschema/filelock 依赖声明
- pytest.ini — 钉住 pytest rootdir/testpaths，避免收集越出工作区触发沙箱 EPERM
- conftest.py — pytest 沙箱安全收集 shim（EPERM 时按无 conftest 处理），正常环境 no-op
- src/orbital_team/ — common-dir resolver、schema/models、atomic storage、events/idempotency、runtime lifecycle 与 CLI
- src/orbital_team/member_workflow.py — current-worktree Member identity、Task resolve/state machine、原子 claim、Context Pack 与 Git-bound Report domain service
- tests/test_runtime_kernel.py — SPEC-01 的临时 Git repo/worktree、并发、损坏恢复、reset 与权限验证
- tests/test_member_workflow.py — SPEC-02 的双进程 claim、状态转换、blocking question、Git Report、schema、幂等与负向测试
- demo/seed/ — schema-valid synthetic Apollo 初始化输入与显式 demo reset marker
- docs/31-file-runtime-kernel.md — File Runtime Kernel 安装、运行、安全与验证说明
- docs/32-member-workflow.md — Member join/claim/start/block/status/report 命令、Context Pack、Git binding 与稳定错误使用说明

## 规范 Schema（schemas/）
- schemas/README.md — runtime 文件/对象与 JSON Schema `$defs` 的消费映射
- schemas/v1/orbital-team.schema.json — Protocol 1.0 的 JSON Schema Draft 2020-12 bundle

## 实现规格（specs/）
- specs/README.md — SPEC-00～SPEC-09 状态、依赖图、冻结原则与执行入口
- specs/EXECUTION_PROTOCOL.md — 每个独立 session 的启动、验证、handoff 与 blocking 协议
- specs/SPEC-00-product-contract-and-architecture.md — 冻结角色、数据、状态机、命令、事件与权限契约
- specs/SPEC-01-file-runtime-kernel.md — Git common-dir 文件 runtime、原子存储、锁、事件与幂等
- specs/SPEC-02-project-command-and-member-workflow.md — `/team claim` 原子认领、成员状态流转与结构化 Report
- specs/SPEC-03-member-skill-and-agent-adapters.md — Member Skill、Claude slash/hook 与 agent-neutral fallback
- specs/SPEC-04-event-driven-manager-integration.md — teamd、Integration Job、ManagerRunner 与自动代码集成
- specs/SPEC-05-manager-knowledge-compilation.md — Manager Skill、Knowledge Pack/Proposal 与 canonical memory apply
- specs/SPEC-06-im-context-and-potential-task-stub.md — IM provider contract、fixture、Potential Task/Open Question 提取与 triage
- specs/SPEC-07-team-dashboard.md — 三类工作对象、活动、集成与知识变化的本地文件看板
- specs/SPEC-08-demo-fixture-and-orchestration.md — 可重置 sample project、多 worktree 和 live/replay 演示编排
- specs/SPEC-09-e2e-hardening-and-delivery.md — clean-clone 验证、README、文档收敛与最终 repo 整理
