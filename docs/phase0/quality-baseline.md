# Phase 0 quality baseline

The baseline is intentionally dependency-light so a fresh checkout can run
`make check` before any package is installed. The structural checker validates
package metadata, version consistency, required design documents, the twelve
scenario IDs, Python importability roots, and the Core dependency direction.

## Initial measurements (2026-09-02)

| Measure | Baseline | Phase 0 gate |
|---|---:|---|
| Published package skeletons | 16 | exactly the PRD 5.1 list |
| Core Python source lines | 4 | below the Phase 1 limit of 5,000 |
| Repository Python source lines (including checks/tests) | 228 | informational; grows with implementation |
| Structural checks | pass | `python3 tools/check_phase0.py` |
| Unit checks | 1 test, pass | `python3 -m unittest discover -s tests` |
| Product coverage | not yet meaningful | coverage gate starts with Phase 1 behavior |
| Supported interpreters | Python 3.12, 3.13 | required CI matrix |

The development tool versions are pinned in `requirements-dev.txt`. A complete
transitive lockfile and SBOM become release gates once runtime dependencies are
introduced; Phase 0 does not pretend the empty skeleton has production
coverage.

## Required CI checks

The workflow runs the structural and unit checks on both supported Python
versions, then runs Ruff, mypy and coverage as explicit quality signals. A
future phase may raise coverage/type thresholds, but no check may be hidden by
`continue-on-error`.
