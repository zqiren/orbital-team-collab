# 34 — Manager Knowledge Compilation

SPEC-05 在代码 merge 后继续事件驱动 Manager pipeline：把 immutable Report、
merged diff、Task 契约和当前项目记忆编译成结构化 Knowledge Proposal，经确定性
校验后，才用一个独立的本地 Git commit 更新 canonical memory。

## Pipeline

```text
integration.merged
→ knowledge.prepared / Knowledge Pack
→ short-lived Manager knowledge run
→ knowledge.proposed
→ knowledge.validated
→ knowledge.applied
→ task.completed + integration.completed
```

最终 apply 成功前，Task 始终保持 `integrating`。`awaiting_knowledge` Job 不占用
project integration slot，因此后续 Report 可继续完成代码集成。

## 输入与持久化结果

Knowledge Pack 记录 Job、Report、Task ID、merged diff 摘要，以及每个现有
canonical memory 文件的 SHA-256 基线。Manager run 同时读取 immutable Report、
Task snapshot 和以下四个文件：

- `orbital/PROJECT_STATE.md`：当前事实、进行中工作、blocker 和下一步；
- `orbital/DECISIONS.md`：已落地且跨 session 有效的决定与理由；
- `orbital/LESSONS.md`：去重后的非显而易见 gotcha 与恢复 playbook；
- `orbital/INDEX.md`：每个 durable path 一条简洁导航。

普通实现细节、临时调试和重复 Report 文本不进入 canonical knowledge。
`orbital/instructions/` 可作为只读上下文，但不在 v1 自动 apply allowlist 中。

本地 runtime artifact 位于：

```text
<git-common-dir>/orbital-team/projects/<slug>/
├── knowledge-packs/
├── knowledge-proposals/
├── knowledge-summaries/
└── runs/
```

只有四个 canonical Markdown 文件及其本地 commit 属于 Git 版本化 durable layer。

## Proposal 与 apply

Proposal 对每个 allowlisted path 最多包含一个 full-file patch。现有文件使用
`operation=updated` 和 Pack 中的精确 hash；缺失的新文件使用
`operation=created` 和 `base_sha256=null`。v1 拒绝删除或移动这四个 canonical
memory 文件。

受控命令如下：

```bash
teamctl manager knowledge propose <job-id> --summary <text> [--patch '<json>']
teamctl manager knowledge validate <proposal-id>
teamctl manager knowledge apply <proposal-id> [--request-id <id>]
```

配置的 Manager runner 通常调用 `propose`，再由 `teamd` 校验并 apply 其结构化
结果。这些命令也可用于恢复和检查；它们始终复用共享 domain/storage 层，不授权
直接写 runtime JSON。

Apply 取得 project lock 和 SPEC-04 Git mutation lock，重新校验 source merge
ancestry 与每个 memory hash，原子写入 full-file 结果，并且只 stage Proposal 指定
的 allowlisted path。随后创建以 Proposal 命名的独立本地 commit；不 amend code
merge，也绝不 remote push。

Immutable Knowledge Change Summary 同时记录 `source_commit`、
`knowledge_commit`、Proposal、Report 和逐路径 change category。Dashboard 读取
该 summary，不从 Markdown diff 猜测第二套状态。

## No-change

若 merged work 没有可沉淀的 durable knowledge，Manager 仍创建可追溯的
`patches=[]` Proposal。Validation 重新校验完整 memory hash map；apply 写入
`changes=[]`、`knowledge_commit=null` 的 summary，不创建空 Git commit。

## 冲突与恢复

- Pack 或 Proposal 之后 memory 发生变化时，validation/apply 将旧 Proposal 标为
  `stale` 并返回 `E_STALE_PROPOSAL`；不会覆盖新文件，新的 Manager run 必须重新
  读取并编译。
- 事实与现有决定冲突，或需要 Human authority 时，Job 进入 `blocked` 且
  `block_kind=knowledge`，并关联一个 Open Question；Task 保持 `integrating`。
- 问题回答后产生 `question.answered` 与 `knowledge.resume_requested`。所有关联的
  blocking question 解决后，domain recovery 将 Job 恢复为 `awaiting_knowledge`，
  `teamd` 再从当前文件启动新的短生命周期 run。
- canonical workspace 存在无关未提交改动时，apply 返回
  `E_DIRTY_WORKSPACE`，并阻塞等待明确的 Human 处理决定。
- 相同 request ID 的 propose/apply 幂等。若 knowledge commit 已成功、runtime
  finalize 前崩溃，恢复流程会定位该 Proposal commit，确认它只改动预期 path，
  再补齐 summary 与状态事件，不创建第二个 commit。

## Guardrails

- Runner policy 只暴露受控 Proposal command，不暴露裸 `git commit`、
  `git push`、`git merge`、staging 或任意 patch 执行。
- Patch path 必须精确命中 allowlist，不能经过 symlink 或逃出 canonical workspace。
- Validator 保留每个 memory 文件的 format-contract comment、唯一 H1、结尾换行和
  大小上限；INDEX 额外只允许 heading、comment 与 `path — description` bullet。
- machine-managed runtime、sessions、ledger、tool results 和 sub-agent JSONL
  transcript 不会被编译或修改为 canonical knowledge。
- 只有 Proposal apply、Task Done 与 Job Done 全部持久化后才发出
  `integration.completed`；Proposed 或 Validated 都不代表完成。
