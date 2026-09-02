UV ?= uv
CORE_SRC := packages/nova-core/src

.PHONY: check sync phase0-check test

check: phase0-check test

sync:
	$(UV) sync --locked

phase0-check:
	$(UV) run --frozen python tools/check_phase0.py

test:
	PYTHONPATH=src:$(CORE_SRC) $(UV) run --frozen python -m unittest discover -s tests -p 'test_*.py' -v
