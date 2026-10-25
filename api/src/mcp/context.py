from typing import Any
from contextvars import ContextVar
from pydantic_ai import RunContext
from pydantic_ai.mcp import ToolResult, CallToolFunc
from src.models.context import ChatContext

current: ContextVar[ChatContext] = ContextVar("mcp_context", default=ChatContext())


async def call_tool(ctx: RunContext[ChatContext], call_next: CallToolFunc, name: str, arguments: dict[str, Any]) -> ToolResult:
    """Make conversation preferences available throughout an MCP tool call."""

    # Restore the caller's context even when a tool fails or is cancelled.
    token = current.set(ctx.deps)
    try:
        return await call_next(name, arguments)
    finally:
        current.reset(token)
