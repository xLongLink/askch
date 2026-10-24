# Swiss API

FastAPI backend for the Swiss chatbot. Calls Infomaniak and streams OpenUI Lang using the AI SDK UI-message SSE protocol, compatible with `@ai-sdk/svelte` in `web/`.

## Development

Install [uv](https://docs.astral.sh/uv/), then from the repository root:

```sh
cp api/.env.example api/.env
# Set INFOMANIAK_API_KEY in api/.env
make api
```

Existing credentials have been moved from `web/.env` to `api/.env`. Do not overwrite that file if already configured. It is ignored by Git. Keys are loaded only by the Python backend.

In another terminal, run `make web`. Vite forwards `/api/*` to `http://127.0.0.1:8000` during development. No CORS configuration is needed with this same-origin proxy.

- `POST /api/chat`: accepts AI SDK messages containing text parts, streams responses.
- `GET /api/health`: health check.
- `/api/mcp/`: mounted MCP Streamable HTTP endpoint, exposing `search(website)` to fetch readable text from a public website URL. It is not a search engine.
- `GET /docs`: interactive API documentation.

`INFOMANIAK_PRODUCT_ID` defaults to `112804`; `INFOMANIAK_MODEL` defaults to `swiss-ai/Apertus-v1.5-70B`. Run commands from `api/` so settings load its `.env` file; production can also supply environment variables directly. The OpenUI generation instructions live in `src/prompt.py`, matching the five renderers registered in `web/src/lib/library.ts`.

## Structure

```text
api/
├── src/
│   ├── main.py
│   ├── prompt.py
│   ├── models/
│   │   ├── chat.py
│   │   └── settings.py
│   ├── routes/
│   │   ├── chat.py
│   │   └── health.py
│   └── mcp/
│       ├── server.py
│       └── website.py
├── tests/
└── pyproject.toml
```

`swiss-api` is the only installable project, with `src` as its Python package. MCP is an internal subpackage (`src.mcp`), keeping it distinct from the official SDK's top-level `mcp` package.

## Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Production

```sh
uv sync --no-dev --locked
uv run uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8000
```

The root [Docker setup](../README.md#containers) builds the Svelte frontend and serves it directly through this FastAPI process using `frontend()`. No separate frontend service is needed. Outside Docker, set `FRONTEND_DIR` to the absolute path of a built `web/build` directory to enable the same behavior; leave it unset for API-only development. An explicitly configured build must contain `index.html` or startup fails. API and MCP routes take priority over frontend files, and `/api/*` errors never fall back to HTML. Browser navigation requests accept HTML and can fall back to `index.html`; missing non-navigation requests return 404.

Keep credentials in the backend environment, add authentication and rate limits before public deployment, and ensure any external TLS proxy sends all application requests to Uvicorn without buffering SSE responses. No conversations are persisted by this service; Infomaniak's retention policy still applies.

The MCP endpoint is mounted in the same process and its lifecycle is managed by FastAPI. It is not yet called automatically by the chat endpoint.
