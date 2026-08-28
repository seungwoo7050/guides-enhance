PYTHON ?= python3

.PHONY: all check test clean

all: test

check:
	$(PYTHON) -m py_compile manifest_check.py tests/test_manifest_check.py

test: check
	$(PYTHON) tests/test_manifest_check.py ./manifest_check.py

clean:
	rm -rf __pycache__ tests/__pycache__
