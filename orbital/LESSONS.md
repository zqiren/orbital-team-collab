<!--format LESSONS entries: numbered durable heuristics and playbooks. Add on error recovery or non-obvious workaround; keep real playbooks intact.-->
# LESSONS

### 2026-09-01 — error-recovery
**What happened:** `git clone` 在沙箱内连续失败两次：先拒读 `~/.gitconfig`；加 `GIT_CONFIG_GLOBAL=/dev/null` 后仍报 "Invalid path '/Users': Operation not permitted"（对象下载阶段）。
**Do instead:** 直接 curl 官方 tarball：`curl -sfL https://github.com/<org>/<repo>/archive/refs/heads/main.tar.gz`（github.com 已在 allowlist；branch 不对再试 master），解压 `tar xzf x.tar.gz -C <dir> --strip-components=1`。
**Keywords:** git, clone, sandbox, tarball, github

### 2026-09-01 — zsh-special-variable
**What happened:** 在 zsh 验证脚本中使用 `for path in ...`，覆盖了 zsh 特殊数组 `$path`（与 `$PATH` 绑定），导致同一 shell 后续暂时找不到 `rg`、`git` 等命令；文件与系统 PATH 均未被持久修改。
**Do instead:** zsh 循环变量使用 `artifact_file`、`target_file` 等任务专用名称，避免 `path`、`status` 等 zsh special parameters；若已触发，开启新 shell 或重新导出 PATH 后重跑验证，不能采信受影响 shell 里的扫描结果。
**Keywords:** zsh, path, PATH, shell, verification
