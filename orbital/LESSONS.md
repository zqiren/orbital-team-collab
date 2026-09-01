<!--format LESSONS entries: numbered durable heuristics and playbooks. Add on error recovery or non-obvious workaround; keep real playbooks intact.-->
# LESSONS

### 2026-09-01 — error-recovery
**What happened:** `git clone` 在沙箱内连续失败两次：先拒读 `~/.gitconfig`；加 `GIT_CONFIG_GLOBAL=/dev/null` 后仍报 "Invalid path '/Users': Operation not permitted"（对象下载阶段）。
**Do instead:** 直接 curl 官方 tarball：`curl -sfL https://github.com/<org>/<repo>/archive/refs/heads/main.tar.gz`（github.com 已在 allowlist；branch 不对再试 master），解压 `tar xzf x.tar.gz -C <dir> --strip-components=1`。
**Keywords:** git, clone, sandbox, tarball, github
