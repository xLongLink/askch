.PHONY: web api

web:
	cd web && npm ci && npm run dev

api:
	cd api && uv sync && uv run uvicorn src.main:create_app --factory --reload --host 127.0.0.1 --port 8000
