# NovaAgent

NovaAgent is a graph-driven ReAct agent framework for Python 3.12+.

The repository keeps independently buildable distribution metadata under
`packages/`, while all importable Python code lives directly under the single
top-level `src/` tree. Phase 1 provides the typed `nova-core` contracts, ports,
InMemory fakes and schema catalog. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the development workflow and [the server manual](docs/phase1/server-manual-test.md)
for an end-to-end acceptance run.

The repository namespace is `src/nova_agent/`; capability imports such as
`nova_core`, `nova_graph` and `nova_runtime` are sibling directories in the
same source root. Each `packages/nova-*` manifest explicitly selects only its
matching import package through a relative source link when building a
distribution; the implementation remains owned by the top-level `src/` tree.

```text
uv sync --locked
make check
```
