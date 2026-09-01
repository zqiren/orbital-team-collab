# 最终验证与演示录制

本文面向最终评审和维护者，给出不依赖聊天历史的 clean-copy、Dashboard、live/replay 与录制
步骤。产品论点与 5 分钟 walkthrough 见根 [README](../README.md)。

## 自动验证矩阵

```bash
python3 scripts/verify_clean_copy.py --dashboard-policy require
```

脚本只读取 source repo，并在安全创建的临时根中完成：

1. 排除 `.git`、cache、build、Orbital runtime/session/ledger/tool output 后复制交付文件。
2. 初始化新的 local Git repo，创建隔离的 `venv --system-site-packages`。
3. `pip install -e . --no-deps --no-build-isolation`。
4. `python -m pytest -q`、`teamctl/teamd/demo --help`。
5. builtin doctor、setup、双成员 start、status、replay、reset。
6. 确认两个 seed Tasks/Integration Jobs Done、两份 knowledge summaries、replay 明确 simulated。
7. 确认 clean copy `git status --porcelain` 为空，并比较 source tree fingerprint 未变化。

`--dashboard-policy require` 会真实尝试 IPv4 loopback bind，失败即验证失败。最终交付验证在
当前环境中 bind 实际成功；对确实禁止 loopback bind 的更严格 sandbox，可用
`--dashboard-policy allow`：仍然尝试 bind 并记录实际错误，但只允许其作为明确 limitation，
不会把 projection/handler tests 写成 browser success。`--keep` 可保留临时根供人工检查。

## 手工 5 分钟 walkthrough

按 README Quickstart 完成 setup/start 后：

1. Dashboard 初始页指出 Apollo Project、demo-manager、Alice/Bob 与三类工作对象。
2. Activity 展示 `task.claimed`、`report.submitted`、`integration.merged`、
   `knowledge.applied`、`integration.completed`。
3. Tasks 中 `apollo-T-0001/0002` 为 Done；IM Promote 的第三项仍是 Draft，blocking Question 可见。
4. Integration/Run 区显示两个串行 Job；Knowledge 区显示两份 summary 和 PROJECT_STATE preview。
5. canonical repo 中运行 `git --no-pager log --oneline --decorate -8`，说明 code merge 与 knowledge
   commit 是独立 commit，且没有 remote push。
6. 执行 reset，展示仅精确 marker 绑定的临时根被删除，交付 repo `git status` 未污染。

## External runner rehearsal

```bash
python3 demo/scripts/team_demo.py doctor --runner codex
python3 demo/scripts/team_demo.py doctor --runner claude-code
```

只有 doctor 可用、runner 实际写出 schema-valid result、受控 code merge 和 knowledge apply 全部
完成，才能记录为 external live success。CLI 不存在、未登录、nested sandbox EPERM 或 timeout 都
必须保留 stderr/result 并标为失败/未覆盖。`builtin` 和 replay 都不能替代这条证据。

## 截图/录屏清单

普通本机启动 Dashboard 后，可使用系统截图/录屏工具捕获以下五帧，不需要额外前端工具：

1. setup 后：两个 Ready Tasks + Potential Task + Open Question。
2. 双成员 report 后：Submitted/Integrating 与 activity。
3. 完成后：两个 Done Tasks/Jobs。
4. Knowledge view：summary、source commit、独立 knowledge commit 与 preview。
5. terminal：clean `git status`、reset 精确路径和 replay 的 `simulated-replay` 标签。

录制时不要展示 home path、provider token、真实聊天内容或 private run logs。若需分享素材，先裁剪
到 demo 临时路径并复核 metadata；本 repo 不提交包含个人路径的录屏产物。

## 已验证与环境限制

- 最终 root test matrix：`112 passed in 111.55s`；disposable clean-copy matrix：copy 内
  `112 passed in 111.81s`，随后完整 builtin demo（40 events、2 Done Integration Jobs、2 knowledge
  summaries、IM Promote Task 保持 Draft）、replay simulated 标记、reset、clean `git status` 与
  source fingerprint 未变化均通过。
- 自动测试覆盖 Python 3.13/macOS sandbox 下的 file runtime、双进程/双 worktree、Manager pipeline、
  knowledge、IM fixture、Dashboard handler/projection 与 clean-copy demo。
- 最终验证中 `127.0.0.1` bind 真实成功，并完成真实 socket 上的 `GET /`（200）与
  `GET /api/bootstrap`（200，actor 绑定 JSON）smoke；浏览器级可视化 walkthrough 仍建议在普通
  本机执行。更严格的 sandbox 可能对 bind 返回 EPERM，届时用 `--dashboard-policy allow` 如实记录。
- nested Codex provider 初始化曾在 sandbox 返回 EPERM，Claude CLI 不可用；external LLM rehearsal
  未伪造，仍待具备已登录 agent CLI 的环境复测。
- 无 Node/frontend build；静态 HTML/CSS/ES modules 由 Python package data 交付，相关 lint 为静态安全扫描。
