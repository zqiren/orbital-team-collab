<!--format LESSONS entries: numbered durable heuristics and playbooks. Add on error recovery or non-obvious workaround; keep real playbooks intact.-->
# LESSONS

### 2026-09-01 — error-recovery
**What happened:** `git clone` 在沙箱内连续失败两次：先拒读 `~/.gitconfig`；加 `GIT_CONFIG_GLOBAL=/dev/null` 后仍报 "Invalid path '/Users': Operation not permitted"（对象下载阶段）。
**Do instead:** 直接 curl 官方 tarball：`curl -sfL https://github.com/<org>/<repo>/archive/refs/heads/main.tar.gz`（github.com 已在 allowlist；branch 不对再试 master），解压 `tar xzf x.tar.gz -C <dir> --strip-components=1`。
**Keywords:** git, clone, sandbox, tarball, github

### 2026-09-01 — git-sandbox-commit-push
**What happened:** 子 agent 报告「.git 只读、DNS 不通、无法 commit/push」；主 session 实测网络正常（curl github.com 返回 200），commit 失败仅因 git 读 `~/.gitconfig` 被沙箱拒绝。push 另因 HTTPS 无凭据失败：沙箱无 gh CLI、`~/.ssh` 不可读、osxkeychain 静默无凭据，用户拒绝提供 PAT（request_credential 被 DENIED，勿重试）。
**Do instead:** 本仓所有 git status/add/commit/log 加 `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null`（identity 走 repo 本地 config 的 zqiren / zqzqzqr0@gmail.com，不受影响；`~/.config/git/ignore` 警告无害）。push 沙箱内不可行，交用户本机终端执行 `git push -u origin main`。子 agent 的环境失败结论先在主 session 复测再采信。
**Keywords:** git, sandbox, GIT_CONFIG_GLOBAL, commit, push, credential, PAT

### 2026-09-01 — zsh-special-variable
**What happened:** 在 zsh 验证脚本中使用 `for path in ...`，覆盖了 zsh 特殊数组 `$path`（与 `$PATH` 绑定），导致同一 shell 后续暂时找不到 `rg`、`git` 等命令；文件与系统 PATH 均未被持久修改。
**Do instead:** zsh 循环变量使用 `artifact_file`、`target_file` 等任务专用名称，避免 `path`、`status` 等 zsh special parameters；若已触发，开启新 shell 或重新导出 PATH 后重跑验证，不能采信受影响 shell 里的扫描结果。
**Keywords:** zsh, path, PATH, shell, verification

### 2026-09-01 — common-dir-lock-reset
**What happened:** linked worktree 的 `.git` 是指向 worktree metadata 的文件，只有 `git rev-parse --path-format=absolute --git-common-dir` 才会让 manager workspace 与所有 worktree 落到同一 runtime。`filelock` 的 lock 文件在进程退出后仍可残留，但真正的 OS advisory lock 已释放；按文件存在时间删除“stale lock”既无必要也会误伤活锁。
**Do instead:** 所有 runtime 路径只从 Git common-dir 解析；reset 同时验证 common-dir 直属 `orbital-team/`、非 symlink、安全 marker 与 registry project，再接受 `--yes`/demo marker。锁文件可以保留并复用，活锁只通过 bounded timeout 报 `E_LOCK_TIMEOUT`，不得按 mtime 强删。
**Keywords:** git-common-dir, worktree, filelock, stale-lock, reset, symlink

### 2026-09-01 — json-schema-fragment-validation
**What happened:** 构造 `$defs/memberStore` validator 时误把 schema bundle 顶层 `oneOf` 一起保留；四种空 store 结构相同，因此同时匹配多个分支并被错误拒绝。另一个首轮错误是确定性 UUIDv5 不符合冻结的 UUIDv4 schema pattern。
**Do instead:** fragment validator 只携带 `$schema`、`$defs` 与目标 `$ref`，不继承 bundle 顶层 `oneOf`；需要稳定 event ID 时从 hash 派生 16 bytes 后显式设置 RFC 4122 v4/variant bits，并继续让 schema 做最终校验。
**Keywords:** jsonschema, oneOf, defs, fragment, uuid4, idempotency

### 2026-09-01 — sandbox-processpool-semaphore
**What happened:** Python 3.13 的 `ProcessPoolExecutor` 初始化会调用 `os.sysconf("SC_SEM_NSEMS_MAX")`，当前 macOS sandbox 对该查询返回 `PermissionError: Operation not permitted`，导致并发 claim 测试尚未启动 worker 就失败；这不是 filelock 或业务并发失败。
**Do instead:** 需要真实跨进程竞争时，用两个 `subprocess.Popen` 启动独立 Python interpreter，让它们等待同一个临时文件 barrier 后同时调用 domain command；显式传入 `GIT_CONFIG_GLOBAL=/dev/null`、`GIT_CONFIG_SYSTEM=/dev/null` 与 repo `PYTHONPATH`，再分别收集结构化 stdout/exit code。
**Keywords:** python, ProcessPoolExecutor, semaphore, sandbox, subprocess, concurrency, barrier

### 2026-09-01 — pytest-rootpath-parent-eperm
**What happened:** 沙箱内任何 pytest 运行（含显式 `pytest tests/`）收集阶段即报 `PermissionError: ... '/Users/keanezhou/Desktop'`。真实根因：pytest 8.3 收集 rootpath（=仓库根）的 Dir 节点时，`Session._collect_path` → `gethookproxy(rootpath.parent)` → `PytestPluginManager._getconftestmodules(Desktop)` → `_get_directory` 对 Desktop 调 `is_file()` stat，被沙箱拒绝；与 rootdir 探测无关，仅在仓库根放 pytest.ini 无效。
**Do instead:** 仓库根 `conftest.py` monkeypatch `PytestPluginManager._getconftestmodules`：捕获 `PermissionError` 返回空 conftest 列表（正常机器不会触发该分支）；根目录 `pytest.ini` 设 `testpaths = tests` 钉住收集范围、`pythonpath = src` 让 src 布局免安装可导入。统一用 `python3 -m pytest -q` 跑全量。
**Keywords:** pytest, rootpath, gethookproxy, conftest, sandbox, EPERM, collection
