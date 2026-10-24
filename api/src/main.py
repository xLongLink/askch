from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from .mcp import create_server
from .models.settings import Settings
from .routes.chat import router as chat_router
from .routes.health import router as health_router


def frontend_request(request: Request):
    if request.url.path == "/api" or request.url.path.startswith("/api/"):
        raise HTTPException(status_code=404)


def create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
    settings = settings or Settings()
    mcp = create_server()
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with (
            httpx.AsyncClient(
                base_url=f"https://api.infomaniak.com/2/ai/{settings.infomaniak_product_id}/openai/v1/",
                headers={
                    "Authorization": f"Bearer {settings.infomaniak_api_key.get_secret_value()}"
                },
                timeout=httpx.Timeout(60, connect=10),
                transport=transport,
            ) as client,
            mcp.session_manager.run(),
        ):
            app.state.client = client
            yield

    app = FastAPI(title="Swiss API", lifespan=lifespan)
    app.state.settings = settings
    app.mount("/api/mcp", mcp_app)
    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    if settings.frontend_dir is not None:
        frontend = APIRouter(dependencies=[Depends(frontend_request)])
        frontend.frontend(
            "/", directory=settings.frontend_dir, fallback="index.html", check_dir=True
        )
        app.include_router(frontend)
    return app
