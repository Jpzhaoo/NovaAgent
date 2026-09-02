"""生成或校验 Phase 1 的 nova-core JSON Schema catalog。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nova_core.schema import build_core_schema_catalog

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "phase1" / "core-schemas.json"


def render_catalog() -> str:
    """使用稳定 key 顺序和统一缩进渲染 catalog。"""

    return json.dumps(build_core_schema_catalog(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    """写入 schema；``--check`` 模式只比较，不修改工作区。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验已提交 catalog")
    args = parser.parse_args()
    rendered = render_catalog()

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("core schema catalog is stale; run `make schema`")
            return 1
        print(f"core schema catalog is current: {OUTPUT.relative_to(ROOT)}")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
