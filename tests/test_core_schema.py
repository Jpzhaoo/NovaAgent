"""公开 Core 类型与 schema catalog 注册表的一致性测试。"""

import inspect
import unittest
from enum import Enum

import nova_core
from pydantic import BaseModel

from nova_core.schema import (
    CORE_ENUM_TYPES,
    CORE_MODEL_TYPES,
    CORE_UNION_TYPES,
    build_core_schema_catalog,
)


class CoreSchemaTests(unittest.TestCase):
    """阻止公共类型在没有 schema 文档的情况下进入发布包。"""

    def test_every_exported_model_and_enum_is_registered(self) -> None:
        exported_models: set[str] = set()
        exported_enums: set[str] = set()
        for name in nova_core.__all__:
            candidate = getattr(nova_core, name)
            if inspect.isclass(candidate) and issubclass(candidate, BaseModel):
                exported_models.add(name)
            if inspect.isclass(candidate) and issubclass(candidate, Enum):
                exported_enums.add(name)

        self.assertEqual(exported_models, {model.__name__ for model in CORE_MODEL_TYPES})
        self.assertEqual(exported_enums, {enum_type.__name__ for enum_type in CORE_ENUM_TYPES})

    def test_catalog_contains_all_models_enums_and_unions(self) -> None:
        catalog = build_core_schema_catalog()
        self.assertEqual({model.__name__ for model in CORE_MODEL_TYPES}, set(catalog["models"]))
        self.assertEqual({enum_type.__name__ for enum_type in CORE_ENUM_TYPES}, set(catalog["enums"]))
        self.assertEqual(set(CORE_UNION_TYPES), set(catalog["unions"]))
        for union_schema in catalog["unions"].values():
            self.assertIn("discriminator", union_schema)


if __name__ == "__main__":
    unittest.main()
