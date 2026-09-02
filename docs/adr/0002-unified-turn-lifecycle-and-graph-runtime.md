# ADR-0002：基于 Graph Runtime 的统一 Turn 生命周期

- 状态：Proposed
- 日期：2026-09-02
- 决策者：NovaAgent 架构评审组（待确认）
- 关联 ADR：[ADR-0001](0001-core-boundaries-and-typed-contracts.md)、[ADR-0003](0003-centralized-tool-security-and-approval.md)
- 替代 ADR：无

## 上下文

Agent 执行同时包含模型流、工具副作用、人工审批、取消、超时、重试、持久化和进程恢复。如果正常运行、审批恢复和崩溃恢复分别使用不同循环，生命周期会发生分叉：工具可能重复执行，事件可能出现多个终止信号，暂停后的 Turn 也可能失去原有身份。

NovaAgent 还要支持普通 ReAct、可嵌入业务流程的 AgentNode，以及线性、条件、循环、扇出、汇聚和子图。单纯在 Agent 外包一层 workflow 不能为节点执行、deliver、恢复和观测提供一致语义。

## 决策驱动因素

- 正常、错误、取消、审批和恢复必须共享一个生命周期。
- Graph 是执行内核，ReAct 是可替换的图策略，而非第二套调度循环。
- 工具采用 at-least-once 语义，需要可验证的幂等与崩溃窗口处理。
- 事件流必须足以驱动 UI、日志、结果聚合、trace 和 cassette。
- 运行中的每个 Turn 必须有唯一终止结果，并可以确定性恢复。

## 决策

### 1. Turn 是可靠执行边界

每次用户输入创建一个 Turn。一个 Turn 只有一个 `TurnIdentity`、`GraphContext`、`GraphState` 和 `CancelToken`。同一 session 的 Turn 由 Session Actor 串行化；Session Actor 不是 Graph 的数据面。

Turn 状态机固定为：

```text
RECEIVED → RUNNING ↔ WAITING_APPROVAL
               │             │
               └──→ CANCELLING
               │             │
               ↓             ↓
         COMPLETED/FAILED   CANCELLED/FAILED
```

审批通过后回到 `RUNNING` 的同一调度路径；拒绝或控制命令可以触发取消。每个 Turn 必须且只能产生一个终止事件：`COMPLETED` 和 `CANCELLED` 使用带明确 `StopReason` 的 `TurnFinished`，`FAILED` 使用 `TurnFailed`，不额外创建第二个完成协议。

### 2. Graph Engine 是唯一调度内核

`Graph[S]` 是启动时编译的不可变拓扑；`GraphEngine` 负责 admission、节点 invocation、deliver、控制安全点和 quiescence。节点生命周期固定为：

```text
begin → integrate → execute → complete
      → promote staged delivers → dispatch
      → promote consumed delivers
```

节点之间只通过 typed deliver 传递业务数据。调度器只发送唤醒信号，不把数据塞入 dispatch payload。`LinearScheduler` 与 `ParallelScheduler` 共享同一生命周期、persistence coordinator 和 `bootstrap(FRESH|RECOVERY)`。

### 3. ReAct 是固定拓扑的内置 Graph

默认 `ReActAgent` 使用：

```text
START → BEFORE_TURN → LLM → TOOL → LLM
                         ↘
                    AFTER_TURN → BEFORE_TURN | END
```

`LLMNode` 仅构造请求、消费模型事件并路由；`ToolNode` 仅处理策略、审批、批调度、结果序提交和 deliver；`AFTER_TURN` 统一处理 continuation、循环检测、迭代预算和 `StopReason`。不得在 Agent 外再维护 ReAct `while` 循环。

### 4. 中断、控制与恢复共享语义

- `GraphInterrupt` 表示预期挂起，例如审批或人工输入；引擎传播该信号并保存 snapshot，不将其转成普通错误。
- `GraphBubbleUp` 用于控制面传播；普通异常将当前 invocation 标记为 `CRASHED`。
- `FRESH` 与 `RECOVERY` 是同一 scheduler 的显式 bootstrap 模式。恢复根据 invocation version chain 与 pending deliver 推导 seeds，不复制恢复引擎。
- 暂停和恢复保持相同 `turn_id`、`graph_instance_id` 与 `trace_id`，仅创建新的 attempt span 或 invocation version。
- 所有等待统一受 runtime watchdog 管理；局部组件只声明预算，不嵌套第二套超时控制。

### 5. 持久化采用事件日志、snapshot 与 deliver 状态机

- EventStore 使用 append-only 日志；snapshot 保存当前 Turn/Graph 状态。
- `GraphInstance`、`NodeInvocation` 和 `DeliverRecord` 与 Turn 一起持久化。
- Deliver 状态固定为 `STAGED → PENDING → CONSUMED_PENDING → CONSUMED_COMPLETED`。
- 工具调用携带稳定 `idempotency_key`；系统承诺 at-least-once，不承诺 exactly-once。
- Graph run 以 `wait_quiesce()` 作为唯一完成契约。

## 关键不变量

- 每个 Turn 恰好一个终止事件，终止事件与最终 snapshot 可关联。
- 新运行、审批恢复和崩溃恢复进入同一 scheduler，不存在旁路执行器。
- invocation version 单调递增；崩溃不会被静默吞掉。
- 节点不得读取其他节点的工作状态或依赖全局可变状态。
- `complete_invocation`、deliver promotion 和消费推进遵循既定事务边界。
- 模型事件、节点事件、工具事件和控制事件携带稳定 correlation identity。
- ReAct 达到迭代上限、循环、结构错误或控制命令时产生可解释 `StopReason`。
- 纯内存模式明确拒绝 recovery，不伪装为可恢复运行时。

## 替代方案

### ReAct while-loop 外加可选 workflow 层

实现较快，但 ReAct 与业务 Graph 会拥有两套取消、重试、事件和恢复逻辑，AgentNode 嵌入也会丢失统一 invocation 语义，因此不采用。

### 为崩溃恢复实现独立 replay engine

可以针对恢复做优化，但 live 与 recovery 的 admission 规则容易漂移，长期会出现只在恢复路径复现的错误，因此不采用。

### 仅保存 Turn snapshot

数据量较小，但无法区分工具已执行、结果已提交或 deliver 已消费等崩溃窗口，可能丢输入或重复副作用，因此不采用。

### exactly-once 工具执行

跨外部系统无法由框架普遍保证。NovaAgent 明确采用 at-least-once，并通过幂等键、结果唯一约束和业务冲突错误管理重复执行。

### 事件总线作为 Graph 数据面

可以统一消息形式，但会混淆实时观测事件和可靠节点输入。NovaAgent 用 DeliverStore 承载数据，EventSink 只承载可观察事件。

## 后果

### 正面

- 所有终止路径和恢复路径共享同一套状态机，行为更易推理和测试。
- ReAct 与业务 Graph 可以共享类型、事件、控制和持久化语义。
- crash window 可通过 invocation 与 deliver 状态精确定位。
- UI、CLI、评测和观测系统只消费事件流，不需了解调度内部。

### 负面与成本

- 即使简单聊天也需要经过 Graph runtime，初始实现复杂度较高。
- 持久化表、状态迁移和事务边界需要严格设计。
- 节点作者必须理解幂等与 at-least-once，不能假设函数只执行一次。
- 并行 scheduler、取消和审批之间存在较大的组合测试空间。

### 风险与缓解

| 风险 | 缓解措施 |
|---|---|
| 多个路径重复发出 terminal event | 原子终态转换、唯一约束和 Turn contract tests |
| 工具在崩溃窗口重复产生副作用 | 稳定 idempotency key、结果唯一约束和冲突错误 |
| Linear/Parallel 行为漂移 | 共享 bootstrap/admission/lifecycle，并运行同一 conformance suite |
| 暂停时仍启动新节点 | 在 admission 前设置 control safety point，等待 quiesce 后落 snapshot |
| 图循环无法收敛 | 编译期要求路由条件或预算，运行期 iteration/loop detector 产生 StopReason |

## 实施与验证

- 编译期验证节点 ID、入口/出口、边目标、可达性及受控循环，生成稳定 `graph_spec_hash`。
- 对 linear、conditional、loop、fan-out/join、subgraph 和 `ON_ALL_PREDS` 建立 Graph conformance suite。
- 为模型返回、工具执行、结果提交、snapshot、dispatch 和 cleanup 前后建立至少 14 个 crash windows。
- 对正常、异常、取消、审批恢复分别断言唯一 terminal event、稳定 identity 和最终 snapshot。
- 验证 `max_parallel=1` 与串行语义一致，并验证并行结果实时事件按 settle 顺序、历史按模型序提交。
- 随机执行 1,000 次故障注入，Beta 恢复成功率不低于 99%，Stable 不低于 99.9%。
- 测量取消响应：Beta ≤500ms，Stable ≤200ms。
- 架构测试阻断第二个 scheduler、恢复 engine、timeout wrapper 或完成 Event。

## PRD 可追溯性

- `1.3 核心假设`：Turn、at-least-once、事件流、GraphInterrupt。
- `FR-02`：Graph Engine、Turn lifecycle、事件和调度器。
- `FR-02A`：Graph-driven ReAct 六节点拓扑与 StopReason。
- `FR-06`：append-only、snapshot、deliver 四态与恢复。
- `5.3–5.6`：Graph 执行模型、ReAct、Session Actor 边界和 Turn 流程。
- `6.1`：watchdog、资源清理、terminal event 与 quiesce。
- `7.1`：Graph、Turn 和 crash-window 测试。

## 决策日志

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-09-02 | 创建 Proposed 版本 | 从 PRD Draft v1.0 提炼 Phase 0 Turn lifecycle 基线 |
