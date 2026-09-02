"""模型流与 Agent 运行时使用的判别事件契约。"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import AwareDatetime, Field

from .types import (
    ApprovalTransaction,
    Correlation,
    ErrorInfo,
    ModelErrorInfo,
    StopReason,
    ToolCall,
    ToolResult,
    _FrozenModel,
)


class ModelFinishReason(str, Enum):
    """供应商完成原因经过协议适配后的稳定分类。"""

    STOP = "STOP"
    TOOL_CALLS = "TOOL_CALLS"
    LENGTH = "LENGTH"
    CONTENT_FILTER = "CONTENT_FILTER"


class ModelTextDelta(_FrozenModel):
    """模型流中新增的可展示文本。"""

    kind: Literal["model_text_delta"] = "model_text_delta"
    delta: str = Field(min_length=1)


class ModelReasoningDelta(_FrozenModel):
    """模型流中可按策略隐藏的推理增量。"""

    kind: Literal["model_reasoning_delta"] = "model_reasoning_delta"
    delta: str = Field(min_length=1)


class ModelToolCallDelta(_FrozenModel):
    """模型流中按序到达的工具名称或 JSON 参数片段。"""

    kind: Literal["model_tool_call_delta"] = "model_tool_call_delta"
    call_id: str = Field(min_length=1)
    seq: int = Field(ge=0)
    name: str | None = None
    arguments_delta: str = ""


class ModelUsage(_FrozenModel):
    """一次模型调用累计报告的 token 用量。"""

    kind: Literal["model_usage"] = "model_usage"
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)


class ModelCompleted(_FrozenModel):
    """模型流正常结束，并给出归一化完成原因。"""

    kind: Literal["model_completed"] = "model_completed"
    finish_reason: ModelFinishReason


class ModelFailed(_FrozenModel):
    """模型流以结构化供应商错误结束。"""

    kind: Literal["model_failed"] = "model_failed"
    error: ModelErrorInfo


ModelEvent = Annotated[
    Union[
        ModelTextDelta,
        ModelReasoningDelta,
        ModelToolCallDelta,
        ModelUsage,
        ModelCompleted,
        ModelFailed,
    ],
    Field(discriminator="kind"),
]


class _AgentEventBase(_FrozenModel):
    """所有运行时事件共享的顺序、时间和追踪字段。"""

    event_id: str = Field(min_length=1)
    seq: int = Field(ge=0)
    occurred_at: AwareDatetime
    correlation: Correlation


class GraphStarted(_AgentEventBase):
    """图实例通过 bootstrap 后开始调度。"""

    kind: Literal["graph_started"] = "graph_started"
    graph_id: str = Field(min_length=1)
    graph_spec_hash: str = Field(min_length=1)


class NodeStarted(_AgentEventBase):
    """一个带版本号的节点 invocation 开始。"""

    kind: Literal["node_started"] = "node_started"
    node_id: str = Field(min_length=1)
    invocation_version: int = Field(ge=1)


class NodeFinished(_AgentEventBase):
    """节点 invocation 完成并准备提升 staged deliver。"""

    kind: Literal["node_finished"] = "node_finished"
    node_id: str = Field(min_length=1)
    invocation_version: int = Field(ge=1)
    duration_ms: float = Field(ge=0)


class TextDelta(_AgentEventBase):
    """面向实时消费者发布的回答文本增量。"""

    kind: Literal["text_delta"] = "text_delta"
    delta: str = Field(min_length=1)


class ReasoningDelta(_AgentEventBase):
    """面向获准消费者发布的推理文本增量。"""

    kind: Literal["reasoning_delta"] = "reasoning_delta"
    delta: str = Field(min_length=1)


class ToolCallStarted(_AgentEventBase):
    """工具调用通过 admission 并开始执行。"""

    kind: Literal["tool_call_started"] = "tool_call_started"
    call: ToolCall


class ToolCallFinished(_AgentEventBase):
    """工具调用结束；事件可按完成顺序发布。"""

    kind: Literal["tool_call_finished"] = "tool_call_finished"
    result: ToolResult


class ApprovalRequested(_AgentEventBase):
    """工具批次暂停并等待原子审批判定。"""

    kind: Literal["approval_requested"] = "approval_requested"
    transaction: ApprovalTransaction


class GraphInterrupted(_AgentEventBase):
    """图在显式业务或人工断点处持久化并挂起。"""

    kind: Literal["graph_interrupted"] = "graph_interrupted"
    interrupt_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class TurnFinished(_AgentEventBase):
    """Turn 正常或受控停止时唯一的完成事件。"""

    kind: Literal["turn_finished"] = "turn_finished"
    stop_reason: StopReason
    result: str | None = None


class TurnFailed(_AgentEventBase):
    """Turn 因不可收敛错误终止时唯一的失败事件。"""

    kind: Literal["turn_failed"] = "turn_failed"
    error: ErrorInfo


AgentEvent = Annotated[
    Union[
        GraphStarted,
        NodeStarted,
        NodeFinished,
        TextDelta,
        ReasoningDelta,
        ToolCallStarted,
        ToolCallFinished,
        ApprovalRequested,
        GraphInterrupted,
        TurnFinished,
        TurnFailed,
    ],
    Field(discriminator="kind"),
]
