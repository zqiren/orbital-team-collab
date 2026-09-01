# 32 — `/team` Member Workflow

SPEC-02 在 SPEC-01 的 Git common-dir runtime 上实现成员命令。CLI 与后续 slash/Skill adapter 共用 `MemberWorkflow` domain service；adapter 不直接读写 JSON。

## 身份与 worktree 绑定

成员在自己的 named-branch worktree 内执行 join：

```bash
teamctl member join --project apollo --member alice --agent codex
```

join 自动记录当前 worktree 根目录和当前 branch，并验证它与 Project canonical workspace 使用同一个 Git common dir。后续 claim/start/block/report 不接受可冒充的 `--member`；actor 由当前 worktree 的唯一 Member binding 推导。切换到与 binding 不同的 branch 会返回 `E_WORKTREE_MISMATCH`。

## Confirmed Task 生命周期

Human/Manager 可先创建 Draft，再显式置 Ready：

```bash
teamctl task create --project apollo --title "Add health endpoint" \
  --description "Implement GET /health" \
  --acceptance "GET /health returns 200" \
  --path src/health.py --label backend
teamctl task ready apollo-T-0001
```

成员流程：

```bash
teamctl claim --project apollo apollo-T-0001
teamctl task start apollo-T-0001
teamctl task status apollo-T-0001
teamctl task block apollo-T-0001 --reason "Waiting for an API decision"
```

claim 的 resolve 顺序为 Task ID exact、normalized title exact、ID/title/label token substring。零匹配返回 `E_TASK_NOT_FOUND`；多匹配返回按 Task ID 排序的候选和 `E_TASK_AMBIGUOUS`，两者都不改变 store。唯一匹配后，command 在 project lock 内重新 resolve 并检查 Ready、assignee、dependencies 与 Open/Deferred blocking question，再写 Task 和 `task.claimed` event。

claim 成功返回最大 32 KiB 的 Context Pack（可配置，硬上限 64 KiB），包括 Task、dependencies、Open Questions、Member/branch、Report 要求和四个 canonical memory 路径的受限摘要。发生裁剪时返回 `truncated=true`、`omitted_paths` 和 `omitted_count`。

## Report

Report 只允许 assignee 从 `in_progress` 提交；`claimed → submitted` 返回 `E_INVALID_TRANSITION`。先在成员 worktree commit，再提交：

```bash
teamctl report submit apollo-T-0001 \
  --summary "Implemented GET /health" \
  --validation '{"command":"python -m unittest","outcome":"passed","summary":"all tests passed"}'
```

Report 自动绑定当前 named branch 的 HEAD，并记录 canonical HEAD 与 member HEAD 的 merge-base、changed files 和 `git diff --stat`。可用 `--commit <full-hash>` 做 expected-HEAD 校验；非当前 HEAD 返回 `E_COMMIT_MISMATCH`。每个 `--validation` 都是符合 `#/$defs/validation` 的 JSON object。

Report 文件写入 `projects/<slug>/reports/<report-id>.json`，创建后不可变。Task 和 Report 持久化后才追加 `report.submitted`。相同 `(task, commit)` 的重复提交返回原 Report，不重复 event；Manager integration 由 SPEC-04 消费该 event。

## 其他读取命令

```bash
teamctl task status
teamctl question list --project apollo
```

无 Task ID 的 status 返回当前 worktree Member 在所有 logical projects 中已分配的 Task；question list 返回 Project 的 Open Question store 投影。读取命令不产生 event。

## 稳定错误

本阶段实现 `E_MEMBER_NOT_FOUND`、`E_TASK_NOT_FOUND`、`E_TASK_AMBIGUOUS`、`E_TASK_NOT_READY`、`E_TASK_ALREADY_CLAIMED`、`E_BLOCKING_QUESTION`、`E_DEPENDENCY_INCOMPLETE`、`E_INVALID_TRANSITION`、`E_FORBIDDEN_ACTOR`、`E_WORKTREE_MISMATCH`、`E_COMMIT_MISMATCH` 与 `E_VALIDATION_FAILED`，exit code 与 `docs/22-protocol.md` 一致。所有 mutation 支持 `--request-id`；adapter 重试必须复用同一 ID。
