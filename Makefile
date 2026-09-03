UV ?= uv
CORE_SRC := packages/nova-core/src

.PHONY: check sync phase0-check schema schema-check test lint typecheck coverage package-check

check: phase0-check schema-check test lint typecheck coverage package-check

sync:
	$(UV) sync --locked

phase0-check:
	$(UV) run --frozen python tools/check_phase0.py

schema:
	PYTHONPATH=$(CORE_SRC) $(UV) run --frozen python tools/generate_core_schema.py

schema-check:
	PYTHONPATH=$(CORE_SRC) $(UV) run --frozen python tools/generate_core_schema.py --check

test:
	PYTHONPATH=src:$(CORE_SRC) $(UV) run --frozen python -m unittest discover -s tests -p 'test_*.py' -v

lint:
	$(UV) run --frozen ruff check src $(CORE_SRC) tools tests

typecheck:
	$(UV) run --frozen mypy src $(CORE_SRC) tools tests

coverage:
	PYTHONPATH=src:$(CORE_SRC) $(UV) run --frozen coverage run -m unittest discover -s tests -p 'test_*.py'
	$(UV) run --frozen coverage report

package-check:
	NOVA_UV=$(UV) $(UV) run --frozen python tools/check_core_distribution.py
