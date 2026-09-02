# Phase 0 end-to-end scenario matrix

This matrix defines the twelve scenarios used to review the design baseline.
Each scenario names its fixture, required observable evidence, and the
invariant that later implementation tests must assert. `clean` means no
checkpoint/recovery side effects; `production` enables the full governance and
checkpoint path.

| ID | Scenario and mode | Fixture/input | Required evidence and assertions |
|---|---|---|---|
| E2E-01 | Pure conversation (`clean`) | Scripted model emits text then EOF; no tools. | `RECEIVED → RUNNING → COMPLETED`; text deltas are ordered; exactly one `TurnFinished`; final snapshot contains the answer. |
| E2E-02 | Single safe tool (`production`) | Model requests one idempotent read tool with valid schema. | Policy decision is recorded before `ToolCallStarted`; one structured result is committed; model sees the result; terminal event is unique. |
| E2E-03 | Parallel reads (`production`) | Two independent `PARALLEL` read calls followed by a final answer. | Calls overlap up to configured limit; settle events may differ from model order; history commits by `seq`; `max_parallel=1` matches serial output. |
| E2E-04 | Dangerous write denied (`production`) | DANGEROUS file write without an allow decision or PolicyGateway. | Registration/execution fails closed; no filesystem mutation; non-sensitive denial reason and audit event are present; Turn ends with explainable stop/error. |
| E2E-05 | Approval and resume (`production`) | Sensitive call requires human approval, then receives an allow decision. | `ApprovalRequested` carries stable ID and expiry; GraphInterrupt persists snapshot; resume keeps `turn_id`, `graph_instance_id`, `trace_id`; already completed calls are not repeated. |
| E2E-06 | Cancellation (`production`) | Cancellation arrives while model stream, tool worker or approval is waiting. | New work is not admitted; workers receive cancellation; `on_cancel()` runs for resource-holding tools; one `CANCELLED` terminal event and quiescent graph. |
| E2E-07 | Model error (`production`) | Scripted gateway returns a classified timeout/protocol/content error. | Error maps to `ModelError` with `retryable`; retry budget is bounded; invocation is `CRASHED` or failed explicitly; no hanging Turn or duplicate terminal event. |
| E2E-08 | SQLite restart/recovery (`production`) | Process terminates between tool execution, result commit, and snapshot writes. | Append-only events plus invocation/deliver state reconstruct seeds; idempotency key prevents unsafe duplicate result; recovery preserves identity and reaches quiescence. |
| E2E-09 | Graph branch and join (`production`) | Typed graph condition selects one branch, then two fan-out nodes join on `ON_ALL_PREDS`. | Compile rejects missing/duplicate/unreachable nodes; selected branch and join outputs are deterministic; Linear and Parallel schedulers agree. |
| E2E-10 | ReAct controlled loop (`production`) | Model alternates tool calls and text for several iterations, then reaches a finish line or budget. | Fixed topology is observed; `iteration` and `max_iterations` are persisted; loop/budget stop emits a typed `StopReason`, never an unbounded while loop. |
| E2E-11 | MCP provider (`production`) | MCP tool discovery, invocation and a simulated reconnect. | MCP is an adapter through ToolExecutor; schemas/risk are revalidated after reconnect; disconnect is observable and cannot bypass policy or approval. |
| E2E-12 | Multi-agent and web stream (`production`) | HTTP/SSE client starts a parent graph that delegates a child AgentNode. | Parent/child Turn identities and spans are distinct; events stream in order with correlation IDs; cancellation and terminal semantics propagate without a second scheduler. |

## Review gates

- Every row must eventually have a deterministic fixture, a trace/cassette, and
  at least one executable assertion beyond the model's prose.
- Security rows (E2E-04, E2E-05, E2E-06, E2E-11) must prove no side effect or
  bypass, not merely inspect an emitted log.
- Recovery rows (E2E-05, E2E-08) must assert stable identity and the final
  snapshot, while cancellation/error rows must assert one terminal event.
- The matrix is a design baseline, not a claim that implementation exists yet;
  Phase 1–4 work should link tests back to these IDs.

