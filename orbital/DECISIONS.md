<!--format DECISIONS entries: '## <slug>' then Chose / Reason / Rejected. Supersede or replace old entries when a decision changes; never leave contradictions.-->
# DECISIONS

## D1 — demo 后置 <!--mem id:d1-demo created:2026-09-01 touched:2026-09-01-->
Chosen: 基础文档（竞品综合、场景、方向池、PRD、路线图）完成并获用户确认前，不启动 demo。
Reason: 用户明确指示（2026-09-01）「要做 demo，但是你先别做，你先沉淀好一些基础文档和理解」。
Rejected: 文档与 demo 同步推进（用户明确否决）。

## D2 — 语言约定 <!--mem id:d2 created:2026-09-01 touched:2026-09-01-->
Chosen: 文档中文为主，术语与 repo 名用英文。
Reason: 用户中文交流；Kimi 为中国公司；技术术语保英文准确。

## D3 — 竞品研究方法 <!--mem id:d3 created:2026-09-01 touched:2026-09-01-->
Chosen: fanout 3 个 worker 并行联网核实（Claude Code / Codex / 其他+趋势），原始研究存 docs/research/，主 agent 核实后综合进 docs/02-competitive-landscape.md。
Reason: 竞品信息必须联网核实且标注来源日期（项目规则）；并行省时。

## D4 — 文档编号体系 <!--mem id:d4 created:2026-09-01 touched:2026-09-01-->
Chosen: docs/00 简报、01 Orbital 现状、02 竞品综合、10 场景、11 方向池；原始研究层 docs/research/。
Reason: 规划文档与原始证据分层，评审可读、论据可溯。

## D5 — 核心立论（作业主线） <!--mem id:d5 created:2026-09-01 touched:2026-09-01-->
Chosen: Team Feature = Orbital「project as unit」逻辑的自然延伸：session→project（已完成）→ team（下一步）；抓手 = 所有项目状态是本地纯文本文件，天然 git 化。
Reason: README 实证 Orbital roadmap 无任何团队字样（单人假设），且竞品 Claude Code/Codex 同样卡在单人假设——这是「定位雷同」质疑的正面解法。
Rejected: 把 team feature 讲成功能堆砌清单（不构成差异化叙事）。

## D6 — demo 运行边界
Chosen: 交付 repo 自包含，不依赖 Orbital 安装、daemon 或本地 API；沿用 Orbital 的项目文件语义，由 repo 内的 CLI、事件调度器、Skills 和看板共同执行文件协议。
Reason: Kimi 应能只 clone 一个 repo 即理解和运行原型；要求额外安装 Orbital 会破坏交付闭环。
Rejected: 调用 Orbital 本地 API 的 companion demo。

## D7 — 角色与事件驱动 Manager
Chosen: Manager/Member 是与 agent 类型正交的角色；成员 Report Submitted 后由文件事件和 `teamd` 启动新的短生命周期 Manager Agent Run，自动串行完成集成与知识编译。
Reason: 任意 agent 都能担当 Manager，且不依赖向某个长期交互窗口注入事件；项目文件而非 session 保存连续性。
Rejected: 固定 Codex 为 Manager；等待用户提醒 Manager 检查 inbox；把长期 agent session 作为事实来源。

## D8 — 工作对象与成员入口
Chosen: 分离 Confirmed Tasks、Potential Tasks、Open Questions；`/project <project-name> <task-id-or-query>` 唯一匹配时原子认领并返回上下文，Potential Task 必须 Promote，blocking Open Question 阻止 claim。
Reason: 执行承诺、IM 提取出的候选和待澄清问题有不同生命周期；分离后才能避免 agent 抢占未确认工作或在关键问题缺失时猜测。

## D9 — 跨 session spec 执行
Chosen: 实现拆为 SPEC-00～SPEC-09，每个 spec 在单独 session 完成；handoff 使用 Spec Index + Completion Record + Orbital PROJECT_STATE/DECISIONS/LESSONS/INDEX。
Reason: 每阶段保持单一可验收结果，并让新 session 无需聊天历史即可冷启动。

## D10 — Git 提前初始化与 push 边界
Chosen: 2026-09-01 应用户要求在工作区根目录提前完成 `git init`（main 分支）+ remote `origin` = https://github.com/zqiren/orbital-team-collab.git（远端为空仓库，已验证可达）；本地 git identity 用 zqiren / zqzqzqr0@gmail.com（个人 GitHub，不用全局 tencent.com 邮箱）。`.gitignore` 排除 `orbital-src/`（55MB 只读快照）与 orbital 机器管理运行时（sessions/ledger/tool-results/output/queue/approval_history/sub_agents 的 jsonl 与 .latest）；`orbital/*.md`、instructions/、skills/、sub_agents MEMORY.md 版本化。每个 spec 完成可做本地 checkpoint commit；任何 push 仍需用户单独授权。
Reason: 用户 2026-09-01 明确要求 setup git；SPEC-00/01 原「git init 由 SPEC-01 执行、不建 remote」的假设由此被取代（两份 spec 文本已同步更新）。
Rejected: 等 SPEC-01 再 init（用户要求提前）；提交 orbital 运行时数据（违反 SPEC-09 交付原则）。
