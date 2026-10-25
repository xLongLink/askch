import httpx2
from functools import wraps
from collections.abc import Callable, Awaitable
from mcp.server.mcpserver.exceptions import ToolError


def boundary[**P, R](tool: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Translate common upstream failures into safe MCP tool errors."""

    @wraps(tool)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        """Preserve the tool's signature and explicit domain errors."""

        # Handle upstream failures consistently without exposing response details.
        try:
            return await tool(*args, **kwargs)
        except (TimeoutError, httpx2.TimeoutException):
            raise ToolError("The data lookup timed out.") from None
        except httpx2.HTTPError:
            raise ToolError("The requested data could not be fetched.") from None
        except ValueError:
            raise ToolError("The data source returned an invalid response.") from None

    return wrapped
