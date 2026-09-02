"""模型流和 Agent 生命周期事件的 schema 与往返测试。"""

import unittest
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from nova_core import (
    AgentEvent,
    ApprovalRequested,
    ApprovalTransaction,
    Correlation,
    ErrorCategory,
    ErrorInfo,
    GraphInterrupted,
    GraphStarted,
    ModelCompleted,
    ModelErrorInfo,
    ModelErrorKind,
    ModelEvent,
    ModelFailed,
    ModelFinishReason,
    ModelReasoningDelta,
    ModelTextDelta,
    ModelToolCallDelta,
    ModelUsage,
    NodeFinished,
    NodeStarted,
    ReasoningDelta,
    StopReason,
    TextDelta,
    TextPart,
    ToolCall,
    ToolCallFinished,
    ToolCallStarted,
    ToolResult,
    TurnFailed,
    TurnFinished,
    TurnIdentity,
)
from pydantic import BaseModel, TypeAdapter


class EventFields(TypedDict):
    """测试中复用的事件公共字段静态类型。"""

    event_id: str
    seq: int
    occurred_at: datetime
    correlation: Correlation


class CoreEventTests(unittest.TestCase):
    """验证事件类型适合流式传输、持久化和重放。"""

    def setUp(self) -> None:
        self.now = datetime(2026, 9, 2, tzinfo=timezone.utc)
        self.correlation = Correlation(turn_id="turn-1", trace_id="trace-1")
        self.common: EventFields = {
            "event_id": "event-1",
            "seq": 1,
            "occurred_at": self.now,
            "correlation": self.correlation,
        }
        self.call = ToolCall(
            call_id="call-1",
            name="read_file",
            arguments={"path": "README.md"},
            seq=0,
            idempotency_key="turn-1:call-1",
        )
        self.result = ToolResult(
            call_id="call-1",
            name="read_file",
            content_parts=(TextPart(text="完成"),),
            idempotency_key="turn-1:call-1",
        )

    def model_event_examples(self) -> tuple[BaseModel, ...]:
        return (
            ModelTextDelta(delta="文本"),
            ModelReasoningDelta(delta="推理"),
            ModelToolCallDelta(call_id="call-1", seq=0, name="read_file", arguments_delta="{}"),
            ModelUsage(input_tokens=10, output_tokens=5, cached_input_tokens=2),
            ModelCompleted(finish_reason=ModelFinishReason.TOOL_CALLS),
            ModelFailed(
                error=ModelErrorInfo(
                    kind=ModelErrorKind.TIMEOUT,
                    message="超时",
                    retryable=True,
                )
            ),
        )

    def agent_event_examples(self) -> tuple[BaseModel, ...]:
        transaction = ApprovalTransaction(
            approval_id="approval-1",
            identity=TurnIdentity(turn_id="turn-1", session_id="session-1"),
            calls=(self.call,),
            summary="读取文件",
            reasons=("敏感目录",),
            created_at=self.now,
            expires_at=self.now + timedelta(minutes=5),
        )
        return (
            GraphStarted(graph_id="graph-1", graph_spec_hash="sha256:test", **self.common),
            NodeStarted(node_id="llm", invocation_version=1, **self.common),
            NodeFinished(node_id="llm", invocation_version=1, duration_ms=12.5, **self.common),
            TextDelta(delta="文本", **self.common),
            ReasoningDelta(delta="推理", **self.common),
            ToolCallStarted(call=self.call, **self.common),
            ToolCallFinished(result=self.result, **self.common),
            ApprovalRequested(transaction=transaction, **self.common),
            GraphInterrupted(interrupt_id="interrupt-1", reason="等待输入", **self.common),
            TurnFinished(stop_reason=StopReason.COMPLETED, result="完成", **self.common),
            TurnFailed(
                error=ErrorInfo(
                    category=ErrorCategory.INTERNAL,
                    code="internal.failure",
                    message="运行失败",
                ),
                **self.common,
            ),
        )

    def test_every_event_has_schema_and_json_round_trip(self) -> None:
        for event in self.model_event_examples() + self.agent_event_examples():
            with self.subTest(event=type(event).__name__):
                self.assertEqual(type(event).__name__, type(event).model_json_schema()["title"])
                restored = type(event).model_validate_json(event.model_dump_json())
                self.assertEqual(event, restored)

    def test_event_unions_preserve_concrete_types(self) -> None:
        model_adapter: TypeAdapter[ModelEvent] = TypeAdapter(ModelEvent)
        agent_adapter: TypeAdapter[AgentEvent] = TypeAdapter(AgentEvent)
        self.assertIn("discriminator", model_adapter.json_schema())
        self.assertIn("discriminator", agent_adapter.json_schema())

        model_event = self.model_event_examples()[0]
        agent_event = self.agent_event_examples()[-1]
        self.assertIsInstance(model_adapter.validate_json(model_event.model_dump_json()), ModelTextDelta)
        self.assertIsInstance(agent_adapter.validate_json(agent_event.model_dump_json()), TurnFailed)


if __name__ == "__main__":
    unittest.main()
