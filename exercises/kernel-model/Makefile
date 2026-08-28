SHELL := /bin/sh
PYTHON ?= python3

.PHONY: test clean

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
