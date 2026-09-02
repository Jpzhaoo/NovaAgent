# ADR-0003：集中式工具安全策略与审批网关

- 状态：Proposed
- 日期：2026-09-02
- 决策者：NovaAgent 架构评审组（待确认）
- 关联 ADR：[ADR-0001](0001-core-boundaries-and-typed-contracts.md)、[ADR-0002](0002-unified-turn-lifecycle-and-graph-runtime.md)
- 替代 ADR：无

## 上下文

Agent 工具可以读写文件、执行命令、访问网络、读取环境变量或操作外部业务系统。若安全判断由每个工具自行实现，工具作者可能遗漏检查，不同调用入口也可能形成绕过路径。并发、重试和恢复还会放大副作用：即使参数合法，也可能因重复执行、取消不完整或审批状态不一致而造成损害。

NovaAgent 需要允许安全工具顺畅运行，同时对敏感和危险行为提供默认拒绝、可解释策略、原子审批和完整审计。策略必须独立于 CLI、HTTP 或模型供应商，且审批恢复不能创建新的 Turn 身份。

## 决策驱动因素

- 所有工具调用必须经过同一个、可审计的安全入口。
- 危险操作在缺少策略实现时必须失败关闭（fail closed）。
- 路径、网络、命令、环境变量和资源限制需要一致的跨工具规则。
- 审批是 Graph 中断的一种，不得建立旁路恢复流程。
- 并行执行不能破坏审批原子性、工具顺序或取消清理。

## 决策

### 1. ToolExecutor 是唯一执行入口

所有工具调用必须经过以下固定管线：

```text
ToolCall
  → registry lookup
  → schema validation
  → PolicyGateway.evaluate
  → approval transaction（如需）
  → parallel/exclusive scheduling
  → tool execution
  → structured result
  → ordered commit + audit events
```

任何 adapter、hook、AgentNode、MCP provider 或内部能力包都不得直接调用工具实现。工具实现不负责决定是否跳过策略。

### 2. 工具声明风险与并发语义

工具注册时必须声明：

- 唯一的 `name`、描述和输入 schema；
- `risk: SAFE | SENSITIVE | DANGEROUS`；
- `execution: PARALLEL | EXCLUSIVE`；
- 对外部副作用适用的幂等策略；
- 持有外部资源时的 `on_cancel()` 清理契约。

重复名称在启动时失败。没有 `PolicyGateway` 时，`DANGEROUS` 工具不得注册；未知工具、无效参数和未知风险值一律拒绝。

### 3. PolicyGateway 在执行前统一判定

策略在参数解析完成后、任何副作用发生前执行。v1 策略至少覆盖：

- workspace realpath 边界、`..` 穿越、符号链接和设备路径；
- 命令模式、shell 注入和资源预算；
- DNS 解析后的私网、回环、IPv4/IPv6 与 SSRF 判定；
- 环境变量 allowlist 与 secret redaction；
- 工具级风险、租户/用户 scope 和审批要求。

`PolicyDecision` 是冻结的 typed model，包含 outcome、理由和审批要求。拒绝与需审批必须提供可供用户和审计读取的非敏感原因。

### 4. 审批使用原子事务与 GraphInterrupt

需要人工决定时，ToolExecutor 创建 `ApprovalTransaction`，其中包含稳定 `approval_id`、Turn/ToolCall 关联、风险摘要、调用集合和过期时间，然后通过 `GraphInterrupt` 挂起当前 Graph。

- 批量审批对整组调用原子决策，不允许一半批准、一半处于未知状态。
- 审批记录 append-only；过期、拒绝、取消和批准是明确终态。
- 恢复保持同一 `turn_id` 和 `trace_id`，只增加 attempt span，并重新进入标准 ToolNode/ToolExecutor 路径。
- 任何 UI 或 API 只能经 `ApprovalPort` 提交决策，不能直接唤起工具。

### 5. 并发、提交和取消由 Executor 管理

工具批次切分为连续 `PARALLEL` 段和 `EXCLUSIVE` 屏障，默认并发度为 4。完成事件可按 settle 顺序发送，但工具结果必须按模型给出的 `seq` 写回历史。

取消时 Executor 停止调度新调用、取消 worker、调用拥有资源工具的 `on_cancel()`，并为未完成调用生成结构化 cancelled result。工具不得吞掉 `CancelledError`；调度器不猜测第三方进程的清理方式。

## 关键不变量

- 不存在绕过 ToolExecutor 的工具执行路径。
- 策略校验发生在副作用之前，且使用已完成 schema validation 的参数。
- 危险工具无 PolicyGateway 时无法注册或执行。
- 审批恢复保留 Turn/Graph/Trace 身份，且不会重复执行已确认完成的调用。
- 审批、策略判定、调用开始、调用结束和取消均产生相关联的审计事件。
- Secret 不进入 prompt、普通日志、trace 或 cassette；敏感参数只记录 hash 或 redact 值。
- 路径授权基于 realpath 后的 workspace 边界；网络授权基于 DNS 解析后的所有地址。
- 外部副作用遵循 at-least-once，并使用稳定 `idempotency_key`。

## 替代方案

### 每个工具内部自行检查权限

实现局部直接，但安全规则会重复、漂移，并且新工具容易漏检，无法证明不存在旁路，因此不采用。

### 只按工具名称维护 allowlist/deny-list

无法根据实际路径、地址、命令或 scope 判断风险，也不能应对符号链接和 DNS rebinding，因此只能作为策略输入，不能作为完整安全模型。

### 在 CLI 或 HTTP adapter 中审批

会让不同入口具有不同安全语义，后台任务和恢复流程也可能绕过审批，因此 adapter 只实现 ApprovalPort，不拥有决策流程。

### 所有敏感工具完全串行执行

虽然简单，但会不必要地降低安全只读操作的吞吐。NovaAgent 显式声明 `PARALLEL`/`EXCLUSIVE`，由 Executor 使用屏障维护安全顺序。

### 默认允许，发生风险后审计

不符合最小权限和危险工具 deny-by-default 要求。NovaAgent 对未知、缺失或无法判断的危险策略使用 fail-closed。

## 后果

### 正面

- 安全人员可以验证单一 choke point，而无需审计所有 adapter 和工具调用方。
- 策略、审批和工具实现可分别测试与替换。
- 审批、取消和恢复共享 Graph 生命周期，避免身份或状态分叉。
- 并行只读工具仍可获得性能收益，副作用顺序保持确定。

### 负面与成本

- 所有工具执行都增加 schema 与策略检查开销。
- 跨平台路径、命令和网络策略实现复杂，需要大量边界测试。
- 工具作者必须声明风险、并发、幂等和取消行为。
- fail-closed 可能误拒绝合法操作，需要提供清晰理由和可审计的策略配置。

### 风险与缓解

| 风险 | 缓解措施 |
|---|---|
| 新代码直接调用工具实现 | AST guard、registry/executor capability token 和 runtime negative tests |
| TOCTOU 导致路径检查后目标变化 | 尽可能使用目录句柄/安全打开方式，并在实际操作点复核解析结果 |
| DNS rebinding 绕过 URL 检查 | 对解析后的所有地址执行策略；连接层验证实际 peer 地址 |
| 审批与取消竞态 | ApprovalTransaction 原子状态转换，Turn control 在执行前再次检查 |
| secret 泄漏到事件或 cassette | 中央 redaction policy、敏感 fixture 和序列化快照测试 |
| 重试导致重复副作用 | idempotency key、工具结果唯一约束与显式 conflict result |

## 实施与验证

- ToolRegistry 在启动时检查名称、schema、risk、execution 和危险工具的 policy availability。
- 提供 workspace、command、network、environment 和 resource guard 的组合式 PolicyGateway。
- 使用 realpath、Unicode、符号链接、设备路径、私网/回环/IPv6、DNS rebinding、shell 注入和 secret env 红队用例。
- 对拒绝、批准、批量拒绝、过期、取消与审批竞态运行确定性测试。
- 使用 AST 与 runtime tests 验证 adapter、hook、MCP 和 AgentNode 不能绕过 Executor。
- 验证并发段、独占屏障、settle-order 事件与 model-order commit；`max_parallel=1` 必须等价于串行。
- 验证持有外部资源的工具在取消和异常路径调用 `on_cancel()`，并记录清理失败 owner。
- 发布门禁要求安全旁路为 0，跨用户/跨 workspace 越权为 0。

## PRD 可追溯性

- `1.3 核心假设`：唯一工具执行入口与 at-least-once。
- `FR-04`：Tool Runtime、风险与并发声明、取消契约。
- `FR-05`：PolicyGateway、审批事务和身份保持。
- `FR-06`：幂等键与恢复冲突语义。
- `5.6`：Turn 规范流程中的 ToolExecutor 与 ApprovalPort。
- `6.1`：资源释放和取消。
- `6.2`：最小权限、路径/网络/env 与审计要求。
- `7.1`：Security 与 Architecture tests。

## 决策日志

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-09-02 | 创建 Proposed 版本 | 从 PRD Draft v1.0 提炼 Phase 0 security gateway 基线 |

