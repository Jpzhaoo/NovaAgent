"""NovaAgent 的异常控制流与可序列化错误信息映射。"""

from __future__ import annotations

from pydantic import JsonValue

from .types import (
    Correlation,
    ErrorCategory,
    ErrorInfo,
    ModelErrorInfo,
    PolicyDecision,
    PolicyOutcome,
    ToolCall,
)


class NovaAgentError(Exception):
    """所有框架异常的基类，对外信息统一保存在 ``info``。"""

    def __init__(self, info: ErrorInfo) -> None:
        self.info = info
        super().__init__(info.message)


class ContractViolationError(NovaAgentError):
    """调用方违反 Core 契约时产生的不可重试错误。"""

    def __init__(self, code: str, message: str, correlation: Correlation | None = None) -> None:
        super().__init__(
            ErrorInfo(
                category=ErrorCategory.CONTRACT,
                code=code,
                message=message,
                correlation=correlation,
            )
        )


class ModelGatewayError(NovaAgentError):
    """模型适配器归一化认证、限流、超时和协议错误后的异常。"""

    def __init__(
        self,
        model_error: ModelErrorInfo,
        correlation: Correlation | None = None,
    ) -> None:
        details: dict[str, JsonValue] = {"kind": model_error.kind.value}
        if model_error.provider_code is not None:
            details["provider_code"] = model_error.provider_code
        super().__init__(
            ErrorInfo(
                category=ErrorCategory.MODEL,
                code=f"model.{model_error.kind.value.lower()}",
                message=model_error.message,
                retryable=model_error.retryable,
                correlation=correlation,
                details=details,
            )
        )


class ToolExecutionError(NovaAgentError):
    """工具执行失败，并保留调用身份以支持有序结果和审计。"""

    def __init__(
        self,
        call: ToolCall,
        message: str,
        *,
        retryable: bool = False,
        correlation: Correlation | None = None,
    ) -> None:
        super().__init__(
            ErrorInfo(
                category=ErrorCategory.TOOL,
                code="tool.execution_failed",
                message=message,
                retryable=retryable,
                correlation=correlation,
                details={"call_id": call.call_id, "name": call.name},
            )
        )


class PolicyDeniedError(NovaAgentError):
    """策略明确拒绝工具调用时产生的不可重试异常。"""

    def __init__(
        self,
        call: ToolCall,
        decision: PolicyDecision,
        correlation: Correlation | None = None,
    ) -> None:
        if decision.outcome is not PolicyOutcome.DENY:
            raise ValueError("PolicyDeniedError requires a DENY decision")
        super().__init__(
            ErrorInfo(
                category=ErrorCategory.POLICY,
                code="policy.denied",
                message="; ".join(decision.reasons),
                correlation=correlation,
                details={"call_id": call.call_id, "name": call.name},
            )
        )


class PersistenceError(NovaAgentError):
    """存储适配器无法完成读写或事务操作时的异常。"""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        correlation: Correlation | None = None,
    ) -> None:
        super().__init__(
            ErrorInfo(
                category=ErrorCategory.STORAGE,
                code="storage.operation_failed",
                message=message,
                retryable=retryable,
                correlation=correlation,
            )
        )


class ConcurrencyConflictError(NovaAgentError):
    """compare-and-swap 或序列追加发生版本冲突时的可重试异常。"""

    def __init__(self, resource_id: str, expected_version: int, actual_version: int) -> None:
        super().__init__(
            ErrorInfo(
                category=ErrorCategory.STORAGE,
                code="storage.concurrency_conflict",
                message=f"version conflict for {resource_id}",
                retryable=True,
                details={
                    "resource_id": resource_id,
                    "expected_version": expected_version,
                    "actual_version": actual_version,
                },
            )
        )
