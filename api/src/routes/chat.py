import json
from uuid import uuid4

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..models.chat import ChatRequest
from ..prompt import SYSTEM_PROMPT

router = APIRouter()
ERROR_MESSAGE = "Unable to get a response. Check your API key and model, then try again."


def event(kind: str, **data) -> str:
    return f"data: {json.dumps({'type': kind, **data})}\n\n"


async def stream_response(response: httpx.Response):
    try:
        yield event("start", messageId=str(uuid4()))
        yield event("start-step")
        yield event("text-start", id="0")
        finished = False
        finish_reason = "stop"
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                finished = True
                break
            chunk = json.loads(data)
            if "error" in chunk:
                raise ValueError("Provider stream error")
            for choice in chunk.get("choices", []):
                text = choice.get("delta", {}).get("content")
                if text:
                    yield event("text-delta", id="0", delta=text)
                if choice.get("finish_reason"):
                    finish_reason = {
                        "stop": "stop",
                        "length": "length",
                        "content_filter": "content-filter",
                        "tool_calls": "tool-calls",
                        "function_call": "tool-calls",
                    }.get(choice["finish_reason"], "unknown")
                    finished = True
        if not finished:
            raise ValueError("Incomplete provider stream")
        yield event("text-end", id="0")
        yield event("finish-step")
        yield event("finish", finishReason=finish_reason)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        yield event("error", errorText=ERROR_MESSAGE)
    finally:
        await response.aclose()
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    settings = request.app.state.settings
    if not settings.infomaniak_api_key.get_secret_value():
        return JSONResponse(
            {"error": "Add INFOMANIAK_API_KEY to api/.env to start chatting."}, status_code=503
        )
    client = request.app.state.client
    upstream_request = client.build_request(
        "POST",
        "chat/completions",
        json={
            "model": settings.infomaniak_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *[
                    {"role": message.role, "content": message.text}
                    for message in body.messages
                    if message.text
                ],
            ],
            "stream": True,
            "max_tokens": 4096,
        },
    )
    try:
        response = await client.send(upstream_request, stream=True)
    except httpx.HTTPError:
        return JSONResponse({"error": ERROR_MESSAGE}, status_code=502)
    if not response.is_success:
        await response.aclose()
        return JSONResponse({"error": ERROR_MESSAGE}, status_code=502)
    return StreamingResponse(
        stream_response(response),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
