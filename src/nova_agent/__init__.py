"""NovaAgent workspace composition root.

Runtime capabilities are implemented in the independently publishable
packages under ``packages/*/src``. This root package is intentionally small:
it provides the repository-level namespace and version while keeping all
workspace application code under the conventional top-level ``src`` tree.
"""

__version__ = "0.1.0.dev0"

