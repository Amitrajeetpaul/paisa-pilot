.PHONY: dev test lint deploy run-api run-web

VENV := .venv/bin

dev:
	python3 -m venv .venv
	$(VENV)/pip install --quiet -r requirements-dev.txt
	cd web && npm install

test:
	$(VENV)/python -m pytest rules_engine/ llm/ api/ agents/ -q
	$(VENV)/python -m mypy rules_engine llm api agents
	cd web && npx tsc -b && npm run build

lint:
	$(VENV)/python -m mypy rules_engine llm api agents
	cd web && npm run lint

run-api:
	$(VENV)/python -m uvicorn api.main:app --reload --port 8000

run-web:
	cd web && npm run dev

deploy:
	@echo "See infra/deploy.md -- requires an explicit go-ahead and a real GCP project; not something 'make deploy' runs unattended."
