PYTHON ?= python3

.PHONY: install test unit e2e run-local compile

install:
	$(PYTHON) -m pip install -r requirements.txt

unit:
	PYTHONPATH=. pytest -q

e2e:
	PYTHONPATH=. $(PYTHON) scripts/e2e_smoke.py

test: unit e2e

run-local:
	PYTHONPATH=. $(PYTHON) scripts/run_local.py --provider-mode $${PROVIDER_MODE:-fake}

compile:
	$(PYTHON) -m compileall -q shared services scripts tests
