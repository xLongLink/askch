import httpx2
import uvicorn
from fastapi import Depends, FastAPI, Request, APIRouter, HTTPException
from pathlib import Path
from contextlib import asynccontextmanager
from src.routes import router
from src.settings import settings
from src.mcp.server import server


def frontend_request(request: Request):
    """Exclude API paths from frontend fallback responses."""
    # Keep unknown API paths out of the frontend fallback.
    if request.url.path == "/api" or request.url.path.startswith("/api/"):
        raise HTTPException(status_code=404)


# Configure the API and its internal MCP endpoint.
mcp_app = server.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage provider connections and MCP sessions for the application."""
    # Open and close provider connections and MCP together.
    client = httpx2.AsyncClient(
        base_url=f"https://api.infomaniak.com/2/ai/{settings.INFOMANIAK_PRODUCT_ID}/openai/v1/",
        headers={"Authorization": f"Bearer {settings.INFOMANIAK_API_KEY.get_secret_value()}"},
        timeout=httpx2.Timeout(60, connect=10),
    )
    async with client, server.session_manager.run():
        app.state.client = client
        yield


# Register application routes before the optional frontend.
app = FastAPI(title="Swiss API", lifespan=lifespan)
app.mount("/api/mcp", mcp_app)
app.include_router(router, prefix="/api")

# Serve the bundled frontend when present, leaving API-only development available.
frontend_path = Path(__file__).resolve().parent / "web"
if frontend_path.is_dir():
    frontend = APIRouter(dependencies=[Depends(frontend_request)])
    frontend.frontend("/", directory=frontend_path, fallback="index.html", check_dir=True)
    app.include_router(frontend)

# Start the development server when invoked directly.
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
