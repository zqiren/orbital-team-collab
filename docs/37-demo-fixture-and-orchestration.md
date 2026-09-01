# 可重置多 worktree Demo

SPEC-08 把已经交付的 runtime、Member workflow、IM fixture、teamd、knowledge
workflow 和 Dashboard projection 组装成一个完全离线的 Apollo 演示。演示只在安全创建的
临时 Git 仓库中写入；交付 repo 只作为版本化 fixture 与 Python package 来源。

## 最短演示

```bash
python3 demo/scripts/team_demo.py doctor
python3 demo/scripts/team_demo.py setup
# 从上一条 JSON 输出复制精确的 root 绝对路径
python3 demo/scripts/team_demo.py start --root /exact/orbital-team-demo-path
python3 demo/scripts/team_demo.py status --root /exact/orbital-team-demo-path
python3 demo/scripts/team_demo.py reset --root /exact/orbital-team-demo-path
```

`setup` 创建 canonical repo、`demo/alice` 与 `demo/bob` linked worktree，安装 generic
Member Skill，使用 `demo/seed/` 初始化两个 Ready Tasks，并通过 fixture provider ingest
一个 Potential Task 和一个 blocking Open Question。三类工作对象保持分离；`start` 只把
Potential Task triage/promote 成 Draft，不会自动把它变成 Ready 或 claim。

Alice/Bob 是等待同一临时 barrier 的两个独立 Python 进程。它们在各自 linked worktree
内通过 `MemberWorkflow` 推导 actor，claim/start、提交不同文件的 commit/report。随后
`teamd` 串行运行 `builtin` Manager：代码只经 `manager merge` 受控命令合并，knowledge
只经 `manager knowledge propose` 受控命令进入 SPEC-05 apply，并形成独立本地 knowledge
commit。成功输出会明确标记 `mode: live-scripted`，Dashboard 投影中两个 Task/Job 均为
Done，且 `knowledge_summaries` 为 2。

## Dashboard

`status` 返回精确 URL 和启动命令。普通本机可运行：

```bash
python3 -m orbital_team dashboard --workspace /exact/root/canonical \
  --actor human:demo-manager --host 127.0.0.1 --port 8765
```

服务端沿用 SPEC-07，只允许 IPv4 loopback。当前受限 sandbox 禁止 `socket.bind`，因此自动
验证直接读取同一个 `DashboardProjection`，没有把内存 transport 冒充真实浏览器 smoke。

## Runner 与 replay

默认 `builtin` runner 不需要网络或外部 agent CLI，同时覆盖 integration 与 knowledge
phase。`doctor --runner codex` 或 `doctor --runner claude` 会检查相应 manifest、可执行文件
及两个 phase；缺失时 `setup --runner ...` 在创建临时根之前返回
`E_RUNNER_UNAVAILABLE`。外部 runner 选择只改临时目录中的 seed 副本，不修改版本化 seed。

```bash
python3 demo/scripts/team_demo.py replay
```

replay 只输出 `mode: simulated-replay`、`live_success: false` 的事件/UI fixture。它不是 live
agent 成功证据，也不写 runtime。

## Reset 安全

`reset` 需要绝对路径、非 symlink 目录，以及内容绑定该 resolved root 的
`.orbital-team-demo-root` 私有 marker。它先调用已有 `RuntimeManager.reset_runtime` 再删除
这个精确临时根；无 marker、marker 被复制到其他目录、home/root 或宽泛路径都会拒绝。
成功 cleanup 不可恢复，输出包含被删除的精确路径。

## 故障演示与验证

`start --member-crash bob` 在 Bob start 后注入确定性崩溃，输出 `ok: false`，不会冒充完整
成功；Alice 仍可完成，Bob Task 保持 In Progress。专项测试还以 injected flaky runner
验证第一次无结果、teamd Retryable/requeue 后仅完成一次的恢复路径。

```bash
python3 -m pytest -q tests/test_demo_orchestration.py
python3 -m pytest -q
```
