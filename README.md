# NovaAgent

NovaAgent is a graph-driven ReAct agent framework for Python 3.12+.

The repository is a package-oriented monorepo. Phase 0 established the package
boundaries; Phase 1 now provides the typed `nova-core` contracts, ports,
InMemory fakes and schema catalog. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the development workflow and [the server manual](docs/phase1/server-manual-test.md)
for an end-to-end acceptance run.

The repository-level namespace uses the top-level `src/nova_agent/` layout;
published capability packages keep their implementation in their own
`packages/*/src/` trees.

```text
uv sync --locked
make check
```
