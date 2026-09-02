# NovaAgent

NovaAgent is a graph-driven ReAct agent framework for Python 3.12+.

The repository is a package-oriented monorepo. Phase 0 establishes the package
boundaries and quality baseline; implementation work is tracked from Phase 1
onward. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

The repository-level namespace uses the top-level `src/nova_agent/` layout;
published capability packages keep their implementation in their own
`packages/*/src/` trees.
