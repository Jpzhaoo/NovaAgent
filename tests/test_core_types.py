"""Core 值对象的边界、schema 与 JSON 往返测试。"""

import unittest
from datetime import datetime, timedelta, timezone

from nova_core import (
    AgentRequest,
    ApprovalState,
    ApprovalTransaction,
    ContentPart,
    ControlCommand,
    ControlCommandKind,
    Correlation,
    ErrorCategory,
    ErrorInfo,
    ExecutionMode,
    Message,
    MessageRole,
    ModelErrorInfo,
    ModelErrorKind,
    ModelRequest,
    PolicyDecision,
    PolicyOutcome,
    ReasoningPart,
    SamplingParams,
    Session,
    SessionHistory,
    StopReason,
    TextPart,
    ToolCall,
    ToolCallPart,
    ToolDefinition,
    ToolResult,
    ToolResultPart,
    ToolRisk,
    TurnIdentity,
    TurnPhase,
    TurnSnapshot,
)
from pydantic import BaseModel, TypeAdapter, ValidationError


class CoreTypeBoundaryTests(unittest.TestCase):
    """证明所有公开模型都遵守同一组跨包数据约束。"""

    def setUp(self) -> None:
        """构造带时区的稳定样例，避免测试依赖系统时钟。"""

        self.now = datetime(2026, 9, 2, tzinfo=timezone.utc)
        self.identity = TurnIdentity(turn_id="turn-1", session_id="session-1")
        self.call = ToolCall(
            call_id="call-1",
            name="read_file",
            arguments={"path": "README.md"},
            seq=0,
            idempotency_key="turn-1:call-1",
        )
        self.user_message = Message(
            role=MessageRole.USER,
            content_parts=(TextPart(text="读取说明"),),
            created_at=self.now,
        )
        self.tool = ToolDefinition(
            name="read_file",
            description="读取工作区文件",
            input_schema={"type": "object", "required": ["path"]},
            risk=ToolRisk.SAFE,
            execution=ExecutionMode.PARALLEL,
        )

    def public_model_examples(self) -> tuple[BaseModel, ...]:
        """集中列出每一个公开 Pydantic 模型的合法样例。"""

        return (
            Session(session_id="session-1", tenant_id="tenant-1", created_at=self.now),
            Correlation(turn_id="turn-1", trace_id="trace-1", span_id="span-1"),
            self.identity,
            self.call,
            TextPart(text="文本"),
            ReasoningPart(text="推理"),
            ToolCallPart(call=self.call),
            ToolResultPart(call_id="call-1", output="完成"),
            self.user_message,
            self.tool,
            SamplingParams(temperature=0.2, top_p=0.9, max_output_tokens=512),
            ModelRequest(
                model="scripted",
                messages=(self.user_message,),
                tools=(self.tool,),
                correlation=Correlation(turn_id="turn-1", trace_id="trace-1"),
            ),
            ToolResult(
                call_id="call-1",
                name="read_file",
                content_parts=(TextPart(text="完成"),),
                idempotency_key="turn-1:call-1",
            ),
            PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("安全读取",)),
            ApprovalTransaction(
                approval_id="approval-1",
                identity=self.identity,
                calls=(self.call,),
                state=ApprovalState.PENDING,
                summary="读取工作区说明",
                reasons=("需要人工确认",),
                created_at=self.now,
                expires_at=self.now + timedelta(minutes=10),
            ),
            TurnSnapshot(
                identity=self.identity,
                phase=TurnPhase.COMPLETED,
                messages=(self.user_message,),
                last_event_seq=3,
                trace_id="trace-1",
                stop_reason=StopReason.COMPLETED,
                result="完成",
            ),
            ModelErrorInfo(
                kind=ModelErrorKind.TIMEOUT,
                message="模型请求超时",
                retryable=True,
            ),
            ErrorInfo(
                category=ErrorCategory.MODEL,
                code="model.timeout",
                message="模型请求超时",
                retryable=True,
            ),
            AgentRequest(
                identity=self.identity,
                messages=(self.user_message,),
                correlation=Correlation(turn_id="turn-1", trace_id="trace-1"),
            ),
            SessionHistory(
                session=Session(
                    session_id="session-1",
                    tenant_id="tenant-1",
                    created_at=self.now,
                ),
                messages=(self.user_message,),
                version=1,
            ),
            ControlCommand(
                command_id="command-1",
                kind=ControlCommandKind.CANCEL,
                identity=self.identity,
                issued_at=self.now,
                reason="用户取消",
            ),
        )

    def test_every_public_model_has_schema_and_json_round_trip(self) -> None:
        """防止新增公共模型时漏掉 schema 或反序列化能力。"""

        for model in self.public_model_examples():
            with self.subTest(model=type(model).__name__):
                schema = type(model).model_json_schema()
                self.assertEqual(type(model).__name__, schema["title"])
                restored = type(model).model_validate_json(model.model_dump_json())
                self.assertEqual(model, restored)

    def test_content_union_has_discriminator_schema_and_round_trip(self) -> None:
        """判别联合必须保留具体部件类型，不能退化为匿名字典。"""

        adapter: TypeAdapter[ContentPart] = TypeAdapter(ContentPart)
        schema = adapter.json_schema()
        self.assertIn("discriminator", schema)
        restored = adapter.validate_json(ToolCallPart(call=self.call).model_dump_json())
        self.assertIsInstance(restored, ToolCallPart)

    def test_unknown_fields_mutation_empty_id_and_naive_time_are_rejected(self) -> None:
        """同时覆盖冻结、额外字段、稳定 ID 与时区边界。"""

        with self.assertRaises(ValidationError):
            Correlation.model_validate(
                {"turn_id": "turn-1", "trace_id": "trace-1", "unexpected": "x"}
            )
        correlation = Correlation(turn_id="turn-1", trace_id="trace-1")
        with self.assertRaises(ValidationError):
            correlation.turn_id = "changed"
        with self.assertRaises(ValidationError):
            TurnIdentity(turn_id="", session_id="session-1")
        with self.assertRaises(ValidationError):
            Session(
                session_id="session-1",
                tenant_id="tenant-1",
                created_at=datetime(2026, 9, 2),
            )

    def test_message_role_and_tool_result_pairing(self) -> None:
        """工具结果只能由 tool 角色承载，用户消息只能承载文本。"""

        with self.assertRaises(ValidationError):
            Message(
                role=MessageRole.ASSISTANT,
                content_parts=(ToolResultPart(call_id="call-1", output="完成"),),
                created_at=self.now,
            )
        with self.assertRaises(ValidationError):
            Message(
                role=MessageRole.USER,
                content_parts=(ToolCallPart(call=self.call),),
                created_at=self.now,
            )

    def test_model_request_rejects_duplicate_tool_names(self) -> None:
        """工具名称冲突必须在模型调用前暴露。"""

        with self.assertRaises(ValidationError):
            ModelRequest(
                model="scripted",
                messages=(self.user_message,),
                tools=(self.tool, self.tool),
                correlation=Correlation(turn_id="turn-1", trace_id="trace-1"),
            )

    def test_policy_approval_flag_and_expiration_are_consistent(self) -> None:
        """审批判定和时间窗口不能形成互相矛盾的持久化状态。"""

        with self.assertRaises(ValidationError):
            PolicyDecision(
                outcome=PolicyOutcome.ALLOW,
                reasons=("安全",),
                required_approval=True,
            )
        with self.assertRaises(ValidationError):
            ApprovalTransaction(
                approval_id="approval-1",
                identity=self.identity,
                calls=(self.call,),
                summary="读取说明",
                reasons=("人工确认",),
                created_at=self.now,
                expires_at=self.now,
            )

    def test_snapshot_terminal_state_requires_stop_reason(self) -> None:
        """终态快照必须可解释，运行中快照不得提前写停止原因。"""

        with self.assertRaises(ValidationError):
            TurnSnapshot(
                identity=self.identity,
                phase=TurnPhase.COMPLETED,
                trace_id="trace-1",
            )
        with self.assertRaises(ValidationError):
            TurnSnapshot(
                identity=self.identity,
                phase=TurnPhase.RUNNING,
                trace_id="trace-1",
                stop_reason=StopReason.COMPLETED,
            )


if __name__ == "__main__":
    unittest.main()
