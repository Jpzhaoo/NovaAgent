# Package layout

Each directory below is an independently buildable distribution. Runtime
dependencies must point downward toward `nova-core`; `examples` is not a
published package.

This directory contains distribution metadata only. All implementation code
lives in the repository-level `src/<import_name>/` tree. Each distribution has
a relative symlink at `packages/<distribution>/src/<import_name>` pointing to
that single source of truth, and its `pyproject.toml` includes only the matching
import package. Wheels and source distributions therefore remain isolated and
independently releasable without duplicating implementation files.
