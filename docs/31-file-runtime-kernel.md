# File Runtime Kernel

SPEC-01 提供 Python 3.11+ `orbital_team` package 与最小 `teamctl` 入口。
运行时依赖仅 `jsonschema >=4,<5` 和 `filelock >=3,<4`，统一声明在
`pyproject.toml`。

## 安装与运行

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/teamctl init --project Apollo --workspace . --seed demo/seed
.venv/bin/teamctl status --project apollo
.venv/bin/teamctl reset --runtime-only --project apollo
```

不使用版本化 demo seed 时，reset 必须显式确认：

```bash
teamctl reset --runtime-only --project <slug> --yes
```

runtime 始终解析到 `<git-common-dir>/orbital-team/`，因此 linked worktree
天然共享，且不会出现在 repository worktree status 中。POSIX 上 runtime
目录以 `0700` 创建，文件（含锁和经 storage helper 写入的 log）以 `0600`
创建。

锁通过 `filelock` 使用 OS advisory lock：进程崩溃后 lock 文件可以残留，
但 owner 释放或失去 OS lock 后即可复用。等待活锁超过有界 timeout 返回
`E_LOCK_TIMEOUT`。JSONL reader 会保留并报告不完整的尾记录，绝不静默
重写审计日志。

`IdempotencyGuard` 以 request key 的 SHA-256 保存 operation。私有 journal
record 保留原始 key、payload hash、稳定 event ID、object refs、目标
revision/hash、`Prepared`/`Committed` 状态和稳定 result；同 key 搭配不同
payload 或 target 时返回 `E_IDEMPOTENCY_CONFLICT`。

## 开发验证

测试不需要额外依赖：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

测试在 OS 临时目录创建隔离 Git repository 和 linked worktree。没有 POSIX
permission bits 的平台会跳过 mode 断言；本次 macOS 验证环境未覆盖 Windows
的持锁 reset 行为。
