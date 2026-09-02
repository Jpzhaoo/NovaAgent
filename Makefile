UV ?= uv
CORE_SRC := packages/nova-core/src

.PHONY: check sync phase0-check schema schema-check test

check: phase0-check schema-check test

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
