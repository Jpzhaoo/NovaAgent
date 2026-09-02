"""Core 端口的抽象边界与异步签名测试。"""

import inspect
import unittest
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from nova_core import (
    Agent,
    Clock,
    ControlPort,
    Correlation,
    EventSink,
    EventStore,
    IdGenerator,
    Message,
    MessageRole,
    ModelCompleted,
    ModelEvent,
    ModelFinishReason,
    ModelGateway,
    ModelRequest,
    PolicyGateway,
    SessionStore,
    TextPart,
    Tool,
    TurnStore,
)


class ScriptedGateway(ModelGateway):
    """证明 ModelGateway 的同步建流、异步消费签名可实现。"""

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        async def iterate() -> AsyncIterator[ModelEvent]:
            yield ModelCompleted(finish_reason=ModelFinishReason.STOP)

        return iterate()


class FixedClock(Clock):
    """最小时钟实现，用于验证运行时依赖可以替换。"""

    def now(self) -> datetime:
        return datetime(2026, 9, 2, tzinfo=timezone.utc)


class SequentialIds(IdGenerator):
    """最小确定性 ID 生成器。"""

    def __init__(self) -> None:
        self.value = 0

    def new_id(self, namespace: str) -> str:
        self.value += 1
        return f"{namespace}-{self.value}"


class CorePortTests(unittest.IsolatedAsyncioTestCase):
    """确保端口保持抽象，并能由脚本实现替换。"""

    def test_required_runtime_boundaries_are_abstract(self) -> None:
        ports: tuple[type[object], ...] = (
            Agent,
            ModelGateway,
            Tool,
            PolicyGateway,
            SessionStore,
            TurnStore,
            EventStore,
            EventSink,
            ControlPort,
            Clock,
            IdGenerator,
        )
        for port in ports:
            with self.subTest(port=port.__name__):
                self.assertTrue(inspect.isabstract(port))
                with self.assertRaises(TypeError):
                    port()

    async def test_model_gateway_exposes_async_event_stream(self) -> None:
        now = datetime(2026, 9, 2, tzinfo=timezone.utc)
        request = ModelRequest(
            model="scripted",
            messages=(
                Message(
                    role=MessageRole.USER,
                    content_parts=(TextPart(text="你好"),),
                    created_at=now,
                ),
            ),
            correlation=Correlation(turn_id="turn-1", trace_id="trace-1"),
        )
        events = [event async for event in ScriptedGateway().stream(request)]
        self.assertEqual([ModelCompleted(finish_reason=ModelFinishReason.STOP)], events)

    def test_clock_and_id_generator_are_deterministic_in_tests(self) -> None:
        clock = FixedClock()
        ids = SequentialIds()
        self.assertEqual(timezone.utc, clock.now().tzinfo)
        self.assertEqual("event-1", ids.new_id("event"))
        self.assertEqual("event-2", ids.new_id("event"))


if __name__ == "__main__":
    unittest.main()
