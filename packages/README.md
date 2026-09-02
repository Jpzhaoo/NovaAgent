# Package layout

Each directory below is an independently buildable distribution. Runtime
dependencies must point downward toward `nova-core`; `examples` is not a
published package.

The repository composition namespace lives in the top-level `src/nova_agent/`.
Implementation code for a published capability stays in that capability's own
`packages/<distribution>/src/<import_name>/` tree so package builds remain
isolated and independently releasable.
