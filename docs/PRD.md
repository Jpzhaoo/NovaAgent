# NovaAgent：Graph-driven ReAct 可恢复 Agent 框架 PRD

**文档状态**：Draft v1.0  
**日期**：2026-09-02  
**项目代号**：NovaAgent  
**目标**：定义一个完全独立、从零开始构建的 Python Agent 框架，优先解决可靠执行、安全边界和可验证性，再逐步增加高级能力。

---

## 1. 产品概述

### 1.1 产品定位

NovaAgent 是一个面向 Python 3.12+ 的 Graph-driven ReAct Agent 框架。它以通用 Graph Engine 作为执行内核，以 ReAct 图作为默认 Agent 策略：模型推理、工具调用、审批中断、取消、重试和恢复都由图节点与状态机驱动。开发者通过少量 Python 代码声明模型、工具和策略，就能得到流式输出、持久化、恢复和可观测能力；多 Agent、记忆、MCP、WebUI 和终端在稳定端口之上作为能力包提供。

### 1.2 要解决的问题

构建 Agent 应用时，团队通常会遇到以下系统性问题：

1. 模型请求、工具副作用、审批和用户界面各自维护生命周期，异常时无法收敛。
2. 工具并发没有声明和安全策略，简单的并发优化可能导致重复写入、竞态或资源泄漏。
3. 取消、超时、进程崩溃和人工审批恢复由不同代码路径处理，造成悬挂任务和无法重放的对话。
4. 历史、运行状态、追踪和评测使用不同数据模型，导致线上问题无法复现。
5. 框架为了支持所有场景，把 Web、消息总线、图调度、数据库和业务记忆耦合进内核，新功能的边际成本越来越高。

### 1.3 核心假设

- Agent 的最小可靠执行单元是一次 **Turn**，而不是一个长生命周期的“万能 Agent 对象”。
- 工具执行遵循 **at-least-once**；副作用工具必须提供幂等键或业务级幂等策略，不虚构 exactly-once。
- 事件流是唯一的实时输出原语；完整结果、日志、UI 推送和 cassette 都由事件流派生。
- 所有跨边界数据都必须有明确 schema；运行时对象和可序列化值对象严格分离。
- 安全策略必须位于唯一工具执行入口，不能由工具作者自行决定是否调用。
- Graph Engine 负责调度和恢复，ReAct 只负责定义节点行为；业务 Graph 可以复用同一引擎，但不能把业务状态写入全局单例。
- 人工审批、人工输入和外部控制通过 `GraphInterrupt`/`ControlPort` 表达，恢复时重新进入同一调度路径，不另建恢复引擎。

### 1.4 产品特色

1. **Graph-driven ReAct**：不是在 Agent 外层包一层图，而是把 ReAct 的思考、工具、继续和结束都建模为可观测、可恢复的图节点。
2. **通用 Graph Engine**：同一引擎支持线性图、条件分支、循环、扇出/汇聚、并行调度和子图组合；ReAct 只是第一种内置策略。
3. **GraphInterrupt 人机协同**：审批、人工输入、暂停和业务断点共享同一种中断/恢复语义，保留完整 Turn 与 Graph 身份。
4. **工具安全优先**：风险等级、并发模式、策略检查、审批和取消清理在唯一 ToolExecutor 中收敛。
5. **可验证的恢复**：事件日志、snapshot、invocation version chain 和 deliver 状态机共同提供 at-least-once 恢复，而不是“从头再跑一次”。
6. **从单 Agent 到协作图**：普通 ReAct Turn、嵌入业务 Graph 的 AgentNode，以及后续父子 Agent 能共享类型、事件和控制端口。
7. **三层记忆与上下文治理**：Session、Archive、Core Memory 分层，压缩、注入和 token budget 都是可替换 provider，不污染 ReAct 状态机。
8. **声明式能力装配**：以 Scope/Profile/Capability 声明 Agent 的模型、工具、提示段、Hook 和资源，编译期生成可审计的 assembly manifest。
9. **跨平台执行工具**：终端、子进程和文件工具共享同一安全策略与取消契约，Windows、Linux、macOS 使用不同 adapter。
10. **外部 Agent 与 MCP 互操作**：外部 coding agent 和 MCP server 都通过 Tool/Model/Event 端口接入，不改变 Graph/ReAct 核心。

---

## 2. 目标、用户与非目标

### 2.1 目标用户

1. **应用开发者**：将 Agent 嵌入 CLI、Web 服务或桌面应用，不需要理解内部调度细节。
2. **工具作者**：声明参数 schema、风险等级、并发属性和取消清理逻辑。
3. **平台工程师**：替换模型、存储、审批和观测实现，并进行故障恢复。
4. **安全与运维人员**：审查每次工具调用的策略判定、审批记录、资源消耗和追踪。

### 2.2 产品目标

- 10 分钟内跑通第一个无配置文件的 Agent。
- 一个 Turn 的正常、错误、取消、审批和恢复都遵循同一生命周期。
- Graph Engine 支持线性、条件分支、循环、扇出/汇聚和子图组合；ReAct 是开箱即用的默认图。
- 核心运行时可在没有网络、数据库、Web 框架和可选依赖的环境下运行测试。
- 危险工具默认拒绝，所有副作用可审计，所有终止路径可观测。
- 新增模型供应商、存储后端或输入适配器时，不修改 Turn Engine。

### 2.3 v1 非目标

- 不在核心包中内置 WebUI、IM 适配器、MCP、终端、向量数据库或外部 coding CLI；但 Graph Engine 和 ReAct 属于核心交付范围。
- 不支持任意运行时动态生成工作流、热加载和跨进程分布式调度；图结构在启动时编译和校验。
- 不承诺一次性统一所有供应商的 reasoning replay、文件 API 或多模态格式；只提供协议扩展点。
- 不在框架层内置业务策略（todo、experience、dream、行业知识库等）。
- 不为了兼容其它框架而复制其 API；只承诺本项目自己的 SemVer 合约。

---

## 3. 成功指标

| 指标 | Beta 门槛 | Stable 门槛 | 测量方式 |
|---|---:|---:|---|
| 首个 Agent 跑通时间 | ≤15 分钟 | ≤10 分钟 | 干净环境 Quickstart 演练 |
| Core 代码量 | ≤20,000 行 | ≤15,000 行 | CI 统计核心包 |
| 单 Turn p95（mock model，10 次迭代） | ≤1.5 秒 | ≤1.0 秒 | 固定 benchmark |
| 取消响应延迟 | ≤500ms | ≤200ms | LLM、工具、审批三类注入 |
| 崩溃恢复成功率 | ≥99%（1,000 次注入） | ≥99.9% | crash-window 测试 |
| Graph 拓扑/调度一致性 | 100% | 100% | linear/parallel conformance |
| ReAct 场景完成率（cassette） | ≥95% | ≥99% | 固定场景集：工具、审批、循环、取消、恢复 |
| 世界状态断言通过率 | ≥90% | ≥97% | EvalSpec 的文件、命令和业务 oracle |
| Cassette replay miss | 0 | 0 | 每个 golden case 的所有模型调用 |
| Judge 重复评测一致率 | ≥85% | ≥95% | 同一 Trace 重复 judge 的 verdict agreement |
| Memory arm 相对 no-memory arm 提升 | ≥10 个百分点 | ≥20 个百分点 | 冻结 synthetic world 的双臂 probe |
| 跨用户记忆泄漏 | 0 | 0 | cross-user isolation probe + 安全测试 |
| Memory 检索 p95 | ≤150ms | ≤80ms | 10k 条记录、固定 embedding/mock retriever |
| Core 测试覆盖率 | ≥85% | ≥90% | coverage gate |
| 严格类型检查 | 0 error | 0 error | mypy 或 pyright |
| 安全旁路 | 0 | 0 | AST + runtime policy tests |
| 依赖可复现性 | lockfile 命中 100% | lockfile + SBOM | CI hash 校验 |

---

## 4. 功能需求

### 4.1 P0：首个可用版本必须交付

#### FR-01：Typed Core Contracts

- `Agent`、`ModelGateway`、`Tool`、`SessionStore`、`EventSink`、`PolicyGateway` 使用 ABC。
- 所有跨模块数据使用 `pydantic.BaseModel(frozen=True, extra="forbid")`；开放扩展必须放入显式的 `extensions` 字段。
- `Message`、`ToolCall`、`ToolResult`、`ModelRequest`、`TurnSnapshot`、`PolicyDecision` 使用枚举和判别联合。
- 公共类型集中于 `nova_core.types`，每个公共类型有 schema、序列化和反序列化测试。

#### FR-02：Graph Engine 与 Turn Runtime

- 生命周期固定为 `RECEIVED → RUNNING → WAITING_APPROVAL → CANCELLING → COMPLETED/FAILED/CANCELLED`。
- Graph Engine 提供 `Graph[S]`、`Node[S]`、`GraphContext[S]`、`GraphState` 和 `GraphEngine`；节点之间通过 typed `deliver` 传递输入，不直接读取其他节点的工作状态。
- 图在启动时执行结构校验：节点 ID 唯一、入口/出口明确、边目标存在、不可达节点失败；循环必须声明路由条件或预算，未受控循环在编译期失败；编译产物包含稳定 `graph_spec_hash`。
- 调度器至少支持 `LinearScheduler` 和 `ParallelScheduler` 两种模式；二者共享同一 `bootstrap(FRESH|RECOVERY)`、deliver admission 和节点生命周期。
- 节点生命周期固定为 `begin → integrate → execute → complete → promote → dispatch`；每次执行都有 invocation version，异常时标记为 `CRASHED`，不会静默吞错。
- `GraphInterrupt` 用于审批、人工输入和业务断点；引擎不得捕获并吞掉该异常。暂停只保存 snapshot，恢复重新走正常调度路径。
- 一个 Turn 只有一个 `GraphContext`、一个 `GraphState` 和一个 `CancelToken`；跨节点数据通过 deliver store 流转，不能依赖全局可变变量。
- 事件类型至少包括 `GraphStarted`、`NodeStarted`、`NodeFinished`、`TextDelta`、`ReasoningDelta`、`ToolCallStarted`、`ToolCallFinished`、`ApprovalRequested`、`GraphInterrupted`、`TurnFinished`、`TurnFailed`。
- 每个 Turn 必须且只能产生一个终止事件；消费者可以只依赖事件流。
- LLM 重试、工具重试、取消、审批恢复和崩溃恢复均从同一图调度器进入，不得新增旁路执行器。

#### FR-02A：Graph-driven ReAct Agent

- 内置 `ReActAgent`，由固定拓扑 `START → BEFORE_TURN → LLM → TOOL → AFTER_TURN → END` 构成；`LLM ↔ TOOL` 支持受控循环，`AFTER_TURN` 负责 continuation 和 finish-line 判断。
- `LLMNode` 只负责构造 `ModelRequest`、消费模型事件和决定下一节点；`ToolNode` 只负责审批分类、并发执行、结果序提交和 deliver，二者不互相持有 Agent 反向引用。
- ReAct 状态至少包含 `iteration`、`max_iterations`、`message_delta`、`pending_approval`、`tool_batch`、`stop_reason` 和 `result`；状态使用可序列化 typed model。
- 工具调用批次支持连续 PARALLEL 段与 EXCLUSIVE 屏障；工具结果按模型顺序写回历史，但实时完成事件可以按 settle 顺序发送。
- 达到迭代上限、检测到循环、模型返回结构错误或控制命令到达时，ReAct 必须产生可解释的 `StopReason`，而不是无限重试。
- ReAct 既可作为普通 Turn 运行，也可作为 Graph 的一个 `AgentNode` 嵌入更大的业务图；两种用法共享同一 `AgentContext` 和事件协议。

#### FR-03：Model Gateway

- 核心只依赖 `ModelGateway.stream(request) -> AsyncIterator[ModelEvent]`。
- v1 提供一个 OpenAI-compatible SSE 实现；传输、协议解析和请求体构造分层，新增供应商优先配置化。
- `ModelRequest` 是模型、采样参数、工具 schema 和 correlation 的唯一载体。
- 认证、限流、超时、协议、内容和未知错误映射为带 `retryable` 标志的 `ModelError`。
- Provider 不写历史、不写 snapshot、不触发 UI；它只产生 typed model events。

#### FR-04：Tool Runtime

- 工具必须声明 `name`、`description`、输入 schema、`risk: SAFE|SENSITIVE|DANGEROUS`、`execution: PARALLEL|EXCLUSIVE`。
- `ToolRegistry` 启动时校验名称唯一性；重复名称直接失败，禁止静默覆盖。
- `ToolExecutor` 是唯一入口：参数校验 → PolicyGateway → 审批（如需）→ 执行 → 结构化结果 → 审计。
- 工具调度采用并行段、独占屏障、模型序提交；默认并发度为 4，设置为 1 时必须与串行行为等价。
- 持有外部状态的工具必须实现 `on_cancel()`；工具不得吞掉 `CancelledError`。

#### FR-05：安全与审批

- PolicyGateway 提供 workspace path、路径穿越、设备路径、命令模式、网络/SSRF、环境变量和资源限制策略。
- 策略在参数解析完成后、工具真正执行前强制检查；工具实现不能绕过该检查。
- 审批请求包含稳定 `approval_id`、Turn/ToolCall 关联、风险原因、摘要和过期时间；批量审批采用原子决策。
- 审批恢复保留同一 `turn_id` 和 `trace_id`，仅增加新的 attempt span。
- 没有 PolicyGateway 时，危险工具不可注册，而不是自动放行。

#### FR-06：持久化与恢复

- v1 提供 SQLite reference store，并抽象 `SessionStore`、`TurnStore`、`EventStore` 三个端口。
- Graph 运行额外持久化 `GraphInstance`、`NodeInvocation` 和 `DeliverRecord`；deliver 状态使用 `STAGED → PENDING → CONSUMED_PENDING → CONSUMED_COMPLETED`，保证节点输入不会因进程崩溃丢失。
- 采用 append-only 事件日志加当前 Turn/Graph snapshot；所有写入使用事务和 schema migration。
- 每次工具调用包含 `idempotency_key`；重复恢复只能得到同一业务结果或明确的冲突错误。
- `FRESH` 与 `RECOVERY` 是同一 scheduler 的两个显式入口模式；恢复只根据 invocation 状态链和 pending deliver 推导 seeds，不复制一套恢复引擎。
- 进程退出、取消、审批等待、图中断、节点崩溃和清理均有故障注入测试；纯内存模式明确标记不支持恢复。

#### FR-07：配置与装配

- Python API 可以零配置启动；YAML/TOML 是上层适配器，不进入 Core 依赖。
- 配置模型使用 frozen Pydantic，优先级固定为 defaults → profile → app config → per-turn override。
- 只保留一个 `CapabilityRegistry`；能力包声明自己提供的 tool、hook、policy 或 supply。
- GraphSpec、AgentSpec 和 CapabilitySpec 在启动时统一校验；编译产物包含 `graph_spec_hash`、来源和最终能力列表。
- 运行期不得偷偷修改已装配对象；动态输入只能通过 typed `deliver` 或 ControlPort 进入。

#### FR-08：观测与诊断

- 默认提供结构化日志和 InMemory EventSink；安装 `nova-observe` 后启用 OpenTelemetry。
- Span 层级固定为 `graph_run → turn/node → model_call/tool_call/approval/policy`；敏感字段应用 redaction policy。
- 每个 Turn 可导出 cassette（GraphSpec hash、ModelRequest、ModelEvents、Node/Deliver events、clock/seed metadata），支持确定性重放。
- 提供 `nova doctor`，一次检查依赖、配置、模型连通性、工具策略和数据库迁移。

#### FR-09：Agent 评测与回归

- 提供独立的 `nova-eval` 包和 `EvalSpec`，描述任务 ID、多轮输入、工具集/deny-list、world setup、world assertions、expected stop reason 和 metadata；评测 schema 与生产运行时 schema 复用同一套 `Message`、`ToolCall`、`StopReason` 和 Trace 类型。
- `EvalRunner` 对每个 item 创建隔离的 workspace、session、trace 和 Agent runtime；多轮 item 共享该 item 的历史，但不同 item 之间禁止状态泄漏。支持 `clean`（trace-only）和 `production`（完整治理、checkpoint、loop detection）两种模式。
- 结果必须同时记录最终回答、每轮结果、stop reason、错误、工具统计、world assertion 结果、执行轮数和 stop mismatch；Agent 的自然语言声明不能作为任务完成的唯一依据。
- 内置确定性 evaluator：`accuracy`（适用于固定答案的大小写不敏感匹配）、`completion`、`response_length`、`world_state`、`tool_success`，并提供可选的 run-level aggregate。每个 evaluator 返回数值/布尔值、版本、comment 和证据引用。
- World assertion v1 至少支持 `file_exists`、`file_absent`、`file_contains`、`command_exit`；命令在隔离 workspace 中由 harness 执行，路径必须经过 workspace boundary 校验。后续可增加 HTTP、数据库和业务 API oracle，但不得读取 Agent prose 代替 oracle。
- 提供 LLM-as-a-judge 后处理：使用独立 judge model、temperature=0、版本化 rubric 和结构化 verdict（`MET|UNMET|NA|CANNOT_ASSESS`）；记录 weighted score、criterion evidence、judge model、rubric hash 和重复评测 agreement。Judge 可以对已有 Trace 重判，不触发 Agent 重跑。
- 提供 provider-only cassette record/replay：只回放模型请求，工具在 record/replay 两端均真实执行。cassette key 必须包含完整消息、模型、采样参数、max output tokens、工具 schema 和 kwargs；临时 workspace 统一归一化为 `<workspace>`。
- Golden replay 必须通过四个 gate：fingerprint match、cassette miss=0、每轮无错误且 `COMPLETED`、至少一个非空 world assertion（或显式 `baseline=true`）。Golden 刷新必须人工审核并记录变更原因，不能由 CI 自动覆盖。
- 提供生产 Trace metrics：stop reason、审批、handoff、工具成功率、迭代数、LLM 调用数、token、延迟、cache、reasoning、memory read/write/compression/utilization 等；数据源可以是 OTel/Langfuse 或本地 JSONL。
- 提供隔离环境评测适配器，用于验证安装、依赖、workspace、pool、memory、checkpoint resume、成本预算和 artifact 归档；外部环境失败必须区分安装失败、运行失败、Agent 失败和 oracle 失败。

#### FR-10：记忆系统实现

- `nova-memory` 必须是可独立安装的能力包；Core 只依赖 `MemoryPort`，不得直接依赖数据库、向量库或具体 embedding 服务。
- 记忆分为四层逻辑存储：
  - **Session Memory**：当前会话的原始消息和工具结果，保证可重放，默认不压缩；
  - **Archive Memory**：按会话/时间窗口生成的摘要、事件索引和可检索片段；
  - **Core Memory**：跨会话稳定事实、用户偏好、约束和身份信息，每条记录带来源、置信度、有效期和 superseded 关系；
  - **Experience Memory**：可复用的操作经验/策略，必须与用户事实隔离，按 agent/scope 授权。
- 所有记忆记录使用冻结 typed model，至少包含 `memory_id`、`layer`、`scope`、`owner`、`content`、`source_event_ids`、`created_at`、`updated_at`、`confidence`、`valid_from`、`valid_to`、`superseded_by` 和 `retention`；禁止使用无 schema 的 JSON 作为跨模块记忆接口。
- 提供以下端口：`MemoryWriter`（事件摄取）、`MemoryRetriever`（按 query 检索）、`MemoryCompressor`（摘要/压缩）、`MemoryConsolidator`（Archive→Core/Experience）、`MemoryContextAssembler`（注入上下文）和 `MemoryPolicy`（scope、保留、删除、敏感信息规则）。
- 记忆摄取必须由 Turn 完成事件驱动，并以 outbox/队列方式异步处理；写入失败不得阻塞最终回答，也不得修改原始 EventStore。写入和删除都要有可追踪的 lifecycle span。
- 检索流程固定为 `scope filter → lexical/semantic candidate → recency/confidence ranking → deduplicate/superseded filter → token budget packing → injection`。每次注入都附带 provenance（memory_id、score、reason、source event），便于调试和评测。
- Core/Experience 更新必须经过 consolidation policy：相同事实合并、冲突事实建立版本链、低置信度事实不得覆盖高置信度事实；用户可撤回、删除或冻结某条记忆。敏感字段默认不进入跨会话 Core Memory。
- Memory context 使用独立 token budget，不得挤占系统指令和当前用户输入；预算不足时按优先级丢弃，并产生 `MemoryTruncated` 事件。压缩不能改写原始消息或 cassette。
- 每个 Agent/tenant/user/session 都有显式 scope；跨用户检索默认拒绝，父子 Agent 只有声明 `memory_share` capability 才能共享指定层和字段。删除用户时必须级联清理索引、摘要、Core、Experience 引用和缓存。
- 提供 `memory_enabled=true|false` 的对照运行模式；no-memory arm 必须禁用所有历史注入和 consolidation，但保留相同模型、工具、任务、预算和 trace 采样。
- 记忆系统必须暴露可评测指标：retrieval recall、temporal ordering、knowledge update、refusal、cross-user isolation、compression ratio/monotonicity、prefix stability、read latency、write cost、injection retention 和 utilization delta。

### 4.2 P1：Beta 前交付

- `nova-http`：ASGI 适配器，支持 SSE/WebSocket 流、审批回调和历史分页。
- `nova-cli`：聊天、审批、恢复、日志查询、cassette replay。
- `nova-memory`：Session/Archive/Core/Experience 四层、异步 consolidation、token budget、scope isolation 和可插拔 Store；不把长期记忆塞入 ReAct Core state。
- `nova-mcp`：将 MCP server 映射为普通 ToolProvider，连接生命周期由包内负责。
- `nova-multi`：父子任务、inbox 和并发上限；暂不承诺跨租户 peer 通信。
- `nova-scope`：Workspace → Pool → Agent 的声明树、profile 深度合并、能力包启用和 assembly manifest。
- `nova-media`：附件 MIME/魔数/大小安全门、`media://` 持久化引用、按模型 modality 的临时多模态注入。
- `nova-terminal`：持久 shell、一次性 subprocess、交互式 terminal 三种 adapter；统一输入、输出、Ctrl-C 和进程树清理。
- `nova-external`：将外部 coding agent CLI 作为 Graph 的 `AgentNode` 或父 Agent 的子任务，统一事件投影和资源释放。

#### P1 能力包的行为约束

- **Memory**：Session Memory 保存原始消息；Archive Memory 保存压缩摘要；Core Memory 保存稳定事实/偏好；Experience 保存可复用操作经验。每层声明 scope、保留策略、注入优先级和 token 预算。压缩不得改变原始事件日志。
- **Multi-agent**：默认是“主 Agent + 子 Agent”的星型拓扑；子 Agent 只能向父 Agent 回传结果，父 Agent 通过 inbox 消费异步消息。并发上限、超时、取消和子树清理由 `nova-multi` 统一管理。跨 pool peer 通信属于后续版本。
- **MCP**：每个 MCP server 连接由共享 registry 管理，工具 schema、断线重连和 close 生命周期对上层表现为普通 `ToolProvider`。
- **Scope/Capability**：声明树只描述资源和继承，不执行逻辑；`ScopeCompiler` 产生每个 Agent 的模型、工具、memory、hooks、capabilities 和 provenance，装配失败必须在启动期暴露。
- **Media**：附件先经过 MIME、魔数、大小和路径安全门；持久化只保存引用。只有模型声明支持对应 modality 时，当前 Turn 才临时注入原生内容块，历史仍保留文本引用。
- **Terminal/External**：终端和外部 CLI 必须使用拥有者负责的 `close()`/`on_cancel()`，调度器只取消任务，不直接猜测或清理第三方进程状态。

### 4.3 P2：Stable 后交付

- Docker/E2B/Landlock sandbox、更多协议引擎、多租户、分布式 graph、WebUI（实时事件流、会话树、Graph viewer）和 hot reload。

---

## 5. 目标架构

### 5.1 包边界

```text
src/
  nova_core/        # types + ABC + ControlPort + EventSink（稳定内核契约）
  nova_graph/       # generic Graph Engine + Linear/Parallel schedulers
  nova_react/       # Graph-driven ReActAgent + standard ReAct nodes
  nova_runtime/     # TurnEngine + ToolExecutor，组合 core/graph/react
  nova_storage/     # SQLite/File stores，实现 core ports
  nova_models/      # HTTP/SSE gateway，实现 ModelGateway
  nova_policy/      # approval、workspace、network、env guards
  nova_cli/         # CLI adapter
  nova_http/        # ASGI/SSE adapter
  nova_memory/      # Session/Archive/Core Memory/Experience providers
  nova_multi/       # parent-child agents、inbox 和协作拓扑
  nova_mcp/         # MCP ToolProvider
  nova_scope/       # declarative scope/profile/capability compiler
  nova_media/       # attachment store and multimodal injection
  nova_terminal/    # cross-platform PTY/subprocess adapters
  nova_external/    # external CLI agent harness
packages/
  nova-*/pyproject.toml  # 各能力的独立发行元数据
  nova-*/src/nova_*      # 指向根 src 对应模块的相对链接，不存放实现副本
  examples/              # 业务示例，不进入 core 发布包
```

依赖方向只能由上层包指向 `nova-core` 的端口；`nova-graph` 只依赖标准库和 core types，`nova-react` 依赖 graph + core，`nova-runtime` 负责把 ReAct、工具和策略接成一次 Turn。`nova-core` 不得 import storage、HTTP、CLI、MCP、graph、react 或 WebUI。架构测试同时使用 AST 扫描和 import-time guard。

### 5.2 六个核心端口

| 端口 | 责任 | v1 参考实现 |
|---|---|---|
| `ModelGateway` | 请求模型并产生模型事件 | OpenAI-compatible SSE |
| `ToolRegistry/ToolExecutor` | 工具 schema、调度、结果 | InMemory registry + batch scheduler |
| `PolicyGateway` | 风险、路径、网络、审批 | deny-by-default workspace policy |
| `SessionStore/TurnStore/EventStore` | 会话、snapshot、事件 | SQLite |
| `EventSink` | UI、日志、测试和观测消费 | InMemory、JSONL、OTel bridge |
| `Clock/IdGenerator` | 可测试的时间和标识 | SystemClock、DeterministicClock |

### 5.3 Graph Engine 执行模型

Graph Engine 是 NovaAgent 的识别性核心，不只是一个可选 workflow 工具。

#### 图定义

- `Graph[S]` 是注册节点、静态边和入口/出口的不可变拓扑；`S` 必须是可序列化的 `GraphState`。
- `Node[S]` 只通过 `execute(ctx, integrated_input)` 处理输入；跨节点数据通过 `deliver(target, payload)` 传递。
- `GraphContext[S]` 包含 state、runtime、persistence coordinator、control 和 user data；每次运行一个 context，禁止共享可变全局 state。
- `GraphInterrupt`、`GraphBubbleUp` 和普通异常语义不同：前者是预期的挂起，后者是控制面传播，普通异常导致 invocation crash。
- `CompiledGraph` 本身也是 `Node`，因此子图可以作为父图节点组合；内外调度器共享 context 和事件协议，但 invocation 边界独立。
- 标准节点包括 `StartNode`、`EndNode`、`FunctionNode`、`HumanInputNode`、`AgentNode` 和 `DelayNode`；业务方只需实现一个 `Node[S]`，不需要接触 scheduler 内部。

最小业务图示例：

```python
graph = Graph[ReviewState](entry="start", end="finish")
graph.add_node(StartNode("start"))
graph.add_node(AgentNode("draft", agent=react_agent))
graph.add_node(FunctionNode("review", fn=review_document))
graph.add_node(EndNode("finish"))
graph.add_edge("start", "draft")
graph.add_conditional_edges(
    "draft", route_by_quality, destinations={"retry": "draft", "ok": "review"}
)
graph.add_edge("review", "finish")
compiled = graph.compile()
result = await GraphEngine(compiled).run_async(input_state)
```

`Graph.compile()` 只做拓扑和 schema 校验；`GraphEngine.run_async()` 才创建运行实例、invocation 和 deliver 记录。“声明错误”和“运行失败”可以分别诊断，同一 GraphSpec 也可以被测试、重放和多次调用。

#### 调度与触发

- `LinearScheduler` 用于 ReAct 等单指针图；`ParallelScheduler` 用于可并行的业务 DAG。
- 默认触发器为 `ON_ALL_PREDS`：节点等待所有已激活前驱的 deliver，并一次消费当前批次；`ON_RECEIVE` 仅作为实验特性，必须在编译期显式声明。
- scheduler 主循环只负责 admission、实例并发和安全点 control check；业务数据永远来自 DeliverStore，不塞进 dispatch payload。
- `bootstrap(mode=FRESH|RECOVERY)` 是正常执行、暂停恢复和崩溃恢复的统一入口；恢复只推导 seeds，不复制第二套执行引擎。

#### 节点生命周期与不变量

```text
begin_invocation
  → integrate(PENDING/CONSUMED_PENDING delivers)
  → execute(ctx, integrated_input)
  → complete_invocation
  → promote_staged_delivers
  → dispatch(target wakeups)
  → promote_consumed_delivers
```

- 节点 invocation version 单调递增；崩溃重试是 at-least-once，节点作者通过版本、幂等键或业务状态去重。
- 调度器只传递唤醒信号，数据面由 DeliverStore 负责；这样 live dispatch 和 crash recovery 可以共享同一份数据语义。
- `GraphInterrupt` 不被吞掉；暂停时在安全点停止启动新实例，正在执行的实例按取消/崩溃契约落库，恢复时重新 admission。

### 5.4 Graph-driven ReAct 拓扑

```text
START
  ↓
BEFORE_TURN → LLM ── tool_calls ──→ TOOL ──→ LLM
                  │                    │
                  └── final text ─────→ AFTER_TURN ── continue? ──→ BEFORE_TURN
                                                        │
                                                        └────────→ END
```

- `START` 区分新 Turn 与审批恢复；恢复时从 `TOOL` 继续，避免重复调用已经发出的工具。
- `BEFORE_TURN` 创建本次 attempt 的 runtime view；`LLM` 生成文本/推理/工具调用事件；`TOOL` 执行并提交结果；`AFTER_TURN` 负责 continuation、迭代预算和 stop reason；`END` 写入最终 `AgentResult`。
- ReAct 的循环上限、loop detection、长度退化和取消都是图节点路由，不在 `Agent` 外层再维护一套 while-loop。
- 任何节点都可以被替换或扩展，但节点之间必须遵循 typed input/output 与事件不变量。

### 5.5 Session Actor 与业务 Graph 的边界

- **Session Actor** 是长生命周期的会话容器，负责接收用户输入、维护 session history、串行化同一 session 的 Turn，并可通过 `nova-multi` 产生子 Agent 任务。
- **Business Graph** 是有明确起点和终点的执行实例，负责声明式的节点、分支、并行和汇聚；它不拥有用户会话，也不直接管理 Web/IM 连接。
- `ReActAgent` 可以独立运行在 Session Actor 内，也可以由 `AgentNode` 嵌入 Business Graph。嵌入时使用新的 child Turn identity，不共享父节点的可变 scratch。
- Session Actor 的异步 inbox 与 Graph 的 deliver 数据流不混为一谈：前者解决“消息何时被会话消费”，后者解决“节点何时具备执行输入”。

### 5.6 一次 Turn 的规范流程

```text
InputAdapter
   ↓ InputEnvelope
TurnEngine.acquire(session lock)
   ↓
ContextAssembler(history + system prompt + budget)
   ↓
ModelGateway.stream(ModelRequest)
   ├─ Text/Reasoning events → EventSink
   ├─ Tool calls → ToolExecutor
   │      ├─ PolicyGateway
   │      ├─ ApprovalPort (optional)
   │      ├─ parallel/exclusive scheduler
   │      └─ ordered commit + ToolResult events
   └─ Finish → snapshot + EventSink(TurnFinished)
```

安全、取消、重试和恢复必须发生在这条路径上；adapter、provider 或 hook 不得发明第二种 Turn 完成协议。

### 5.7 状态与数据契约

核心枚举：`TurnPhase`、`StopReason`、`MessageRole`、`ToolRisk`、`ExecutionMode`、`ApprovalState`、`ModelErrorKind`。

关键模型：

- `Session(id, tenant, created_at, metadata)`
- `TurnIdentity(turn_id, session_id, parent_turn_id | None)`
- `ChatMessage(role, content_parts, tool_calls, created_at)`
- `ModelRequest(model, messages, tools, sampling, correlation)`
- `ToolCall(call_id, name, arguments, seq)`
- `PolicyDecision(outcome, reasons, required_approval)`
- `ApprovalTransaction(approval_id, calls, decision, expires_at)`
- `TurnSnapshot(identity, phase, messages, pending_calls, last_event_seq, trace_id)`

所有序列化使用 `model_dump_json/model_validate_json`；禁止用匿名 `dict` 代替结构化模型。

### 5.8 Memory 运行架构

记忆系统与 ReAct 图通过两个明确的时机连接：`BEFORE_TURN` 读取并注入相关记忆，`END/TurnFinished` 将本轮事件投递给异步写入管线。记忆写入不改变 Graph 状态，也不绕过 EventStore。

```text
TurnFinished/EventStore
        ↓ outbox
MemoryWriter → Session Memory
        ↓ window/cursor
MemoryCompressor → Archive Memory
        ↓ consolidation job
MemoryConsolidator → Core Memory / Experience Memory

用户输入
   ↓
MemoryRetriever(scope + query)
   ↓
rank / deduplicate / superseded filter
   ↓ token budget
MemoryContextAssembler
   ↓ provenance 注入
BEFORE_TURN → LLM
```

#### 组件与职责

- `MemorySystem`：按 Agent/scope 组装 writer、retriever、compressor、consolidator 和 policy；生命周期由 Session Actor 管理。
- `SessionStore`：保存原始消息、工具调用和工具结果，使用 event sequence/cursor 增量读取；它是回放的唯一事实源。
- `ArchiveStore`：保存摘要和可检索片段；每个摘要指向一组不可变 `source_event_ids`，支持重新压缩和审计。
- `CoreStore`：保存事实/偏好版本链；更新使用 compare-and-swap 或事务，避免并发 consolidation 覆盖。
- `ExperienceStore`：保存与用户无关的操作经验；默认 scope 为 agent 或 workspace，不能自动提升为 tenant/global。
- `MemoryRetriever`：提供 lexical、embedding 和 hybrid 三种 adapter；检索算法本身只返回候选，不负责越权放行。
- `MemoryPolicy`：在读取、写入、共享、删除和注入五个边界执行 scope、敏感信息、retention 和用户撤回规则。
- `Dream/Consolidation Scheduler`：消费 Archive cursor，限制每次消费量和总 token/cost；检测 cursor 不前进并产生 stalled 诊断。

#### 记忆数据模型

```text
MemoryRecord
  memory_id: str
  layer: SESSION | ARCHIVE | CORE | EXPERIENCE
  scope: tenant / user / session / agent / workspace
  owner_id: str
  content: typed content parts
  source_event_ids: list[str]
  confidence: float
  valid_from / valid_to: datetime | None
  superseded_by: str | None
  retention: RetentionPolicy

MemoryQuery(query, scope, layers, top_k, token_budget, as_of)
MemoryHit(memory_id, score, reason, provenance)
MemoryContext(items, token_count, truncated, provenance)
ConsolidationJob(cursor, input_event_ids, output_memory_ids, status)
```

#### 一致性与隐私不变量

- 原始 Session Memory 只追加，不被摘要覆盖；Archive/Core/Experience 均可删除或重建。
- `superseded_by` 形成显式版本链；检索默认排除已被替代的记录，但历史回放可以按 `as_of` 查询。
- 同一个 `idempotency_key` 的写入只产生一个 memory record；重复消费 outbox 不产生重复事实。
- 记忆注入必须带 provenance，Trace 中记录命中的 ID、层级、得分、截断数量和 policy decision；默认不记录敏感原文。
- 用户删除请求必须生成可审计的 tombstone，并级联清理派生摘要、索引、缓存和共享引用；清理完成前禁止重新注入。
- no-memory arm 与 memory arm 使用相同的随机种子、模型参数、工具和任务输入，只改变记忆能力开关。

### 5.9 评测架构与结果模型

评测作为独立进程/包运行，避免与生产 OTel provider 或业务事件循环互相污染。它复用生产 assembly seam，但不直接修改生产代码路径。

```text
EvalSpec → Dataset/fixture materializer → EvalRunner
                                      ↓
                         Agent + real tools + isolated workspace
                                      ↓
          EvalTaskOutput + Trace + world oracle + tool statistics
             ↙                  ↓                    ↘
  deterministic scores   cassette replay gates    post-hoc LLM Judge
             ↘                  ↓                    ↙
                  experiment report / regression gate
```

- `EvalSpec` 支持单轮/多轮 turns、工具集、deny-list、world setup、world assertions、expected stop 和 metadata；每个 item 有稳定 ID 与 suite version。
- `EvalTaskOutput` 是评测和回放的唯一 wire shape，包含 `output`、`stop_reason`、`error`、`world_results`、`tool_stats`、`turn_records`、`turns_executed` 和 `stop_mismatches`。
- 确定性评分与主观评分分离：world/tool/completion/accuracy 先由代码计算；开放式质量再由独立 Judge 按版本化 rubric 评分。任何单一分数都不能覆盖其他 gate。
- Golden suite 的用例必须覆盖执行结果（例如运行生成文件并检查 exit/stdout）、多轮状态、只读纪律和长轨迹压缩；仅检查文件形状或零断言的 case 只能显式标记为 baseline。
- 评测报告至少输出 item 通过率、world 通过率、工具错误率、平均迭代/延迟/token、cassette miss、Judge weighted score/agreement，以及 memory/no-memory 差异。

---

## 6. 非功能需求

### 6.1 可靠性

- 所有可等待操作都由统一 watchdog 管理；局部层只能声明预算，不能自行包裹第二个超时。
- `finally` 必须释放 session lock、HTTP client、子进程、文件句柄和临时目录；清理失败要可观测并保留 owner 供重试。
- terminal event 唯一性、snapshot 原子性、审批恢复同一身份、工具结果模型序提交是不可变不变量。
- Graph run 以 `wait_quiesce()` 作为唯一完成契约；ReAct Turn、业务 Graph 节点和评测入口都必须等待同一 quiesce 信号，不允许各自维护完成 Event。

### 6.2 安全

- 默认最小权限；危险工具 deny-by-default；API key 不进入 prompt、日志、trace 或 cassette。
- 路径检查使用 realpath + workspace root；网络策略在 DNS 解析后判断私网/回环/IPv6；环境变量采用 allowlist。
- 审计日志 append-only；敏感参数 hash 或 redact；cassette 默认不保存原始文件内容。

### 6.3 性能

- 模型流首字节 p95 ≤1.5 秒（不含供应商网络）；工具并行段默认 4 个 worker。
- SQLite 写入可批量化但不能牺牲 snapshot 原子性；历史读取支持分页和 token budget。
- Core 不执行网络 IO；所有 IO 通过端口或上层 adapter。

### 6.4 可维护性

- 单模块公共接口不超过 7 个主要类型；单文件建议不超过 600 行。
- 新抽象必须有第二个真实适配器或明确的删除测试，否则不增加抽象层。
- 每个端口提供 InMemory fake、conformance suite、故障注入 fixture 和最小示例。

### 6.5 兼容与发布

- 支持 Python 3.12、3.13；采用 SemVer，0.x 阶段的破坏变更必须有 migration note。
- 所有依赖锁版本并生成 SBOM；发布 wheel、源码包和最小容器镜像。
- Core、models、storage、policy 独立版本；examples 不阻塞核心包发布。

---

## 7. 测试与验收

### 7.1 测试分层

1. **Schema tests**：公共模型构造、未知字段拒绝、判别联合和 JSON round-trip。
2. **Port conformance**：InMemory 与 SQLite 对同一 ABC 的行为一致。
3. **Graph conformance**：拓扑校验、条件分支、循环、扇出/汇聚、子图、`ON_ALL_PREDS`、deliver 四态和两种 scheduler 行为一致性。
4. **Turn contract tests**：正常、异常、取消、审批恢复均只产生一个 terminal event；ReAct 六节点拓扑的每条边都有覆盖。
5. **Crash-window tests**：在模型返回、工具执行、结果提交、snapshot、节点 dispatch 和 cleanup 前后注入进程终止。
6. **Security tests**：路径穿越、符号链接、私网/IPv6、危险命令、secret env、审批绕过。
7. **Architecture tests**：反向 import、工具旁路 executor、第二套 timeout、未注册工具直执行都必须失败。
8. **Deterministic evals**：至少 20 个 cassette，覆盖文本、工具、并行、审批、取消、恢复和图节点重放；真实模型仅夜间执行。
9. **Capability conformance**：Memory 四层隔离、MCP 重连、terminal Ctrl-C、media 引用不泄漏、Scope provenance 和父子 Agent 拓扑。

### 7.1A：Agent 评测验收

- **任务集**：至少 50 个固定 EvalSpec item，其中 ≥20 个包含真实工具副作用，≥10 个为多轮任务，覆盖正常完成、工具错误、审批、取消、循环上限、恢复和只读约束。
- **World oracle**：所有副作用任务至少有一个可执行 oracle；`file_exists/file_contains` 只能作为补充，代码修复类任务必须执行测试或命令并检查退出码/输出。
- **隔离性**：随机并发运行 100 个 item，任何 item 不得读取其他 item 的 workspace、session、memory 或 cassette 状态。
- **回放门禁**：所有 committed golden 必须 fingerprint 匹配、cassette miss=0、所有 turn clean、oracle 非空；缺少任一条件即失败，禁止空 suite 绿灯。
- **结果完整性**：每个 item 都能关联 root trace、结构化 `EvalTaskOutput`、各 evaluator score 和本地 archive；评测进程异常时保留失败原因和已完成 item。
- **Judge 质量**：固定 rubric 至少重复评测两次，agreement 低于门槛时标记为需人工复核，不得自动合并或覆盖 golden。

### 7.1B：Memory 评测验收

- 使用固定 seed 生成 facts、persona、session timeline 和 probes；expected truth 必须由 facts 自动推导，禁止人工复制答案造成 oracle 错误。
- 每个 suite 至少覆盖 extraction、temporal、knowledge update、refusal、cross-user isolation 五类 probe，并为可对照 probe 同时运行 memory/no-memory 两个 arm。
- deterministic reducer 必须输出每类通过率、NA/CANNOT_ASSESS 数量、整体 success delta 和 provenance；NA 不能静默计为失败或成功。
- 记忆 arm 必须在检索/更新任务上相对 no-memory arm 达到成功率提升门槛；cross-user isolation 出现一次越权注入即阻断发布。
- 在长对话中验证 compression ratio、压缩单调性、prefix stability、injection retention、read latency 和 write cost；consolidation cursor 停滞必须显式失败。
- 运行用户删除、记忆撤回、过期、冲突更新和重复 outbox 消费测试，确认派生索引/缓存清理和幂等性。

### 7.2 发布门槛

- required CI：format、lint、strict type、unit、conformance、architecture、security、coverage。
- 任一 required job 失败不得合并；禁止用 `continue-on-error` 绕过质量门禁。
- 每次 release 自动生成 changelog、SBOM、API schema 和 cassette 兼容报告。
- Beta 前完成至少 3 个独立示例的外部试用；Stable 前完成至少 2 个真实部署和一次恢复演练。

---

## 8. 详细实施计划（从 0 开始）

以下按 3 名工程师（Graph/ReAct 核心、基础设施/安全、DX/适配器）和 1 名兼职评测/产品估算，共 18 周。单人执行预计 32–36 周。

### Phase 0：立项与设计基线（第 1 周）

**任务**

- 建立 monorepo、包布局、版本策略、贡献指南和术语表。
- 定义 12 个端到端场景：纯对话、单工具、并行读取、危险写入、审批恢复、取消、模型错误、SQLite 重启、Graph 分支/汇聚、ReAct 循环、MCP、多 Agent/Web 流。
- 建立 Core boundary、Turn lifecycle、security gateway 三份 ADR。
- 建立依赖、代码量、覆盖率和 CI 质量基线。

**验收**：新仓库可运行 `make check`；架构图、非目标清单和场景矩阵评审通过。

### Phase 1：Core Types 与端口（第 2–3 周）

**任务**

- 实现 `nova_core.types` 的枚举、Pydantic 模型、错误族和序列化。
- 实现 6 个核心端口与 InMemory fake；注入 `Clock`、`IdGenerator`。
- 启用 strict mypy/pyright，生成 schema 文档。
- 完成模型边界测试：未知字段、联合判别、时间/ID、消息和工具调用配对。

**验收**：`nova-core` 可独立安装、无外部网络依赖、核心代码 ≤5,000 行、类型检查零错误。

### Phase 2：Graph Engine 基础（第 4–5 周）

**任务**

- 实现 `Graph[S]`、`Node[S]`、`GraphState`、`GraphContext`、`GraphSpec` 和 compile-time topology validator。
- 实现 `LinearScheduler` 与 `ParallelScheduler`；先完成 `START/END`、静态边、条件边、fan-out、join 和子图节点。
- 实现 `DeliverStore` 四态、`NodeInvocation` version chain、`bootstrap(FRESH|RECOVERY)` 和 `GraphInterrupt` 传播。
- 为 scheduler 注入 `Clock`、`IdGenerator`、`GraphPersistenceCoordinator` 和 `ControlPort`，禁止直接依赖模型或工具。

**验收**：框架无 Agent 依赖即可运行一个带分支和汇聚的 typed graph；线性/并行两种调度结果一致；GraphInterrupt 可挂起并恢复；拓扑和恢复 conformance 通过。

### Phase 3：Model Gateway（第 6–7 周）

**任务**

- 实现 SSE framing、请求体构造、事件 parser、错误分类和活动预算。
- 实现 scripted gateway、cassette record/replay 和供应商模拟服务器。
- Provider config 使用 schema 校验；secret 只从 `SecretResolver` 读取。

**验收**：文本、reasoning、tool call、usage、错误和 EOF 均有确定性测试；首字节 benchmark 达标。

### Phase 4：Graph-driven ReAct 与 Tool Scheduler（第 8–9 周）

**任务**

- 实现 `ReActAgent` 和固定六节点图：`START → BEFORE_TURN → LLM → TOOL → AFTER_TURN → END`，支持 `LLM ↔ TOOL` 受控循环。
- 实现 ReAct 状态模型、message delta、reasoning replay、loop detection、长度退化和 continuation。
- 实现 Turn 状态机、session 单飞锁、上下文组装和迭代上限，并将 Agent 运行放入 GraphContext。
- 实现 ToolRegistry、参数校验、并行段/独占屏障/模型序 commit。
- 统一取消：取消 worker、调用 `on_cancel`、为未完成调用生成 cancelled result。
- 实现 EventSink fan-out 和 terminal event invariant。

**验收**：ReAct 六节点图通过纯对话、单工具、多工具、审批中断、循环退出和取消用例；并行读取较串行延迟下降 ≥30%；`max_parallel=1` 严格回归；取消延迟 ≤500ms。

### Phase 5：Storage、Snapshot 与恢复（第 10–11 周）

**任务**

- 设计 SQLite schema：sessions、turns、graph_instances、node_invocations、deliver_records、events、tool_results、approvals、migrations。
- 实现 append-only event store、snapshot store 和 idempotency key 唯一约束。
- 实现从最后确认 event、invocation version chain 和 pending deliver 重建 Turn/Graph 的恢复算法。
- 建立至少 14 个 crash windows 的故障注入 fixture；实现 orphan graph instance 扫描和清理。

**验收**：ReAct Turn 与业务 Graph 均可从进程崩溃恢复；1,000 次随机注入成功率 ≥99%；conformance 通过；内存模式明确拒绝 recovery。

### Phase 6：Policy Gateway 与审批（第 12–13 周）

**任务**

- 实现 path/traversal/device/network/command/env/resource guards。
- 让 ToolExecutor 强制经过 PolicyGateway；无 gateway 时危险工具注册失败。
- 实现 ApprovalPort、批量原子决策、过期和审计；恢复保持原 turn_id/trace_id。
- 完成符号链接逃逸、Unicode 路径、DNS rebinding、shell 注入和 secret 泄漏红队用例。

**验收**：安全旁路为 0；危险操作默认拒绝；审批恢复事件链完整；取消与审批竞态有确定结果。

### Phase 7：CLI/HTTP 与开发者体验（第 14 周）

**任务**

- 实现 `nova run`、`nova replay`、`nova inspect`、`nova approve`、`nova doctor`。
- 实现 ASGI adapter：SSE、WebSocket、审批回调和历史分页。
- 编写 10 分钟 Quickstart、最小 Dockerfile、配置参考和故障排查。
- 接入 structured logging、可选 OTel bridge 和 redaction 默认值。

**验收**：干净环境 15 分钟内跑通；CLI/HTTP 不复制 Turn 逻辑，只消费 Core ports。

### Phase 8：可选能力包（第 15–16 周）

**任务**

- `nova-memory`：实现 Session/Archive/Core/Experience 四层存储、typed `MemoryRecord`/`MemoryQuery`/`MemoryHit`/`MemoryContext` 模型和对应 ABC。
- 实现 TurnFinished→outbox→MemoryWriter 的异步摄取；实现 Archive cursor、窗口压缩、Dream/Consolidation Scheduler、Core/Experience 版本链和 idempotency key。
- 实现 scope filter、lexical/semantic/hybrid retriever、recency/confidence rerank、superseded 过滤、token budget packing 和 provenance 注入。
- 实现 MemoryPolicy 的读写/共享/删除/retention/sensitive redaction；完成 user、session、agent、workspace、tenant 五级隔离和级联删除。
- 提供 memory-enabled/no-memory 双臂 harness 与 deterministic reducer，接入五类 probe、压缩/延迟/成本指标和 sentinel gate。
- `nova-mcp`：MCP ToolProvider、共享连接 registry、断线重连和生命周期管理。
- `nova-multi`：主 Agent + 子 Agent 星型拓扑、inbox、并发上限、子树取消和 quiesce。
- `nova-scope`：Workspace/Pool/Agent 声明树、profile 合并、能力包编译和 provenance manifest。
- `nova-media`：附件安全门、媒体存储引用和按 modality 的临时注入。
- `nova-terminal` / `nova-external`：跨平台 PTY/subprocess、外部 CLI session、事件投影和 close/on_cancel。

**验收**：每个能力包可独立安装；Graph Engine 与 ReAct 核心包始终可用；无反向 import；能力来源、子 Agent 拓扑、媒体引用和资源清理均可观测。

### Phase 9：评测、硬化与 Beta（第 17 周）

**任务**

- 实现 `nova-eval`：EvalSpec、隔离 EvalRunner、确定性 evaluators、world assertion harness、Langfuse/local trace adapter 和本地 run archive。
- 实现 provider-only cassette record/replay、fingerprint/miss/clean-turn/non-vacuous-oracle 四个 gate；提交至少 20 个 golden，覆盖工具副作用、多轮状态、审批、取消、恢复和长轨迹压缩。
- 实现独立 LLM Judge、rubric SHA 版本、MET/UNMET/NA/CANNOT_ASSESS verdict、重复评测 agreement 和 post-hoc score 注入。
- 完成 10 个 Graph/ReAct 场景、5 个真实模型 smoke、memory 五类 probe 双臂实验和 2 个外部应用示例。
- 运行 24 小时、1,000 Turn soak；检查资源泄漏和数据库迁移回滚。
- 固化性能基线、故障手册、威胁模型和 SBOM；冻结 v1 API。

**验收**：全部 Beta 指标达标；评测报告可追溯到 item、Trace、oracle 和 rubric；memory arm 达到提升门槛且无跨用户泄漏；外部试用问题关闭；候选版本带 known limitations。

### Phase 10：Stable 发布（第 18 周）

**任务**

- 发布 `nova-core`、`nova-models`、`nova-storage`、`nova-policy` 1.0。
- 建立兼容政策、CVE 响应、依赖升级窗口和季度 ADR 复审。
- 规划 v1.1（更多协议、sandbox backend、WebUI）与 v2（分布式 graph、跨租户、hot reload）。

**验收**：Stable 门槛全部满足；至少两个真实部署完成升级和恢复演练；文档、schema、SBOM、changelog 一致。

---

## 9. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| 为“以后可能需要”不断扩张 Core | 高 | 高 | 以非目标清单和代码量门槛阻断；能力包优先 |
| at-least-once 导致副作用重复 | 中 | 高 | 强制 idempotency key；故障注入先于功能扩展 |
| 安全策略误杀正常命令 | 中 | 高 | deny-by-default + 可解释理由；策略包独立迭代 |
| 供应商协议差异污染 Core | 中 | 中 | Core 只看 ModelEvent；每个协议独立 engine 和 wire fixture |
| 可选包边界再次膨胀 | 高 | 中 | CapabilityRegistry 只允许声明提供物；新增包须有第二适配器或删除测试 |
| WebUI/IM 需求打断核心迭代 | 高 | 中 | 适配器独立发布；核心 API 冻结后再扩展 |
| 依赖升级造成行为漂移 | 中 | 中 | lockfile、SBOM、定期依赖 PR、cassette 回归 |

---

## 10. Definition of Done

NovaAgent v1 只有在以下条件全部满足时才算完成：

- [ ] Core、Model、Storage、Policy 四个包可独立安装和版本化。
- [ ] Graph Engine 与 ReAct 核心包可独立运行；线性/并行调度、分支/汇聚、子图和 GraphInterrupt 均有 conformance 覆盖。
- [ ] 一个 Turn 的所有结束路径都有唯一 terminal event、snapshot 和 trace。
- [ ] 模型、工具、审批、取消、恢复均有真实调用模式测试与故障注入测试。
- [ ] 危险工具无 PolicyGateway 时无法注册；不存在 executor 旁路。
- [ ] InMemory/SQLite conformance、schema round-trip、架构守卫全部通过。
- [ ] required CI 不使用 `continue-on-error`；覆盖率、类型、依赖锁和 SBOM 均有门禁。
- [ ] Quickstart、API reference、威胁模型、故障手册和 known limitations 齐全。
- [ ] 至少两个外部示例在不修改 Core 的情况下接入；一次进程崩溃恢复演练成功。

最终判断标准不是“功能最多”，而是：开发者能否快速理解核心；运维能否可靠停止和恢复；安全人员能否证明没有旁路；团队能否在不触碰 Turn Engine 的情况下增加能力。只有这四点同时成立，框架才具备长期演化的基础。
