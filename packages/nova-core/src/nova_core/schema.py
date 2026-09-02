"""公开 Core 类型的 JSON Schema catalog 构建入口。"""

from __future__ import annotations

from enum import Enum
from types import ModuleType
from typing import Any

from pydantic import BaseModel, TypeAdapter

from . import events as events_module
from . import types as types_module
from .events import AgentEvent, ModelEvent
from .types import ContentPart


def _discover_models(module: ModuleType) -> tuple[type[BaseModel], ...]:
    """只发现由目标模块直接声明的公开 Pydantic 模型。"""

    discovered: list[type[BaseModel]] = []
    for name in dir(module):
        candidate = getattr(module, name)
        if (
            not name.startswith("_")
            and isinstance(candidate, type)
            and issubclass(candidate, BaseModel)
            and candidate.__module__ == module.__name__
        ):
            discovered.append(candidate)
    return tuple(sorted(discovered, key=lambda model: model.__name__))


def _discover_enums(module: ModuleType) -> tuple[type[Enum], ...]:
    """只发现由目标模块直接声明的公开枚举。"""

    discovered: list[type[Enum]] = []
    for name in dir(module):
        candidate = getattr(module, name)
        if (
            not name.startswith("_")
            and isinstance(candidate, type)
            and issubclass(candidate, Enum)
            and candidate.__module__ == module.__name__
        ):
            discovered.append(candidate)
    return tuple(sorted(discovered, key=lambda enum_type: enum_type.__name__))


CORE_MODEL_TYPES = _discover_models(types_module) + _discover_models(events_module)
CORE_ENUM_TYPES = _discover_enums(types_module) + _discover_enums(events_module)
CORE_UNION_TYPES: dict[str, Any] = {
    "AgentEvent": AgentEvent,
    "ContentPart": ContentPart,
    "ModelEvent": ModelEvent,
}


def build_core_schema_catalog() -> dict[str, Any]:
    """生成稳定排序的模型、枚举与判别联合 JSON Schema catalog。"""

    return {
        "catalog": "nova-core",
        "schema_version": 1,
        "models": {
            model.__name__: model.model_json_schema() for model in CORE_MODEL_TYPES
        },
        "enums": {
            enum_type.__name__: TypeAdapter(enum_type).json_schema()
            for enum_type in CORE_ENUM_TYPES
        },
        "unions": {
            name: TypeAdapter(annotation).json_schema()
            for name, annotation in sorted(CORE_UNION_TYPES.items())
        },
    }
