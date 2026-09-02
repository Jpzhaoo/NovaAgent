.PHONY: check phase0-check test

check: phase0-check test

phase0-check:
	python3 tools/check_phase0.py

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

