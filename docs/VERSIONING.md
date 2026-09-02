# Versioning and release policy

NovaAgent follows SemVer (`MAJOR.MINOR.PATCH`) with an explicit pre-release
identifier while the project is below 1.0. The version currently being built is
`0.1.0.dev0`, recorded in the repository-level [`VERSION`](../VERSION) file.

## Package versions

- Every published package has its own `version` field in `packages/*/pyproject.toml`.
- During the 0.x development line, package versions move together so the
  monorepo can be tested as one compatibility set.
- A package may become independently versioned after 1.0 only when its public
  ports and schema compatibility policy are documented.
- `nova-core` changes are treated as compatibility-sensitive: downstream
  packages must update their pinned range in the same change.

## Compatibility rules

- `0.MINOR.PATCH`: a new minor may include breaking API changes, but each
  breaking change requires a migration note and an ADR when it crosses a
  package boundary.
- Patch releases contain bug fixes, documentation, and backwards-compatible
  schema additions only.
- Pre-releases use `.devN`, `aN`, `bN`, or `rcN`; pre-release artifacts are not
  promoted to stable without a changelog and a clean required CI run.
- Snapshot, event, and cassette schema changes must include a version and a
  round-trip/migration fixture before release.

## Release checklist

1. Update `VERSION` and every package `pyproject.toml` consistently.
2. Add a dated entry to `CHANGELOG.md` describing migrations and compatibility.
3. Run `make check` on Python 3.12 and 3.13 (including the locked dependency
   set once the lockfile exists).
4. Build wheels and source distributions, generate the SBOM and API schema,
   and attach the cassette compatibility report.
5. Create an annotated Git tag named `v<version>` and publish all selected
   package artifacts from that tag.

The `dev` branch may contain pre-release work. Release tags are immutable;
corrections require a new patch or pre-release version rather than rewriting a
published tag.

