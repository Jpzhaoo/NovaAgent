"""Dependency-free structural checks for the Phase 0 design baseline."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

EXPECTED_PACKAGES = {
    "nova-core": "nova_core",
    "nova-graph": "nova_graph",
    "nova-react": "nova_react",
    "nova-runtime": "nova_runtime",
    "nova-storage": "nova_storage",
    "nova-models": "nova_models",
    "nova-policy": "nova_policy",
    "nova-cli": "nova_cli",
    "nova-http": "nova_http",
    "nova-memory": "nova_memory",
    "nova-multi": "nova_multi",
    "nova-mcp": "nova_mcp",
    "nova-scope": "nova_scope",
    "nova-media": "nova_media",
    "nova-terminal": "nova_terminal",
    "nova-external": "nova_external",
}


def _project_field(text: str, field: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(field)}\s*=\s*[\"']([^\"']+)", text)
    return match.group(1) if match else None


def validate(root: Path) -> tuple[dict[str, int], list[str]]:
    errors: list[str] = []
    version_file = root / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.(?:dev|a|b|rc)\d+)?", version):
        errors.append("VERSION must contain a SemVer-compatible development version")

    root_pyproject = root / "pyproject.toml"
    if not root_pyproject.exists():
        errors.append("root pyproject.toml is missing")
    else:
        root_text = root_pyproject.read_text(encoding="utf-8")
        if _project_field(root_text, "version") != version:
            errors.append("root pyproject version does not match VERSION")
        if _project_field(root_text, "requires-python") != ">=3.12":
            errors.append("root pyproject must declare Python >=3.12")

    root_source = root / "src" / "nova_agent" / "__init__.py"
    if not root_source.exists():
        errors.append("root src layout is missing src/nova_agent/__init__.py")

    package_count = 0
    source_lines = 0
    for distribution, import_name in EXPECTED_PACKAGES.items():
        # 根 src 是唯一源码来源；发行目录只用相对链接提供独立构建上下文。
        package_dir = root / "packages" / distribution
        metadata = package_dir / "pyproject.toml"
        source_dir = root / "src" / import_name
        source_link = package_dir / "src" / import_name
        init_file = source_dir / "__init__.py"
        if not metadata.exists():
            errors.append(f"missing metadata: {metadata.relative_to(root)}")
            continue
        package_count += 1
        metadata_text = metadata.read_text(encoding="utf-8")
        if _project_field(metadata_text, "name") != distribution:
            errors.append(f"{distribution} metadata has the wrong project name")
        if _project_field(metadata_text, "version") != version:
            errors.append(f"{distribution} version does not match VERSION")
        if _project_field(metadata_text, "requires-python") != ">=3.12":
            errors.append(f"{distribution} must declare Python >=3.12")
        source_config = f'where = ["src"]\ninclude = ["{import_name}*"]'
        if source_config not in metadata_text:
            errors.append(f"{distribution} must package only src/{import_name}")
        if not source_link.is_symlink() or source_link.resolve() != source_dir.resolve():
            errors.append(
                f"{source_link.relative_to(root)} must link to src/{import_name}"
            )
        if not init_file.exists():
            errors.append(f"missing import root: {init_file.relative_to(root)}")
        else:
            source_lines += sum(
                len(source_file.read_text(encoding="utf-8").splitlines())
                for source_file in source_dir.rglob("*.py")
            )

    required_docs = (
        "CONTRIBUTING.md",
        "docs/GLOSSARY.md",
        "docs/VERSIONING.md",
        "docs/ARCHITECTURE.md",
        "docs/NON-GOALS.md",
        "docs/phase0/scenario-matrix.md",
        "docs/adr/0001-core-boundaries-and-typed-contracts.md",
        "docs/adr/0002-unified-turn-lifecycle-and-graph-runtime.md",
        "docs/adr/0003-centralized-tool-security-and-approval.md",
    )
    for relative_path in required_docs:
        if not (root / relative_path).exists():
            errors.append(f"missing Phase 0 document: {relative_path}")

    matrix = root / "docs/phase0/scenario-matrix.md"
    scenario_ids = set(re.findall(r"\bE2E-\d{2}\b", matrix.read_text(encoding="utf-8"))) if matrix.exists() else set()
    expected_ids = {f"E2E-{index:02d}" for index in range(1, 13)}
    if scenario_ids != expected_ids:
        errors.append(f"scenario matrix must contain exactly E2E-01..E2E-12 (found {sorted(scenario_ids)})")

    forbidden_core_imports = {"nova_graph", "nova_react", "nova_runtime", "nova_storage", "nova_models", "nova_policy"}
    core_src = root / "src/nova_core"
    for source_file in core_src.rglob("*.py"):
        try:
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        except SyntaxError as exc:
            errors.append(f"cannot parse {source_file.relative_to(root)}: {exc}")
            continue
        for node in ast.walk(tree):
            imported = node.names[0].name.split(".")[0] if isinstance(node, ast.Import) and node.names else ""
            if isinstance(node, ast.ImportFrom) and node.module:
                imported = node.module.split(".")[0]
            if imported in forbidden_core_imports:
                errors.append(f"nova-core imports forbidden package {imported}")

    metrics = {"published_packages": package_count, "source_lines": source_lines}
    if package_count != len(EXPECTED_PACKAGES):
        errors.append(f"expected {len(EXPECTED_PACKAGES)} published package skeletons, found {package_count}")
    return metrics, errors


def main() -> int:
    metrics, errors = validate(Path(__file__).resolve().parents[1])
    print(f"phase0: {metrics['published_packages']} package skeletons, {metrics['source_lines']} source lines")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("phase0: structural baseline checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
