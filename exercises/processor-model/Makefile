SHELL := /bin/sh
PYTHON ?= python3

.PHONY: test check demo install clean

test:
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check:
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m compileall -q processor_model tests processor-model.py
	@$(PYTHON) processor-model.py --help >/dev/null
	@$(MAKE) test

install:
	@$(PYTHON) -m pip install .

demo:
	@$(PYTHON) processor-model.py bits add 127 1 --width 8
	@$(PYTHON) processor-model.py isa fixtures/programs/sum.asm --max-steps 100
	@$(PYTHON) processor-model.py pipeline fixtures/traces/pipeline-load-use.trace --forwarding full
	@$(PYTHON) processor-model.py cache fixtures/traces/cache.trace --size 16 --block 4 --ways 1
	@$(PYTHON) processor-model.py vm fixtures/vm/config.json fixtures/vm/trace.txt
	@$(PYTHON) processor-model.py coherence \
		fixtures/traces/coherence-false-sharing.trace \
		--cores 2 --line-size 64

clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type f -name '*.py[co]' -delete
	@rm -rf build dist *.egg-info .pytest_cache
