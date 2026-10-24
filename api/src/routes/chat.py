import anyio
from uuid import uuid4
from typing import Annotated
from fastapi import Depends, Request, APIRouter
from contextlib import AsyncExitStack, aclosing
from pydantic_ai import Agent, exceptions
from src.settings import settings
from pydantic_ai.ui import NativeEvent
from src.mcp.server import server
from collections.abc import AsyncIterator, AsyncGenerator
from pydantic_ai.mcp import MCPToolset
from src.models.chat import ChatRequest
from src.utils.traces import ChatTrace
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic_ai.ui.vercel_ai import VercelAIAdapter, request_types, response_types
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

router = APIRouter()
ERROR_MESSAGE = "Unable to get a response. Check your API key and model, then try again."


async def stream_resources() -> AsyncGenerator[AsyncExitStack]:
    """Keep agent streams alive through the response and close them on disconnect."""
    resources = AsyncExitStack()
    try:
        yield resources
    finally:
        with anyio.CancelScope(shield=True):
            await resources.aclose()


async def stream_response(
    adapter: VercelAIAdapter[None, str],
    native: AsyncIterator[NativeEvent],
    first: NativeEvent | Exception,
    resources: AsyncExitStack,
    trace: ChatTrace,
) -> AsyncGenerator[str]:
    """Encode agent events while sanitizing failures and closing cancelled runs."""

    async def events() -> AsyncGenerator[NativeEvent]:
        # Replay the event fetched before the HTTP response starts.
        if isinstance(first, Exception):
            raise first
        yield first
        async for event in native:
            yield event

    # Close every generator so disconnects also cancel the agent's provider request.
    encoder = adapter.build_event_stream()
    replay = await resources.enter_async_context(aclosing(events()))
    chunks = adapter.transform_stream(replay)
    if isinstance(chunks, AsyncGenerator):
        await resources.enter_async_context(aclosing(chunks))
    async for chunk in chunks:
        # Send tool traces as transient data, keeping them out of conversation history.
        if isinstance(chunk, response_types.ToolInputAvailableChunk):
            trace.record("tool call", {"toolCallId": chunk.tool_call_id, "toolName": chunk.tool_name, "input": chunk.input})
            yield encoder.encode_event(
                response_types.DataChunk(
                    type="data-tool-call",
                    data={"toolCallId": chunk.tool_call_id, "toolName": chunk.tool_name, "input": chunk.input},
                    transient=True,
                )
            )
        elif isinstance(chunk, response_types.ToolOutputAvailableChunk):
            trace.record("tool result", {"toolCallId": chunk.tool_call_id, "output": chunk.output})
            trace.record("thinking", "Waiting for the model to continue.")
            yield encoder.encode_event(
                response_types.DataChunk(
                    type="data-tool-result", data={"toolCallId": chunk.tool_call_id, "output": chunk.output}, transient=True
                )
            )
        elif isinstance(chunk, (response_types.ToolInputErrorChunk, response_types.ToolOutputErrorChunk)):
            trace.record("error", {"toolCallId": chunk.tool_call_id, "error": "Tool call failed or its arguments were rejected."})
            yield encoder.encode_event(
                response_types.DataChunk(
                    type="data-tool-error",
                    data={"toolCallId": chunk.tool_call_id, "error": "Tool call failed or its arguments were rejected."},
                    transient=True,
                )
            )
        if chunk.type.startswith("tool-"):
            continue
        if isinstance(chunk, response_types.TextDeltaChunk):
            trace.record("model output", chunk.delta)
        if isinstance(chunk, response_types.ErrorChunk):
            trace.status = "error"
            trace.record("error", ERROR_MESSAGE)
            yield encoder.encode_event(response_types.ErrorChunk(error_text=ERROR_MESSAGE))
            yield encoder.encode_event(response_types.DoneChunk())
            return
        yield encoder.encode_event(chunk)
    trace.status = "completed"


@router.post("/chat", response_model=None)
async def chat(
    body: ChatRequest, request: Request, resources: Annotated[AsyncExitStack, Depends(stream_resources)]
) -> JSONResponse | StreamingResponse:
    """Stream the chat agent's text using the existing validated request boundary."""

    # Save the trace after stream resources close, including errors and interrupted requests.
    trace = ChatTrace(model=settings.INFOMANIAK_MODEL)
    for message in body.messages:
        trace.record("user message" if message.role == "user" else "assistant message", message.text)
    resources.push_async_callback(anyio.to_thread.run_sync, trace.save, settings.CHATS_DIR)

    # Keep missing credentials separate from upstream provider errors.
    if not settings.INFOMANIAK_API_KEY.get_secret_value():
        trace.status = "error"
        trace.record("error", "Provider API key is not configured.")
        return JSONResponse({"error": "Add INFOMANIAK_API_KEY to api/.env to start chatting."}, status_code=503)

    # Reuse the application's HTTPX2 connection pool and timeout configuration.
    client = request.app.state.client
    provider = OpenAIProvider(base_url=str(client.base_url), api_key=settings.INFOMANIAK_API_KEY.get_secret_value(), http_client=client)
    model = OpenAIChatModel(
        settings.INFOMANIAK_MODEL,
        provider=provider,
        profile=OpenAIModelProfile(openai_chat_supports_max_completion_tokens=False, openai_chat_streaming_requires_finish_reason=True),
    )
    agent = Agent(
        model,
        system_prompt=settings.SYSTEM_PROMPT,
        toolsets=[MCPToolset(server, max_retries=2)],
        retries=0,
        model_settings={"max_tokens": 4096, "max_retries": 0, "timeout": client.timeout},
    )

    # Forward only validated text, not client-supplied provider metadata or control parts.
    run_input = request_types.SubmitMessage(
        id=str(uuid4()),
        messages=[
            request_types.UIMessage(id=message.id, role=message.role, parts=[request_types.TextUIPart(text=message.text)])
            for message in body.messages
            if message.text
        ],
    )
    adapter = VercelAIAdapter(agent=agent, run_input=run_input, sdk_version=6, server_message_id=str(uuid4()))

    # Start the provider request before committing to a successful streaming response.
    trace.record("thinking", "Waiting for the model response.")
    native = adapter.run_stream_native()
    if isinstance(native, AsyncGenerator):
        await resources.enter_async_context(aclosing(native))
    try:
        first = await anext(native)
    except (exceptions.ModelHTTPError, exceptions.ModelConnectionError):
        trace.status = "error"
        trace.record("error", ERROR_MESSAGE)
        return JSONResponse({"error": ERROR_MESSAGE}, status_code=502)
    except Exception as error:
        first = error

    return StreamingResponse(
        stream_response(adapter, native, first, resources, trace),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
