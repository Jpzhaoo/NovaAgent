# NovaAgent 架构决策记录

本目录保存 NovaAgent 的架构决策记录（Architecture Decision Record，ADR）。ADR 用于说明一个重要架构选择的背景、决策、替代方案、后果和验证方式；产品需求仍以 [`docs/PRD.md`](../PRD.md) 为准。

## 状态定义

| 状态 | 含义 |
|---|---|
| `Proposed` | 已形成方案，等待架构评审或实现验证 |
| `Accepted` | 已评审通过，是当前实现必须遵守的约束 |
| `Deprecated` | 仍可能存在于旧实现中，但不得用于新代码 |
| `Superseded` | 已由新的 ADR 替代 |
| `Rejected` | 方案经评审后未采用 |

PRD 当前为 Draft v1.0，因此由其提炼的首批 ADR 均从 `Proposed` 开始。评审通过后只修改状态和决策日志，不重写历史背景。

## ADR 索引

| 编号 | 标题 | 状态 | PRD 基线 |
|---|---|---|---|
| [ADR-0001](0001-core-boundaries-and-typed-contracts.md) | Core 包边界与类型化端口 | Proposed | FR-01、FR-07、5.1、5.2 |
| [ADR-0002](0002-unified-turn-lifecycle-and-graph-runtime.md) | 基于 Graph Runtime 的统一 Turn 生命周期 | Proposed | FR-02、FR-02A、FR-06、5.3–5.6 |
| [ADR-0003](0003-centralized-tool-security-and-approval.md) | 集中式工具安全策略与审批网关 | Proposed | FR-04、FR-05、6.2 |

## 使用规则

1. 对跨包依赖、运行时不变量、安全边界、持久化语义或公共 API 的重大变更，先新增或修订 ADR。
2. 已 `Accepted` 的 ADR 不直接改写核心决策；用新 ADR 替代，并在两份文档中维护互链。
3. ADR 描述“为何这样设计”和必须保持的约束，不替代详细 API 文档、实施任务或测试代码。
4. 每份 ADR 必须列出可执行的验证方式，并引用对应 PRD 章节。
5. 编号一经分配不复用；文件名使用 `NNNN-kebab-case.md`。

## 新建 ADR

复制 [`template.md`](template.md)，分配下一个连续编号。至少填写：上下文、决策、替代方案、后果、约束与验证、PRD 可追溯性。

