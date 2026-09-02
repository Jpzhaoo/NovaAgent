"""NovaAgent 跨包传递的稳定值对象。

本模块只保存能够生成 JSON Schema 并完成 JSON 往返的数据，不得放入网络
连接、数据库句柄、锁或协程等运行时资源。开放字段统一收敛到显式的
``extensions``，其余未知字段在边界处直接拒绝。
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self, Union

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator


class _FrozenModel(BaseModel):
    """为所有跨包值对象提供冻结和未知字段拒绝策略。"""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)


class TurnPhase(str, Enum):
    """一次 Turn 对外可观察的生命周期阶段。"""

    RECEIVED = "RECEIVED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StopReason(str, Enum):
    """Agent 结束运行时可持久化、可统计的原因。"""

    COMPLETED = "COMPLETED"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    LOOP_DETECTED = "LOOP_DETECTED"
    MODEL_ERROR = "MODEL_ERROR"
    STRUCTURED_OUTPUT_ERROR = "STRUCTURED_OUTPUT_ERROR"
    CANCELLED = "CANCELLED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"


class MessageRole(str, Enum):
    """对话历史中消息的发送者角色。"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolRisk(str, Enum):
    """工具声明的风险等级；危险工具必须经过策略端口。"""

    SAFE = "SAFE"
    SENSITIVE = "SENSITIVE"
    DANGEROUS = "DANGEROUS"


class ExecutionMode(str, Enum):
    """工具调度方式；独占调用会在批次中形成并发屏障。"""

    PARALLEL = "PARALLEL"
    EXCLUSIVE = "EXCLUSIVE"


class ApprovalState(str, Enum):
    """审批事务状态，显式区分拒绝、过期和运行取消。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PolicyOutcome(str, Enum):
    """策略网关对单次工具调用给出的判定。"""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ModelErrorKind(str, Enum):
    """供应商错误经过 Core 归一化后的可观测分类。"""

    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    PROTOCOL = "PROTOCOL"
    CONTENT = "CONTENT"
    UNKNOWN = "UNKNOWN"


class Session(_FrozenModel):
    """会话的稳定身份和租户边界。"""

    session_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    created_at: AwareDatetime
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class Correlation(_FrozenModel):
    """把请求、事件和工具调用关联到同一条执行链。"""

    turn_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    span_id: str | None = None


class TurnIdentity(_FrozenModel):
    """Turn 的稳定身份；审批与恢复不得替换这些主键。"""

    turn_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    parent_turn_id: str | None = None


class ToolCall(_FrozenModel):
    """模型发起的工具调用，``seq`` 决定结果写回顺序。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    seq: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1)


class TextPart(_FrozenModel):
    """可展示的普通文本内容。"""

    kind: Literal["text"] = "text"
    text: str


class ReasoningPart(_FrozenModel):
    """可按脱敏策略隐藏的推理文本。"""

    kind: Literal["reasoning"] = "reasoning"
    text: str


class ToolCallPart(_FrozenModel):
    """助手消息中已完成组装的工具调用。"""

    kind: Literal["tool_call"] = "tool_call"
    call: ToolCall


class ToolResultPart(_FrozenModel):
    """工具角色消息中与 ``call_id`` 配对的执行结果。"""

    kind: Literal["tool_result"] = "tool_result"
    call_id: str = Field(min_length=1)
    output: str
    is_error: bool = False


ContentPart = Annotated[
    Union[TextPart, ReasoningPart, ToolCallPart, ToolResultPart],
    Field(discriminator="kind"),
]


class Message(_FrozenModel):
    """可重放的对话消息，内容部件通过 ``kind`` 判别。"""

    role: MessageRole
    content_parts: tuple[ContentPart, ...] = Field(min_length=1)
    created_at: AwareDatetime
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_role_parts(self) -> Self:
        """阻止工具结果进入非工具消息，并限制用户侧内容类型。"""

        kinds = {part.kind for part in self.content_parts}
        if self.role is MessageRole.TOOL and kinds != {"tool_result"}:
            raise ValueError("tool message must contain only tool_result parts")
        if self.role is not MessageRole.TOOL and "tool_result" in kinds:
            raise ValueError("tool_result parts require the tool role")
        if self.role in {MessageRole.SYSTEM, MessageRole.USER} and kinds != {"text"}:
            raise ValueError("system and user messages must contain only text parts")
        return self


class ToolDefinition(_FrozenModel):
    """发送给模型的工具 schema 以及安全、并发声明。"""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: dict[str, JsonValue]
    risk: ToolRisk
    execution: ExecutionMode
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class SamplingParams(_FrozenModel):
    """与供应商无关的基础采样参数。"""

    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    max_output_tokens: int = Field(default=4096, gt=0)


class ModelRequest(_FrozenModel):
    """ModelGateway 唯一接受的请求载体。"""

    model: str = Field(min_length=1)
    messages: tuple[Message, ...] = Field(min_length=1)
    tools: tuple[ToolDefinition, ...] = ()
    sampling: SamplingParams = Field(default_factory=SamplingParams)
    correlation: Correlation
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_tool_names(self) -> Self:
        """同一请求不允许用重复名称覆盖工具定义。"""

        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("model request tool names must be unique")
        return self


class ToolResult(_FrozenModel):
    """工具执行后供历史、事件与幂等缓存共用的结果。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    content_parts: tuple[TextPart, ...] = Field(min_length=1)
    is_error: bool = False
    idempotency_key: str = Field(min_length=1)


class PolicyDecision(_FrozenModel):
    """可审计的策略判定；拒绝与审批都必须携带原因。"""

    outcome: PolicyOutcome
    reasons: tuple[str, ...] = Field(min_length=1)
    required_approval: bool = False
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_approval_flag(self) -> Self:
        """保证审批布尔标志与判定枚举不会互相矛盾。"""

        requires_approval = self.outcome is PolicyOutcome.REQUIRE_APPROVAL
        if self.required_approval != requires_approval:
            raise ValueError("required_approval must match REQUIRE_APPROVAL outcome")
        return self


class ApprovalTransaction(_FrozenModel):
    """可跨进程恢复并执行原子判定的人工作业审批。"""

    approval_id: str = Field(min_length=1)
    identity: TurnIdentity
    calls: tuple[ToolCall, ...] = Field(min_length=1)
    state: ApprovalState = ApprovalState.PENDING
    summary: str = Field(min_length=1)
    reasons: tuple[str, ...] = Field(min_length=1)
    created_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def validate_expiration(self) -> Self:
        """审批必须拥有晚于创建时间的确定过期点。"""

        if self.expires_at <= self.created_at:
            raise ValueError("approval expires_at must be later than created_at")
        return self


class TurnSnapshot(_FrozenModel):
    """恢复当前 Turn 所需的值快照，不包含任何运行时对象。"""

    schema_version: int = Field(default=1, ge=1)
    identity: TurnIdentity
    phase: TurnPhase
    messages: tuple[Message, ...] = ()
    pending_calls: tuple[ToolCall, ...] = ()
    last_event_seq: int = Field(default=0, ge=0)
    trace_id: str = Field(min_length=1)
    stop_reason: StopReason | None = None
    result: str | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_terminal_state(self) -> Self:
        """终态必须说明停止原因，非终态不得提前写入停止原因。"""

        terminal = self.phase in {TurnPhase.COMPLETED, TurnPhase.FAILED, TurnPhase.CANCELLED}
        if terminal and self.stop_reason is None:
            raise ValueError("terminal snapshot requires stop_reason")
        if not terminal and self.stop_reason is not None:
            raise ValueError("non-terminal snapshot cannot have stop_reason")
        return self


class ModelErrorInfo(_FrozenModel):
    """供事件和异常共同引用的模型错误摘要。"""

    kind: ModelErrorKind
    message: str = Field(min_length=1)
    retryable: bool
    provider_code: str | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)
