"""构建并离线安装 nova-core wheel，验证独立发布边界。"""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PACKAGE_FILES = {
    "nova_core/__init__.py",
    "nova_core/errors.py",
    "nova_core/events.py",
    "nova_core/fakes.py",
    "nova_core/ports.py",
    "nova_core/py.typed",
    "nova_core/schema.py",
    "nova_core/types.py",
}


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    """执行验收子命令，并在失败时保留原始输出和退出码。"""

    subprocess.run(command, cwd=cwd, check=True)


def inspect_wheel(wheel: Path) -> None:
    """确认 wheel 包含 typed Core，且没有引入上层能力包依赖。"""

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = EXPECTED_PACKAGE_FILES - names
        if missing:
            raise RuntimeError(f"nova-core wheel 缺少文件：{sorted(missing)}")

        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise RuntimeError("nova-core wheel 必须且只能包含一份 METADATA")
        metadata = archive.read(metadata_names[0]).decode("utf-8")
        dependencies = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
        if dependencies != ["Requires-Dist: pydantic<3,>=2.7"]:
            raise RuntimeError(f"nova-core wheel 依赖边界异常：{dependencies}")


def isolated_import_probe(python: Path, installed_site: Path) -> None:
    """禁用自动 site 与 socket，验证 wheel 本体不从源码树导入。"""

    probe = """
import socket
import sys
from pathlib import Path

installed_site = Path(sys.argv[1]).resolve()
locked_dependencies = Path(sys.argv[2]).resolve()
sys.path[:0] = [str(installed_site), str(locked_dependencies)]

class NetworkForbidden:
    def __init__(self, *args, **kwargs):
        raise AssertionError("nova-core import/schema generation attempted network access")

socket.socket = NetworkForbidden
import nova_core
from nova_core.schema import build_core_schema_catalog

catalog = build_core_schema_catalog()
assert nova_core.__version__ == "0.1.0.dev0"
assert Path(nova_core.__file__).resolve().is_relative_to(installed_site)
assert catalog["catalog"] == "nova-core"
assert "ModelRequest" in catalog["models"]
assert "AgentEvent" in catalog["unions"]
print(f"isolated nova-core import passed: {nova_core.__file__}")
"""
    locked_dependencies = Path(sysconfig.get_path("purelib")).resolve()
    run(
        [
            str(python),
            "-S",
            "-c",
            probe,
            str(installed_site),
            str(locked_dependencies),
        ]
    )


def main() -> int:
    """使用 uv 缓存完成离线构建、安装和 isolated import。"""

    uv = os.environ.get("NOVA_UV", "uv")
    with tempfile.TemporaryDirectory(prefix="nova-core-dist-") as temporary:
        temporary_path = Path(temporary)
        dist_dir = temporary_path / "dist"
        environment_dir = temporary_path / "venv"

        run(
            [
                uv,
                "build",
                "--offline",
                "--package",
                "nova-core",
                "--wheel",
                "--out-dir",
                str(dist_dir),
            ]
        )
        wheels = tuple(dist_dir.glob("nova_core-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"预期生成一个 nova-core wheel，实际为：{wheels}")
        wheel = wheels[0]
        inspect_wheel(wheel)

        run([uv, "venv", "--python", sys.executable, str(environment_dir)])
        python = environment_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(
            [
                uv,
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--python",
                str(python),
                str(wheel),
            ]
        )
        if os.name == "nt":
            installed_site = environment_dir / "Lib" / "site-packages"
        else:
            version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            installed_site = environment_dir / "lib" / version / "site-packages"
        isolated_import_probe(python, installed_site)

    print("nova-core distribution check passed (offline build/install/import)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
