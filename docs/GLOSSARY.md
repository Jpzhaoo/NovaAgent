# NovaAgent 术语表

| 术语 | 定义 |
|---|---|
| Turn | 一次用户输入到唯一终止事件之间的可靠执行边界，拥有稳定 identity、graph context、state 和 cancel token。 |
| Session Actor | 管理会话历史并串行化同一 session 的 Turn 的长生命周期容器；不是 Graph 数据面。 |
| Graph | 启动时编译、不可变的节点与边拓扑；业务数据通过 typed deliver 流转。 |
| Node invocation | 某个节点的一次执行尝试；带单调递增的 invocation version，可因崩溃按 at-least-once 重试。 |
| Deliver | 节点之间可靠传输 typed 输入的记录，状态为 `STAGED → PENDING → CONSUMED_PENDING → CONSUMED_COMPLETED`。 |
| Quiesce | 调度器不再有可执行 invocation、pending deliver 或未完成清理时的稳定点；Graph run 以 `wait_quiesce()` 完成。 |
| ReAct | 默认 Agent 策略，将推理、工具调用、继续判断和结束建模为 Graph 节点。 |
| ToolExecutor | 工具执行的唯一入口，负责 schema 校验、策略、审批、调度、结果提交和审计。 |
| PolicyGateway | 在副作用发生前对工具参数、风险、路径、网络、环境和资源进行统一判定的端口。 |
| GraphInterrupt | 预期的 Graph 挂起信号，用于审批、人工输入或业务断点；恢复沿同一 scheduler 路径继续。 |
| ControlPort | 运行时接收取消、暂停、恢复等外部控制命令的 typed 端口。 |
| StopReason | ReAct 或 Turn 终止的结构化原因，例如完成、达到迭代上限、循环、错误或取消。 |
| at-least-once | 崩溃恢复可能再次执行 invocation；通过幂等键和业务冲突结果控制副作用，不承诺 exactly-once。 |
| Cassette | 记录 GraphSpec、模型请求/事件及相关元数据、用于确定性 provider replay 的工件。 |
| Core Memory | 跨会话稳定事实、偏好和约束的记忆层；带来源、置信度、有效期和版本链。 |
| Experience Memory | 与具体用户事实隔离、按 agent/scope 授权的可复用操作经验层。 |

