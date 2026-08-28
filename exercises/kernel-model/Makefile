SHELL := /bin/sh
PYTHON ?= python3

.PHONY: test smoke check clean

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

smoke:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) kernel-model.py lifecycle examples/lifecycle.json >/dev/null

check:
	$(PYTHON) -m compileall -q kernel_model kernel-model.py tests
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) kernel-model.py lifecycle examples/lifecycle.json >/dev/null
	$(MAKE) clean

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
