# ADR-0001：Core 包边界与类型化端口

- 状态：Proposed
- 日期：2026-09-02
- 决策者：NovaAgent 架构评审组（待确认）
- 关联 ADR：[ADR-0002](0002-unified-turn-lifecycle-and-graph-runtime.md)、[ADR-0003](0003-centralized-tool-security-and-approval.md)
- 替代 ADR：无

## 上下文

NovaAgent 需要同时支持模型供应商、图调度、工具、安全策略、存储、CLI、HTTP、Memory、MCP 和多 Agent 等能力。如果这些能力共享运行时对象、匿名字典或双向依赖，Core 会快速膨胀，供应商差异和 UI 生命周期也会进入执行内核，最终使离线测试、独立发布和能力替换变得困难。

系统还要求运行状态可以持久化、重放和跨进程恢复。隐式字段、宽松 schema 和不可序列化对象会使兼容性错误延迟到运行时，并破坏 snapshot 与 cassette 的确定性。

## 决策驱动因素

- Core 必须能在无网络、数据库、Web 框架和可选依赖时独立测试。
- 新增模型、存储或输入适配器时不得修改 Turn Engine。
- 跨模块数据需要稳定 schema、严格验证和 JSON round-trip。
- 包依赖方向需要可由 CI 自动证明，而不只依赖代码评审。
- 可选能力应独立演化，不能反向污染稳定内核。

## 决策

采用端口与适配器架构，并将稳定契约集中在 `nova-core`：

1. `nova-core` 只包含公共类型、错误、ABC 端口、`ControlPort`、`EventSink`、`Clock` 和 `IdGenerator` 等稳定契约。
2. 跨模块值对象使用 `pydantic.BaseModel`，统一配置为 `frozen=True`、`extra="forbid"`。开放扩展只允许进入显式 `extensions` 字段。
3. `Agent`、`ModelGateway`、`Tool`、存储端口、`EventSink` 和 `PolicyGateway` 使用 ABC；每个端口提供 InMemory fake 与 conformance suite。
4. 运行时资源（HTTP client、数据库连接、进程、锁）不得放入可序列化模型，通过 context 或适配器生命周期注入。
5. 依赖方向固定如下：

   ```text
   adapters / capabilities
            ↓
       nova-runtime
        ↙       ↘
   nova-react  policy/storage/models ports
        ↓
    nova-graph
        ↓
     nova-core
   ```

6. `nova-graph` 只依赖标准库和 Core 类型；`nova-react` 依赖 Graph 与 Core；`nova-runtime` 负责装配 ReAct、工具和策略。
7. `nova-core` 禁止导入 storage、HTTP、CLI、MCP、graph、react、memory 或 WebUI。可选包通过 Core 端口接入，不在 Core 中增加反向适配代码。
8. Python API 是零配置主入口；YAML/TOML 只由上层适配器解析。装配产物是不可变、带来源信息的 manifest，运行中不得偷偷改变能力集合。

## 关键不变量

- 跨包 wire data 不使用匿名 `dict` 代替公共模型。
- 公共模型可执行 schema 生成、序列化和反序列化测试。
- Core 不执行网络或数据库 IO；IO 只能经端口或上层适配器发生。
- 下层包不得 import 上层包；尤其禁止 Core 和 Graph 反向依赖具体能力包。
- 任何新增抽象都需要第二个真实适配器，或一个证明可删除该抽象的测试。
- 配置合并顺序固定为 `defaults → profile → app config → per-turn override`。

## 替代方案

### 单体包与内部模块约定

代码初期较简单，但边界无法独立发布或安装，optional dependency 容易渗入 Core，也难以通过安装测试验证真实依赖方向，因此不采用。

### 以结构化 `dict` 或 TypedDict 作为所有 wire shape

静态类型成本较低，但运行时无法拒绝未知字段，schema、版本迁移和反序列化错误不够明确，无法满足恢复与重放要求，因此不采用。

### Core 直接集成主流供应商和存储

可以减少适配层代码，但会把认证、网络、数据库和供应商协议带入内核，破坏离线测试与独立发布，因此不采用。

### 依赖注入容器管理全部对象

通用容器会隐藏构造关系，并增加运行期可变装配的可能。NovaAgent 使用显式构造、单一 `CapabilityRegistry` 和编译期 manifest，因此不引入全局服务定位器。

## 后果

### 正面

- Core 可独立安装、测试和版本化。
- 适配器替换不会改变 Turn Engine 的控制流。
- schema 错误在模块边界即时暴露，snapshot、事件和 cassette 更易演进。
- 包边界可通过 AST 和 import-time 测试持续验证。

### 负面与成本

- 需要维护公共模型、转换层、fake 和 conformance suite。
- 严格模型在高频事件路径上有一定验证开销，需要用基准测试监控。
- 跨包新增字段需要显式 schema 演进和兼容性说明。
- 细分发布包会增加版本协调和依赖锁管理成本。

### 风险与缓解

| 风险 | 缓解措施 |
|---|---|
| Core 仍因“通用能力”持续膨胀 | Core 代码量门禁；新增类型必须对应稳定端口或跨包 wire contract |
| 包拆分过细导致开发体验下降 | 提供聚合安装项、统一 Quickstart 和 runtime composition root |
| 模型版本升级破坏旧 snapshot | schema 版本、migration note 和 round-trip fixture |
| 适配器行为不一致 | 对每个端口运行同一 conformance suite 和故障注入 fixture |

## 实施与验证

- 创建 PRD 5.1 所列 monorepo 包，各包独立 `pyproject.toml`，并明确可选依赖。
- 为公共类型生成 JSON Schema，测试未知字段拒绝、判别联合和 JSON round-trip。
- 对 Core 运行无网络、无数据库依赖的独立安装测试。
- 使用 AST 扫描和 import-time guard 阻断反向 import。
- 对 InMemory 与 SQLite、scripted 与 HTTP gateway 等实现运行统一 conformance suite。
- CI 启用 Python 3.12/3.13、strict mypy 或 pyright、依赖锁和 SBOM 检查。
- 评审门槛：Core Beta ≤20,000 行、Stable ≤15,000 行；Phase 1 Core ≤5,000 行。

## PRD 可追溯性

- `1.3 核心假设`：跨边界 schema、运行时对象和值对象分离。
- `FR-01`：Typed Core Contracts。
- `FR-07`：配置、CapabilityRegistry 与不可变装配。
- `5.1`：包边界及单向依赖。
- `5.2`：六个核心端口。
- `6.3`：Core 不执行网络 IO。
- `6.4`：抽象、fake 与 conformance 要求。
- `7.1`：Schema、Port conformance 和 Architecture tests。

## 决策日志

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-09-02 | 创建 Proposed 版本 | 从 PRD Draft v1.0 提炼 Phase 0 Core boundary 基线 |

