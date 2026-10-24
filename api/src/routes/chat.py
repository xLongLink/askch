import anyio
from uuid import uuid4
from typing import Annotated
from fastapi import Depends, Request, APIRouter
from contextlib import AsyncExitStack, aclosing
from src.prompt import SYSTEM_PROMPT
from pydantic_ai import Agent, exceptions
from src.settings import settings
from pydantic_ai.ui import NativeEvent
from collections.abc import AsyncIterator, AsyncGenerator
from src.models.chat import ChatRequest
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
    adapter: VercelAIAdapter[None, str], native: AsyncIterator[NativeEvent], first: NativeEvent | Exception, resources: AsyncExitStack
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
        if isinstance(chunk, response_types.ErrorChunk):
            yield encoder.encode_event(response_types.ErrorChunk(error_text=ERROR_MESSAGE))
            yield encoder.encode_event(response_types.DoneChunk())
            return
        yield encoder.encode_event(chunk)


@router.post("/chat", response_model=None)
async def chat(
    body: ChatRequest, request: Request, resources: Annotated[AsyncExitStack, Depends(stream_resources)]
) -> JSONResponse | StreamingResponse:
    """Run the OpenUI chat agent using the existing validated request boundary."""

    # Keep missing credentials separate from upstream provider errors.
    if not settings.INFOMANIAK_API_KEY.get_secret_value():
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
        model, system_prompt=SYSTEM_PROMPT, retries=0, model_settings={"max_tokens": 4096, "max_retries": 0, "timeout": client.timeout}
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
    native = adapter.run_stream_native()
    if isinstance(native, AsyncGenerator):
        await resources.enter_async_context(aclosing(native))
    try:
        first = await anext(native)
    except (exceptions.ModelHTTPError, exceptions.ModelConnectionError):
        return JSONResponse({"error": ERROR_MESSAGE}, status_code=502)
    except Exception as error:
        first = error

    return StreamingResponse(
        stream_response(adapter, native, first, resources),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
