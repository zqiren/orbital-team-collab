# 00 — 作业简报 (Assignment Brief)

> 交付状态：SPEC-00～09 已完成；最终产品入口与可运行 quickstart 见根 `README.md`。下文保留最初作业目标与成功标准，作为验收依据。

> 一句话：为 Kimi PM 面试作业产出「Orbital Team Feature」产品规划 repo。
> Kimi 的质疑是全文的靶心——**「Orbital 和 Claude Code / Codex 太像了」**。

## 作业本质

- 表面任务：给 Orbital（https://github.com/zqiren/Orbital）规划 Team Feature。
- 实际考察：能否把一个「个人效率工具」升级为「团队产品」的故事讲完整——**用户是谁、为什么是现在、凭什么 Orbital 来做、做成什么样、怎么落地**。
- 评审方是 Kimi（Moonshot AI）。Orbital 已内置 Moonshot/Kimi 作为 14 家 LLM provider 之一（README 实证，2026-09-01 抓取），这是天然的亲和点，可作为细节彩蛋而非主论点。

## 已知约束

| 约束 | 来源 |
|---|---|
| 要做 demo，但 demo 后置：基础文档沉淀完成并获用户确认前不动工 | 用户指示（2026-09-01） |
| 文档中文为主，术语与 repo 名用英文 | 项目约定 |
| 竞品信息必须联网核实，标注来源与日期 | 项目规则（防知识过时） |
| 论据优先一手：本项目本身就运行在 Orbital 内 | 项目独特优势 |

## 成功标准

1. **立论成立**：Team Feature 不是功能堆砌，而是 Orbital「project as unit」逻辑的自然延伸——先做成了 session→project 的升维，下一个升维是 project→team。
2. **论据一手**：大量使用「我们就在 Orbital 里运行」的机制证据 + 官方 README/源码；竞品信息全部联网核实并标注日期。
3. **评审可读**：README 电梯陈述 30 秒讲清；PRD 可执行；路线图有优先级逻辑（不写流水账）。
4. **有 demo**（后置）：一个可演示的最小原型，回扣 PRD 里的旗舰 feature。

## 交付 repo 规划（草案，待用户确认命名）

```
README.md               电梯陈述 + 产品一页图
docs/
  competitive-analysis.md   Orbital vs Claude Code vs Codex vs 其他
  user-scenarios.md         目标团队画像与核心场景
  prd.md                    2–3 个旗舰 Team Feature 详案
  roadmap.md                分期路线图 + 北极星指标
demo/                      最小可演示原型（后置）
```

## 工作流

- **P0 基础研究**（进行中）：Orbital 现状盘点（00/01 号文档）+ 竞品联网核实（research/ 目录）。
- **P1 综合分析**：竞品综合对比（02）、用户场景（10）、Team Feature 方向池与优先级（11）。
- **P2 规划文档**：PRD 详案、路线图、README 电梯陈述。
- **P3 demo**（后置，需用户确认 P1/P2 后才动工）。
- **P4 repo 整理**：命名建议 → GitHub 建仓 → 推送。

## 风险与对策

| 风险 | 对策 |
|---|---|
| 竞品迭代极快，知识过时 | 全部联网核实 + 标注来源日期；研究原文存 docs/research/ |
| 「Team feature」含义两可：人与人的团队 vs agent 之间的团队 | 两个维度都分析，PRD 明确聚焦点 |
| Orbital 单人设计（local-first 文件态）与多人共享存在张力 | 用两层文件模型正面回答：durable knowledge/config 经 Git 传播，本地 runtime 支撑看板与日志；跨机器 runtime 同步进入 Team Cloud roadmap |
