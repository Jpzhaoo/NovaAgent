"""InMemory fake 的端口一致性与边界测试。"""

import unittest
from datetime import datetime, timedelta, timezone

from nova_core import (
    AgentRequest,
    ConcurrencyConflictError,
    ContractViolationError,
    ControlCommand,
    ControlCommandKind,
    Correlation,
    DeterministicClock,
    ExecutionMode,
    InMemoryControlPort,
    InMemoryEventSink,
    InMemoryEventStore,
    InMemorySessionStore,
    InMemoryTurnStore,
    Message,
    MessageRole,
    ModelCompleted,
    ModelFinishReason,
    ModelRequest,
    PolicyDecision,
    PolicyOutcome,
    ScriptedAgent,
    ScriptedModelGateway,
    ScriptedPolicyGateway,
    ScriptedTool,
    SequentialIdGenerator,
    Session,
    StopReason,
    TextDelta,
    TextPart,
    ToolCall,
    ToolDefinition,
    ToolResult,
    ToolRisk,
    TurnFinished,
    TurnIdentity,
    TurnPhase,
    TurnSnapshot,
    UuidIdGenerator,
)


class CoreFakeTests(unittest.IsolatedAsyncioTestCase):
    """验证 fake 与端口声明共享关键不变量。"""

    def setUp(self) -> None:
        self.now = datetime(2026, 9, 2, tzinfo=timezone.utc)
        self.identity = TurnIdentity(turn_id="turn-1", session_id="session-1")
        self.correlation = Correlation(turn_id="turn-1", trace_id="trace-1")
        self.message = Message(
            role=MessageRole.USER,
            content_parts=(TextPart(text="你好"),),
            created_at=self.now,
        )
        self.call = ToolCall(
            call_id="call-1",
            name="read_file",
            arguments={"path": "README.md"},
            seq=0,
            idempotency_key="turn-1:call-1",
        )
        self.definition = ToolDefinition(
            name="read_file",
            description="读取文件",
            input_schema={"type": "object"},
            risk=ToolRisk.SAFE,
            execution=ExecutionMode.PARALLEL,
        )
        self.result = ToolResult(
            call_id="call-1",
            name="read_file",
            content_parts=(TextPart(text="完成"),),
            idempotency_key="turn-1:call-1",
        )

    async def test_scripted_agent_gateway_tool_and_policy_record_calls(self) -> None:
        finish = TurnFinished(
            event_id="event-0",
            seq=0,
            occurred_at=self.now,
            correlation=self.correlation,
            stop_reason=StopReason.COMPLETED,
            result="完成",
        )
        agent = ScriptedAgent(((finish,),))
        agent_request = AgentRequest(
            identity=self.identity,
            messages=(self.message,),
            correlation=self.correlation,
        )
        self.assertEqual([finish], [event async for event in agent.stream(agent_request)])
        self.assertEqual([agent_request], agent.requests)

        completed = ModelCompleted(finish_reason=ModelFinishReason.STOP)
        gateway = ScriptedModelGateway(((completed,),))
        model_request = ModelRequest(
            model="scripted",
            messages=(self.message,),
            correlation=self.correlation,
        )
        self.assertEqual([completed], [event async for event in gateway.stream(model_request)])

        tool = ScriptedTool(self.definition, (self.result,))
        self.assertEqual(self.result, await tool.execute(self.call, self.correlation))
        await tool.on_cancel(self.call, self.correlation)
        self.assertEqual(1, len(tool.cancelled_calls))

        decision = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("安全读取",))
        policy = ScriptedPolicyGateway((decision,))
        self.assertEqual(
            decision,
            await policy.evaluate(self.call, self.definition, self.correlation),
        )

        with self.assertRaises(ContractViolationError):
            gateway.stream(model_request)

    async def test_session_and_turn_stores_enforce_optimistic_versions(self) -> None:
        sessions = InMemorySessionStore()
        session = Session(session_id="session-1", tenant_id="tenant-1", created_at=self.now)
        await sessions.create(session)
        self.assertEqual(1, await sessions.append_messages("session-1", (self.message,), 0))
        history = await sessions.get("session-1")
        self.assertIsNotNone(history)
        self.assertEqual((self.message,), history.messages if history else ())
        with self.assertRaises(ConcurrencyConflictError):
            await sessions.append_messages("session-1", (self.message,), 0)

        turns = InMemoryTurnStore()
        running = TurnSnapshot(
            identity=self.identity,
            phase=TurnPhase.RUNNING,
            trace_id="trace-1",
        )
        self.assertEqual(1, await turns.save(running, None))
        self.assertEqual(running, await turns.load("turn-1"))
        with self.assertRaises(ConcurrencyConflictError):
            await turns.save(running, None)

    async def test_event_store_sink_and_control_are_ordered_and_isolated(self) -> None:
        first = TextDelta(
            event_id="event-0",
            seq=0,
            occurred_at=self.now,
            correlation=self.correlation,
            delta="你",
        )
        second = TextDelta(
            event_id="event-1",
            seq=1,
            occurred_at=self.now,
            correlation=self.correlation,
            delta="好",
        )
        store = InMemoryEventStore()
        await store.append(first)
        await store.append(second)
        self.assertEqual((second,), await store.read("turn-1", after_seq=0))
        with self.assertRaises(ConcurrencyConflictError):
            await store.append(second)

        sink = InMemoryEventSink()
        await sink.publish(first)
        await sink.publish(second)
        self.assertEqual([first, second], sink.events)

        control = InMemoryControlPort()
        command = ControlCommand(
            command_id="command-1",
            kind=ControlCommandKind.CANCEL,
            identity=self.identity,
            issued_at=self.now,
            reason="用户取消",
        )
        await control.send(command)
        other = TurnIdentity(turn_id="turn-2", session_id="session-1")
        self.assertIsNone(await control.poll(other))
        self.assertEqual(command, await control.poll(self.identity))
        self.assertIsNone(await control.poll(self.identity))

    def test_clock_and_id_fakes_are_deterministic(self) -> None:
        clock = DeterministicClock(self.now)
        self.assertEqual(self.now + timedelta(seconds=2), clock.advance(timedelta(seconds=2)))
        with self.assertRaises(ValueError):
            clock.advance(timedelta(seconds=-1))

        ids = SequentialIdGenerator()
        self.assertEqual("event-1", ids.new_id("event"))
        self.assertEqual("turn-1", ids.new_id("turn"))
        self.assertNotEqual(UuidIdGenerator().new_id("event"), UuidIdGenerator().new_id("event"))


if __name__ == "__main__":
    unittest.main()
