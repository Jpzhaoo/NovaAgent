# Phase 1：Core Types 与端口交付索引

Phase 1 将跨包数据、事件、异常和运行时依赖收敛到 `nova-core`。Core 只依赖
Pydantic，不包含 HTTP、数据库、Web、Graph 或 ReAct 的具体实现。

## 交付与证据

| PRD 任务 | 实现 | 验证证据 |
|---|---|---|
| 枚举、冻结模型与序列化 | `nova_core.types`：Message、Tool、ModelRequest、审批、snapshot 等 | 未知字段、冻结、带时区时间、角色配对、JSON 往返测试 |
| 错误族 | `nova_core.errors`：统一 `ErrorInfo` 与六类异常 | 稳定 code、retryable、correlation 和上下文测试 |
| typed 事件 | `nova_core.events`：`ModelEvent`、`AgentEvent` 判别联合 | 每个具体事件及联合 schema/往返测试 |
| Core ABC 端口 | `nova_core.ports`：Agent、模型、工具、策略、存储、事件、控制、时钟和 ID | 抽象性、异步流签名与可替换实现测试 |
| InMemory fake | `nova_core.fakes`：脚本 adapter、内存存储、确定性时钟/ID | 乐观锁、连续事件序号、Turn 隔离和脚本耗尽测试 |
| Schema 文档 | [`core-schemas.json`](core-schemas.json) | `make schema-check` 防止公开类型与文档漂移 |
| 独立安装 | `tools/check_core_distribution.py` | wheel 离线构建/安装、隔离导入、禁用 socket 后生成 schema |
| 服务器人工验收 | [`server-manual-test.md`](server-manual-test.md) | 可复制的环境、功能、负向和分发测试步骤 |

## 当前实测基线

- `nova-core` Python 源码：1,452 行，低于 Phase 1 的 5,000 行上限。
- 公开 Pydantic 模型/事件：38 个；枚举：11 个；判别联合：3 个。
- ABC 端口：11 个，其中 Session/Turn/Event Store 属于同一存储端口组。
- 单元测试：23 项通过。
- strict mypy：0 error；Ruff：0 error。
- Core 分支覆盖率：94%，高于 90% 门禁。
- Python 3.12/3.13：由 GitHub Actions 的 `dev` 矩阵执行同一 `make check`。

## 验收入口

```text
uv sync --locked
make check
```

`make check` 依次验证包结构、schema 漂移、单元测试、Ruff、strict mypy、
覆盖率和独立 wheel。它不请求模型、数据库或任何运行期网络服务。
