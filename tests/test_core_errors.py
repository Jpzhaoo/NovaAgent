"""Core 错误族对稳定 ErrorInfo 的映射测试。"""

import unittest

from nova_core import (
    ConcurrencyConflictError,
    ContractViolationError,
    ErrorCategory,
    ModelErrorInfo,
    ModelErrorKind,
    ModelGatewayError,
    PersistenceError,
    PolicyDecision,
    PolicyDeniedError,
    PolicyOutcome,
    ToolCall,
    ToolExecutionError,
)


class CoreErrorTests(unittest.TestCase):
    """验证异常控制流不会丢失机器可读的诊断字段。"""

    def setUp(self) -> None:
        self.call = ToolCall(
            call_id="call-1",
            name="write_file",
            arguments={"path": "result.txt"},
            seq=0,
            idempotency_key="turn-1:call-1",
        )

    def test_contract_and_model_errors_keep_stable_codes(self) -> None:
        contract_error = ContractViolationError("message.invalid", "消息不合法")
        self.assertEqual(ErrorCategory.CONTRACT, contract_error.info.category)
        self.assertFalse(contract_error.info.retryable)
        self.assertEqual("消息不合法", str(contract_error))

        model_error = ModelGatewayError(
            ModelErrorInfo(
                kind=ModelErrorKind.RATE_LIMIT,
                message="请求过多",
                retryable=True,
                provider_code="429",
            )
        )
        self.assertEqual("model.rate_limit", model_error.info.code)
        self.assertTrue(model_error.info.retryable)
        self.assertEqual("429", model_error.info.details["provider_code"])

    def test_tool_and_policy_errors_keep_call_identity(self) -> None:
        tool_error = ToolExecutionError(self.call, "写入失败", retryable=False)
        self.assertEqual("call-1", tool_error.info.details["call_id"])

        decision = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("路径越界",))
        policy_error = PolicyDeniedError(self.call, decision)
        self.assertEqual(ErrorCategory.POLICY, policy_error.info.category)
        self.assertEqual("路径越界", policy_error.info.message)

        with self.assertRaises(ValueError):
            PolicyDeniedError(
                self.call,
                PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("安全",)),
            )

    def test_persistence_errors_expose_retryability_and_versions(self) -> None:
        transient = PersistenceError("数据库忙", retryable=True)
        self.assertTrue(transient.info.retryable)

        conflict = ConcurrencyConflictError("turn-1", expected_version=2, actual_version=3)
        self.assertEqual("storage.concurrency_conflict", conflict.info.code)
        self.assertEqual(2, conflict.info.details["expected_version"])
        self.assertEqual(conflict.info, type(conflict.info).model_validate_json(conflict.info.model_dump_json()))


if __name__ == "__main__":
    unittest.main()
