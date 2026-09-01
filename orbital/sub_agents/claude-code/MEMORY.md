# MEMORY for claude-code

This is your long-term memory across dispatches in this project.
Append entries below.

---

- 2026-09-01 SPEC-09 收尾：交付边界三处同源清单（.gitignore / tests/test_delivery_contract.py 排除 / scripts/verify_clean_copy.py `_ignored`），改一处必须同步三处；orbital/sub_agents/*/ 白名单只留 MEMORY.md。
- verify_clean_copy.py 的 source fingerprint 覆盖版本化 memory 文件——它运行期间不要并发编辑 orbital/*.md，否则误报 "source repo fingerprint changed"。
- 审计前任 agent 自报数字必须先复测（dsh 自报 112/112，实测 1F/111P）；沙箱限制（如 loopback EPERM）逐 session 变化，旧 LESSONS 的环境结论要重验再引用。
