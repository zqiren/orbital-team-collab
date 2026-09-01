<!--format PROJECT_STATE is what is true NOW: current focus, in-progress work, blockers, next steps. Overwrite stale lines; never append dated history. Every line must be understandable without this session's context: concrete names, no unexplained shorthand, no cross-references by list number. [user] flag — one judgment per line: does this need the user (their decision, their action, or something they'd be sorry to miss — including things they assigned to themselves)? If yes, insert [user] after the list marker of the line where the fact already lives: `- [user] <text>` or `3. [user] <text>`. Flagging marks a line, never creates one: one fact = one entry, never duplicated into another section. A dated commitment needing no decision is `[due:YYYY-MM-DD]` (shows on the calendar). Machine attributes (id, created, touched, resolved) live in a daemon-managed mem-comment on the next line — never write or edit these comments; leave them exactly where they are. Never auto-decide: spending money, sending external messages as the user, or irreversible/destructive acts are always surfaced, whatever the autonomy setting. Write timeless ("due Jul 28", never "tomorrow"). A line whose mem-comment carries resolved:<date> is settled — on consolidation rewrite it as the completed fact or drop it; never re-open or re-flag it. CLOSE THE LOOP THE SAME TURN: the moment the user answers a flagged line, decides it, or does it, remove the [user] flag from that line in this turn — rewrite the line as the settled fact (`- Chose option A.`) and leave the mem-comment alone. You are the only reader who can see both the flag and the user's answer; consolidation runs later, sees a truncated window, and cannot do this for you. A flagged line you leave behind after it is answered keeps nagging the user for something they already gave you. Never flag a question you asked during this session — flag the decision that is still genuinely open, written so someone who was not here can act on it.-->
# PROJECT_STATE

## 当前阶段
SPEC-09 收尾与交付终审已由 claude-code 完成（dsh 产出经逐项审计后保留并修复）：接手基线 1 failed/111 passed，失败源为交付扫描测试误扫机器管理 runtime（`orbital/output/` 与 dsh harness 写入 `orbital/sub_agents/dsh/` 的 `.yml`/session 文件）；修复扫描/clean-copy/gitignore 三处共同排除边界（sub_agents 白名单只版本化 MEMORY.md），未弱化断言。终审结论：可交付。全部 SPEC-09 改动仍未 commit，待主 session 复测后最终 checkpoint。

## 本轮完成（2026-09-01，claude-code 收尾实测）
- 根工作树全量 `python3 -m pytest -q` = 112 passed in 111.55s；`scripts/verify_clean_copy.py --dashboard-policy allow` ok:true（copy 内 112 passed in 111.81s、builtin demo 40 events/2 Done Jobs/2 knowledge summaries、replay simulated、reset 后 source fingerprint 未变）。
- 真实 loopback 证据升级：本环境 `127.0.0.1` bind 成功，并完成真实 socket 上 `GET /`（200）与 `GET /api/bootstrap`（200）smoke；此前记录的 bind EPERM 在收尾环境不复现，docs/38、README 限制已按实测改写。
- dsh 产出审计通过：README 三级结构与 quickstart 命令与实现一致、交付树 0 死链、THIRD_PARTY attribution 准确（filelock=Unlicense、jsonschema=MIT）、docs/20/21/22/30/37 收敛合理；SPEC-09 Completion Record 已用真实数字重写（dsh 自报 112/112 当时不实）。
- 隐私扫描：交付树无用户绝对路径、无用户名/email、无 secret/token/key 模式命中。

## 下一步
1. claude-code 已完成 SPEC-09 收尾 + 交付终审（结论：可交付）；主 session 独立复测后做最终 checkpoint（feat + chore），再向用户报告
  <!--mem id:bfc709 created:2026-09-01 touched:2026-09-01-->
2. [user] 用户决定何时 push 或发送给 Kimi；发送外部对象仍需单独明确授权。
  <!--mem id:df866e created:2026-09-01 touched:2026-09-01-->
3. 可选环境证据：普通本机浏览器可视化 walkthrough（bind 与 HTTP GET smoke 已在收尾环境真实通过），以及已登录 provider 中的 external Codex/Claude Code Manager/Member rehearsal；不得用 builtin/replay 替代。
4. Git checkpoint 链截至本轮前：SPEC-00 `902a870`、SPEC-01 `06691b4`、SPEC-02 `83cbf6e`、SPEC-04 `6e30a89`/`fae75d7`、SPEC-05 `ed5c52e`/`4e50161`、SPEC-03 `cbe716a`、SPEC-06 `97be555`、SPEC-07 `1798346`/`6b98ea1`、SPEC-08 `806958a`。

## Blockers / limitations
- loopback bind EPERM 在收尾环境不复现（bind + HTTP GET smoke 真实通过）；浏览器级可视化 walkthrough 仍留普通本机。更严格 sandbox 下 verifier 用 `--dashboard-policy allow` 如实记录失败。
- 编排者现状：claude-code 可用（主用）；codex 用量 2026-09-02 02:45 重置；cursor 需付费；dsh api key invalid 已弃用。Codex CLI/manifest doctor 可用但 nested provider 曾在 sandbox EPERM。builtin 是真实 subprocess/受控 Git/domain 的 live-scripted runner，不是 external LLM agent。
- 非 POSIX 权限与 runner process-tree 行为未做实机验证；根 repo 尚未声明开源许可证；README clone URL 在用户 push origin 前不可用。
