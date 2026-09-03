# Phase 1 服务器人工测试手册

本文用于在 Linux 服务器上人工验收 `dev` 分支的 Core Types 与端口。所有命令
默认在仓库根目录执行；除首次安装 uv 和下载锁定依赖外，测试阶段不访问外部
模型、数据库或 Web 服务。

## 1. 前置条件与检出

服务器需要 Git、curl 和常见构建工具，CPU 架构可为 x86_64 或 aarch64。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
git clone https://github.com/Jpzhaoo/NovaAgent.git
cd NovaAgent
git switch dev
git pull --ff-only origin dev
```

预期：`uv` 版本不低于 `0.12.9`；当前分支为 `dev`，工作区没有本地修改。

```bash
git status --short --branch
```

预期首行形如 `## dev...origin/dev`，后面没有文件列表。

## 2. 用 uv 创建锁定环境

```bash
uv sync --locked --python 3.12
uv run --frozen python --version
uv lock --check
```

预期：Python 为 3.12.x，`uv lock --check` 退出码为 0。`--locked/--frozen`
保证服务器不会静默修改依赖版本或 `uv.lock`。

## 3. 一键质量验收

```bash
make check
```

必须同时看到以下结果：

- structural baseline checks passed；
- core schema catalog is current；
- 23 项单元测试为 `OK`；
- Ruff 为 `All checks passed!`；
- mypy 为 `Success: no issues found`；
- Core 总覆盖率不低于 90%；
- 最后一行为 `nova-core distribution check passed`。

任一子项非零退出都视为 Phase 1 验收失败，不能只重跑并忽略失败项。

## 4. 手动验证模型边界

运行下面的 Python 脚本，验证冻结、未知字段、时区和 JSON 往返：

```bash
uv run --frozen python - <<'PY'
from datetime import datetime, timezone

from pydantic import ValidationError
from nova_core import Correlation, Message, MessageRole, TextPart

now = datetime.now(timezone.utc)
message = Message(
    role=MessageRole.USER,
    content_parts=(TextPart(text="服务器人工测试"),),
    created_at=now,
)
restored = Message.model_validate_json(message.model_dump_json())
assert restored == message

try:
    Correlation.model_validate(
        {"turn_id": "turn-1", "trace_id": "trace-1", "unknown": True}
    )
except ValidationError:
    pass
else:
    raise AssertionError("未知字段没有被拒绝")

try:
    message.role = MessageRole.ASSISTANT
except ValidationError:
    pass
else:
    raise AssertionError("冻结模型仍可修改")

print("PASS: frozen/extra/timezone/json round-trip")
PY
```

预期只输出 `PASS: frozen/extra/timezone/json round-trip`。

## 5. 手动验证判别联合与角色配对

```bash
uv run --frozen python - <<'PY'
from datetime import datetime, timezone

from pydantic import TypeAdapter, ValidationError
from nova_core import ContentPart, Message, MessageRole, ToolResultPart

adapter = TypeAdapter(ContentPart)
part = adapter.validate_json(
    '{"kind":"tool_result","call_id":"call-1","output":"ok","is_error":false}'
)
assert isinstance(part, ToolResultPart)

try:
    Message(
        role=MessageRole.ASSISTANT,
        content_parts=(part,),
        created_at=datetime.now(timezone.utc),
    )
except ValidationError:
    pass
else:
    raise AssertionError("assistant 错误承载了 tool_result")

print("PASS: discriminator/message pairing")
PY
```

预期输出 `PASS: discriminator/message pairing`。

## 6. 手动验证端口与 InMemory fake

此步骤检查 ABC 不可直接实例化、Session 乐观锁、事件序号和 ControlPort 的
Turn 隔离。

```bash
uv run --frozen python - <<'PY'
import asyncio
import inspect
from datetime import datetime, timezone

from nova_core import (
    Agent,
    ConcurrencyConflictError,
    ControlCommand,
    ControlCommandKind,
    Correlation,
    InMemoryControlPort,
    InMemoryEventStore,
    InMemorySessionStore,
    Message,
    MessageRole,
    Session,
    TextDelta,
    TextPart,
    TurnIdentity,
)

async def main() -> None:
    assert inspect.isabstract(Agent)
    now = datetime.now(timezone.utc)
    identity = TurnIdentity(turn_id="turn-1", session_id="session-1")

    sessions = InMemorySessionStore()
    await sessions.create(
        Session(session_id="session-1", tenant_id="tenant-1", created_at=now)
    )
    message = Message(
        role=MessageRole.USER,
        content_parts=(TextPart(text="hello"),),
        created_at=now,
    )
    assert await sessions.append_messages("session-1", (message,), 0) == 1
    try:
        await sessions.append_messages("session-1", (message,), 0)
    except ConcurrencyConflictError:
        pass
    else:
        raise AssertionError("过期版本未触发冲突")

    events = InMemoryEventStore()
    correlation = Correlation(turn_id="turn-1", trace_id="trace-1")
    await events.append(
        TextDelta(
            event_id="event-0",
            seq=0,
            occurred_at=now,
            correlation=correlation,
            delta="ok",
        )
    )
    assert len(await events.read("turn-1")) == 1

    control = InMemoryControlPort()
    command = ControlCommand(
        command_id="command-1",
        kind=ControlCommandKind.CANCEL,
        identity=identity,
        issued_at=now,
        reason="人工测试",
    )
    await control.send(command)
    assert await control.poll(TurnIdentity(turn_id="turn-2", session_id="session-1")) is None
    assert await control.poll(identity) == command
    print("PASS: ABC/session/event/control")

asyncio.run(main())
PY
```

预期输出 `PASS: ABC/session/event/control`。

## 7. 手动验证 schema 文档

```bash
make schema-check
uv run --frozen python - <<'PY'
import json
from pathlib import Path

catalog = json.loads(Path("docs/phase1/core-schemas.json").read_text())
assert catalog["schema_version"] == 1
assert len(catalog["models"]) == 38
assert len(catalog["enums"]) == 11
assert set(catalog["unions"]) == {"AgentEvent", "ContentPart", "ModelEvent"}
print("PASS: schema catalog")
PY
```

如开发中有意改变公共类型，先执行 `make schema`，审查 JSON diff 后再提交；
不要在 CI 中自动覆盖 catalog。

## 8. 手动验证独立 wheel 与禁网导入

```bash
make package-check
```

该命令会在临时目录完成以下操作：

1. 使用 uv cache 离线构建 `nova-core` wheel；
2. 检查 wheel 包含 `py.typed` 和全部 Core 模块，且只声明 Pydantic 依赖；
3. 在临时 venv 中离线安装 wheel；
4. 使用 `python -S`，禁用 socket 后从 wheel 导入并生成 schema；
5. 自动删除临时目录。

预期最后两行包含 `isolated nova-core import passed` 和
`nova-core distribution check passed (offline build/install/import)`。

## 9. Python 3.13 补充验收

服务器同时有 Python 3.13 时，再执行：

```bash
uv sync --locked --python 3.13
make check
uv sync --locked --python 3.12
```

两个解释器都必须通过；最后一条命令将日常环境恢复到仓库默认的 3.12。

## 10. 故障排查与报告模板

- `uv: command not found`：重新加载 shell，或把 `$HOME/.local/bin` 加入 PATH。
- `uv lock --check` 失败：确认位于最新 `origin/dev`，不要手工改锁文件。
- `ModuleNotFoundError: nova_core`：确认先执行 `uv sync --locked`，并从仓库根目录运行。
- `schema catalog is stale`：保存 `git diff`；只有公共契约确实变化时才运行 `make schema`。
- `package-check` 的 offline build 失败：先确认 `uv sync --locked` 已完成，使锁定的构建依赖进入 uv cache。

报告问题时附上以下输出，禁止附带 token、密钥或真实用户数据：

```bash
uname -a
uv --version
uv run --frozen python --version
git rev-parse HEAD
git status --short --branch
make check
```
