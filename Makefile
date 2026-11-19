.PHONY: dev test lint deploy

VENV := .venv/bin

dev:
	python3 -m venv .venv
	$(VENV)/pip install --quiet -r requirements-dev.txt

test:
	$(VENV)/python -m pytest rules_engine/ llm/ -q
	$(VENV)/python -m mypy rules_engine llm

lint: test

deploy:
	@echo "See infra/deploy.md -- not wired up until Milestone 4."
