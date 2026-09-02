# Explicit non-goals

These items are intentionally outside the Phase 0/1 core boundary. They may be
provided later as capability packages or adapters, but their absence must not
block the graph and ReAct contracts.

- A built-in WebUI, IM connector, MCP server, terminal, vector database or
  business memory policy in `nova-core`.
- Arbitrary runtime-generated workflows, hot reload, or cross-process
  distributed graph scheduling in v1.
- A universal provider-specific reasoning replay, file API or multimodal
  representation; only protocol extension points are guaranteed.
- Business-specific strategies such as todo, experience, dream, industry
  knowledge or domain workflows in the framework core.
- Compatibility shims that copy another framework's public API.
- Exactly-once side effects across external systems. Tool execution is
  explicitly at-least-once and requires idempotency handling.
- Treating an Agent's natural-language claim as a world-state oracle in
  evaluation.

Adding a capability requires a port or a separate package, an owner, tests, and
an ADR when it changes a core boundary or lifecycle invariant.

