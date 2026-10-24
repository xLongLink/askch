.PHONY: web api

web:
	cd web && npm ci && npm run dev

api:
	cd api && uv sync && uv run python main.py
