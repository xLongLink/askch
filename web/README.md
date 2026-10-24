# Swiss Chat

A single-page Svelte 5 / SvelteKit chatbot built with Vite+, Tailwind CSS 4, and shadcn-svelte. OpenUI renders streamed responses as text, cards, charts, and follow-up buttons. All five components from the linked Svelte example are registered: `Stack`, `TextContent`, `Card`, `Button`, and `Chart` (bar, line, pie, and doughnut). There is no history sidebar, database, or browser storage; refreshing clears the conversation.

## Run

```sh
vp install
vp dev
```

Run `make api` from the repository root in another terminal. The Python FastAPI backend owns all API endpoints and credentials in `api/.env`; see [its README](../api/README.md). Vite proxies `/api` to `http://127.0.0.1:8000`. There are no API routes or provider credentials in the web app. OpenUI renders the responses locally; no Thesys key is needed.

Without a global Vite+ installation, use `pnpm install` and `pnpm dev`. Node 24 LTS is recommended.

## Validate

```sh
vp check
vp run check
vp build
```

`vp check` runs formatting and linting. `vp run check` runs Svelte's component-aware TypeScript checker. `vp run <task>` runs package scripts rather than Vite+'s built-in commands.

## Components

```sh
pnpm dlx shadcn-svelte@latest add <component>
```

- `src/routes/+page.svelte`: chat interface, stop/retry, and new-chat reset.
- `../api/src/main.py`: FastAPI application and MCP lifecycle.
- `../api/src/routes/chat.py`: validated streaming endpoint.
- `src/lib/library.ts`: OpenUI component schemas and renderer registration.
- `src/lib/openui/`: OpenUI renderers using shadcn-svelte components.
- `../api/src/prompt.py`: server-owned OpenUI generation instructions.

Adapted from https://github.com/thesysdev/openui/tree/main/examples/app-frameworks/svelte (MIT). The integration keeps the renderer, component library, streaming transport, and follow-up actions, without the example's persisted history or demo tools.

The static adapter prerenders the frontend into `build/`, using absolute asset URLs for deep navigation. The root [Docker setup](../README.md#containers) builds these files and copies them into one Python runtime image. FastAPI's `frontend()` facility serves the assets and provides an HTML-navigation fallback while preserving API/MCP routes; there is no separate frontend server or Nginx service. Vite's proxy remains development-only. Add authentication and rate limiting before exposing the paid API endpoint publicly.
