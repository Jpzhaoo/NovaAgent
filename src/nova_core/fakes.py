"""Core 端口的无网络 InMemory fake 与确定性测试依赖。"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Iterable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .errors import ConcurrencyConflictError, ContractViolationError
from .events import AgentEvent, ModelEvent
from .ports import (
    Agent,
    Clock,
    ControlPort,
    EventSink,
    EventStore,
    IdGenerator,
    ModelGateway,
    PolicyGateway,
    SessionStore,
    Tool,
    TurnStore,
)
from .types import (
    AgentRequest,
    ControlCommand,
    Correlation,
    Message,
    ModelRequest,
    PolicyDecision,
    Session,
    SessionHistory,
    ToolCall,
    ToolDefinition,
    ToolResult,
    TurnIdentity,
    TurnSnapshot,
)


class ScriptedAgent(Agent):
    """按请求顺序返回预设事件流的 Agent fake。"""

    def __init__(self, scripts: Iterable[Iterable[AgentEvent]]) -> None:
        self._scripts = deque(tuple(script) for script in scripts)
        self.requests: list[AgentRequest] = []

    def stream(self, request: AgentRequest) -> AsyncIterator[AgentEvent]:
        self.requests.append(request)
        if not self._scripts:
            raise ContractViolationError("fake.script_exhausted", "Agent 事件脚本已耗尽")
        events = self._scripts.popleft()

        async def iterate() -> AsyncIterator[AgentEvent]:
            for event in events:
                yield event

        return iterate()


class ScriptedModelGateway(ModelGateway):
    """按请求顺序返回预设 ModelEvent 的离线模型 fake。"""

    def __init__(self, scripts: Iterable[Iterable[ModelEvent]]) -> None:
        self._scripts = deque(tuple(script) for script in scripts)
        self.requests: list[ModelRequest] = []

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        self.requests.append(request)
        if not self._scripts:
            raise ContractViolationError("fake.script_exhausted", "模型事件脚本已耗尽")
        events = self._scripts.popleft()

        async def iterate() -> AsyncIterator[ModelEvent]:
            for event in events:
                yield event

        return iterate()


class ScriptedTool(Tool):
    """依次返回预设结果并记录执行/取消调用的工具 fake。"""

    def __init__(self, definition: ToolDefinition, results: Iterable[ToolResult]) -> None:
        self._definition = definition
        self._results = deque(results)
        self.calls: list[tuple[ToolCall, Correlation]] = []
        self.cancelled_calls: list[tuple[ToolCall, Correlation]] = []

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, call: ToolCall, correlation: Correlation) -> ToolResult:
        self.calls.append((call, correlation))
        if not self._results:
            raise ContractViolationError("fake.script_exhausted", "工具结果脚本已耗尽")
        result = self._results.popleft()
        if result.call_id != call.call_id or result.name != call.name:
            raise ContractViolationError("fake.result_mismatch", "工具结果与调用身份不匹配")
        return result

    async def on_cancel(self, call: ToolCall, correlation: Correlation) -> None:
        self.cancelled_calls.append((call, correlation))


class ScriptedPolicyGateway(PolicyGateway):
    """按调用顺序返回预设判定的策略 fake。"""

    def __init__(self, decisions: Iterable[PolicyDecision]) -> None:
        self._decisions = deque(decisions)
        self.calls: list[tuple[ToolCall, ToolDefinition, Correlation]] = []

    async def evaluate(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        correlation: Correlation,
    ) -> PolicyDecision:
        self.calls.append((call, definition, correlation))
        if not self._decisions:
            raise ContractViolationError("fake.script_exhausted", "策略判定脚本已耗尽")
        return self._decisions.popleft()


class InMemorySessionStore(SessionStore):
    """带乐观锁的原始 Session 历史存储 fake。"""

    def __init__(self) -> None:
        self._histories: dict[str, SessionHistory] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: Session) -> None:
        async with self._lock:
            current = self._histories.get(session.session_id)
            if current is not None:
                raise ConcurrencyConflictError(session.session_id, 0, current.version)
            self._histories[session.session_id] = SessionHistory(session=session)

    async def get(self, session_id: str) -> SessionHistory | None:
        async with self._lock:
            return self._histories.get(session_id)

    async def append_messages(
        self,
        session_id: str,
        messages: tuple[Message, ...],
        expected_version: int,
    ) -> int:
        if not messages:
            raise ContractViolationError("session.empty_append", "追加消息不能为空")
        async with self._lock:
            current = self._histories.get(session_id)
            if current is None:
                raise ContractViolationError("session.not_found", f"会话不存在：{session_id}")
            if current.version != expected_version:
                raise ConcurrencyConflictError(session_id, expected_version, current.version)
            new_version = current.version + 1
            self._histories[session_id] = SessionHistory(
                session=current.session,
                messages=current.messages + messages,
                version=new_version,
            )
            return new_version


class InMemoryTurnStore(TurnStore):
    """以 compare-and-swap 保存最新 TurnSnapshot 的存储 fake。"""

    def __init__(self) -> None:
        self._snapshots: dict[str, tuple[TurnSnapshot, int]] = {}
        self._lock = asyncio.Lock()

    async def load(self, turn_id: str) -> TurnSnapshot | None:
        async with self._lock:
            record = self._snapshots.get(turn_id)
            return record[0] if record is not None else None

    async def save(self, snapshot: TurnSnapshot, expected_version: int | None) -> int:
        turn_id = snapshot.identity.turn_id
        async with self._lock:
            current = self._snapshots.get(turn_id)
            actual_version = current[1] if current is not None else 0
            valid_create = current is None and expected_version is None
            valid_update = current is not None and expected_version == actual_version
            if not (valid_create or valid_update):
                raise ConcurrencyConflictError(turn_id, expected_version or 0, actual_version)
            new_version = actual_version + 1
            self._snapshots[turn_id] = (snapshot, new_version)
            return new_version


class InMemoryEventStore(EventStore):
    """强制每个 Turn 事件序号连续的 append-only 存储 fake。"""

    def __init__(self) -> None:
        self._events: dict[str, list[AgentEvent]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def append(self, event: AgentEvent) -> None:
        turn_id = event.correlation.turn_id
        async with self._lock:
            events = self._events[turn_id]
            expected_seq = len(events)
            if event.seq != expected_seq:
                raise ConcurrencyConflictError(f"event:{turn_id}", expected_seq, event.seq)
            events.append(event)

    async def read(self, turn_id: str, after_seq: int = -1) -> tuple[AgentEvent, ...]:
        async with self._lock:
            return tuple(event for event in self._events.get(turn_id, ()) if event.seq > after_seq)


class InMemoryEventSink(EventSink):
    """按发布顺序收集实时事件的观测 fake。"""

    def __init__(self) -> None:
        self.events: list[AgentEvent] = []
        self._lock = asyncio.Lock()

    async def publish(self, event: AgentEvent) -> None:
        async with self._lock:
            self.events.append(event)


class InMemoryControlPort(ControlPort):
    """按 Turn 隔离 FIFO 控制命令的端口 fake。"""

    def __init__(self) -> None:
        self._commands: dict[str, deque[ControlCommand]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def send(self, command: ControlCommand) -> None:
        """测试或 adapter 使用的命令投递入口。"""

        async with self._lock:
            self._commands[command.identity.turn_id].append(command)

    async def poll(self, identity: TurnIdentity) -> ControlCommand | None:
        async with self._lock:
            commands = self._commands.get(identity.turn_id)
            if not commands:
                return None
            command = commands.popleft()
            if command.identity != identity:
                raise ContractViolationError("control.identity_mismatch", "控制命令身份不匹配")
            return command


class SystemClock(Clock):
    """生产环境使用的 UTC 系统时钟。"""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class DeterministicClock(Clock):
    """可显式推进、不会读取系统时间的测试时钟。"""

    def __init__(self, current: datetime) -> None:
        if current.utcoffset() is None:
            raise ValueError("DeterministicClock requires a timezone-aware datetime")
        self._current = current

    def now(self) -> datetime:
        return self._current

    def advance(self, delta: timedelta) -> datetime:
        if delta.total_seconds() < 0:
            raise ValueError("clock cannot move backwards")
        self._current += delta
        return self._current


class SequentialIdGenerator(IdGenerator):
    """按命名空间递增、适合断言的确定性 ID 生成器。"""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)

    def new_id(self, namespace: str) -> str:
        if not namespace:
            raise ValueError("ID namespace cannot be empty")
        self._counters[namespace] += 1
        return f"{namespace}-{self._counters[namespace]}"


class UuidIdGenerator(IdGenerator):
    """生产环境使用的随机 UUID4 ID 生成器。"""

    def new_id(self, namespace: str) -> str:
        if not namespace:
            raise ValueError("ID namespace cannot be empty")
        return f"{namespace}-{uuid4()}"
