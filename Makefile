UV ?= uv

.PHONY: check sync phase0-check test

check: phase0-check test

sync:
	$(UV) sync --locked

phase0-check:
	$(UV) run --frozen python tools/check_phase0.py

test:
	$(UV) run --frozen python -m unittest discover -s tests -p 'test_*.py' -v
