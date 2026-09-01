<!--format PROJECT_STATE is what is true NOW: current focus, in-progress work, blockers, next steps. Overwrite stale lines; never append dated history. Every line must be understandable without this session's context: concrete names, no unexplained shorthand, no cross-references by list number. [user] flag — one judgment per line: does this need the user (their decision, their action, or something they'd be sorry to miss — including things they assigned to themselves)? If yes, insert [user] after the list marker of the line where the fact already lives: `- [user] <text>` or `3. [user] <text>`. Flagging marks a line, never creates one: one fact = one entry, never duplicated into another section. A dated commitment needing no decision is `[due:YYYY-MM-DD]` (shows on the calendar). Machine attributes (id, created, touched, resolved) live in a daemon-managed mem-comment on the next line — never write or edit these comments; leave them exactly where they are. Never auto-decide: spending money, sending external messages as the user, or irreversible/destructive acts are always surfaced, whatever the autonomy setting. Write timeless ("due Jul 28", never "tomorrow"). A line whose mem-comment carries resolved:<date> is settled — on consolidation rewrite it as the completed fact or drop it; never re-open or re-flag it. CLOSE THE LOOP THE SAME TURN: the moment the user answers a flagged line, decides it, or does it, remove the [user] flag from that line in this turn — rewrite the line as the settled fact (`- Chose option A.`) and leave the mem-comment alone. You are the only reader who can see both the flag and the user's answer; consolidation runs later, sees a truncated window, and cannot do this for you. A flagged line you leave behind after it is answered keeps nagging the user for something they already gave you. Never flag a question you asked during this session — flag the decision that is still genuinely open, written so someone who was not here can act on it.-->
# PROJECT_STATE

## 当前阶段
SPEC-08 Demo Fixture & Multi-agent Orchestration 已完成并 checkpoint（806958a）：Apollo synthetic fixture 在精确 marker 保护的临时根创建 canonical repo + Alice/Bob linked worktree + 共享 runtime；双成员进程并行 claim/report，builtin Manager 串行完成 code merge、独立 knowledge commit、`integration.completed` 与 Dashboard projection；doctor/reset/replay 齐备，专项 7/7、全量 107/107 通过。SPEC-09（交付收敛，最后一个 spec）已派发 codex。

## 本轮完成（2026-09-01）
- `src/orbital_team/demo_orchestration.py` 与 `demo/scripts/team_demo.py` 提供 doctor/setup/start/status/reset/replay；reset 先复用 D14 runtime marker，再验证绑定精确临时根的私有 demo marker。
- `demo/seed/` 现含两个 Ready Tasks 并默认选择离线 builtin runner；`demo/sample-app/`、`demo/im-fixtures/demo-messages.json` 与 `demo/replay/dashboard.json` 都是无真实身份、凭证、网络或绝对路径的 synthetic fixture。
- builtin Manager 扩展到 integration/knowledge 两个 phase；代码仍只经受控 merge，knowledge 仍只经受控 Proposal 与 SPEC-05 apply/独立 commit。
- `tests/test_demo_orchestration.py` 覆盖 fixture/schema、doctor/missing runner、共享 common-dir/Skill、双进程全闭环、exact-marker reset/连续两次、member crash、Manager retry 与 replay 标签。
- 使用文档位于 `docs/37-demo-fixture-and-orchestration.md`；较旧完成项与产品结论保存在 `orbital/PROJECT_STATE_ARCHIVE.md`。

## 下一步
1. SPEC-09（最后一个 spec）已派发 codex：clean-clone 验证、README 电梯陈述、文档收敛与最终 repo 整理；主 session 复测后做最终 checkpoint
2. SPEC-09 在普通本机补真实 loopback Dashboard/browser smoke，并在可用 provider 环境补至少一次真实外部 Manager/Member agent rehearsal；不得把 deterministic builtin 或 replay 冒充外部 agent。
3. Git checkpoint 链（本地 main）：SPEC-00 `902a870`、SPEC-01 `06691b4`、SPEC-02 `83cbf6e`、SPEC-04 `6e30a89`/`fae75d7`、SPEC-05 `ed5c52e`/`4e50161`、SPEC-03 `cbe716a`、SPEC-06 `97be555`、SPEC-07 `1798346`/`6b98ea1`、SPEC-08 `806958a`；push 由用户本机终端执行。

## Blockers / limitations
- 当前 sandbox 禁止 IPv4 loopback `socket.bind`，所以本轮验证 Dashboard projection 与启动命令，未伪造 live socket/browser 成功。
- 当前 sandbox 不具备可验证的真实 Claude/Codex nested agent rehearsal；builtin 是真实 subprocess/受控 domain 流程的稳定离线 runner，但不是外部 LLM agent。外部 smoke 留 SPEC-09 普通 provider 环境完成。
