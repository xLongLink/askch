import json
import httpx2
import pytest
from src.prompt import SYSTEM_PROMPT
from src.settings import Settings
from src.routes.chat import ERROR_MESSAGE
from fastapi.testclient import TestClient


def message(text="Hello", role="user"):
    """Build an AI SDK message for request validation."""
    return {"id": "1", "role": role, "parts": [{"type": "text", "text": text}]}


def settings(key="test-key"):
    """Provide deterministic provider settings without dotenv credentials."""
    return Settings(_env_file=None, INFOMANIAK_API_KEY=key)


def events(response):
    """Decode SSE data frames from a completed response."""
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"]


def test_health(load_app):
    """Check health without a configured provider key."""
    app = load_app(settings(""))
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_missing_key(load_app):
    """Reject chat when the provider key is missing."""
    app = load_app(settings(""))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 503
        assert response.json() == {"error": "Add INFOMANIAK_API_KEY to api/.env to start chatting."}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"messages": "invalid"},
        {"messages": []},
        {"messages": [{"role": "user"}]},
        {"messages": [message(role="system")]},
        {"messages": [message()] * 101},
        {"messages": [message("x" * 100_001)]},
        {"messages": [message("x" * 60_000), message("x" * 60_000)]},
        {"messages": [{"id": "1", "role": "assistant", "parts": [{"type": "unknown"}]}]},
    ],
)
def test_invalid_messages(body, load_app):
    """Reject invalid messages before contacting the provider."""

    def unexpected_request(request):
        pytest.fail("Invalid messages must not reach the provider")

    app = load_app(settings(), httpx2.MockTransport(unexpected_request))
    with TestClient(app) as client:
        assert client.post("/api/chat", json=body).status_code == 422


def test_streaming_chat(load_app):
    """Translate a provider stream into the expected AI SDK protocol."""

    def upstream(request):
        assert str(request.url) == ("https://api.infomaniak.com/2/ai/112804/openai/v1/chat/completions")
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "swiss-ai/Apertus-v1.5-70B"
        assert body["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
        assert body["messages"][1:] == [{"role": "user", "content": "Hello"}]
        assert body["stream"] is True
        assert body["max_tokens"] == 4096
        assert request.extensions["timeout"] == {"connect": 10, "read": 60, "write": 60, "pool": 60}
        return httpx2.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"root = Stack([])"}}]}\n\n'
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                "data: [DONE]\n\n"
            ),
        )

    app = load_app(settings(), httpx2.MockTransport(upstream))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 200
        assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
        chunks = events(response)
        assert chunks[0]["type"] == "start"
        assert chunks[0]["messageId"]
        text_id = chunks[2]["id"]
        assert chunks[1:-3] == [
            {"type": "start-step"},
            {"type": "text-start", "id": text_id},
            {"type": "text-delta", "id": text_id, "delta": "root = Stack([])"},
            {"type": "text-end", "id": text_id},
        ]
        assert chunks[-3]["type"] == "message-metadata"
        assert chunks[-2] == {"type": "finish-step"}
        assert chunks[-1] == {"type": "finish", "finishReason": "stop"}
        assert response.text.endswith("data: [DONE]\n\n")


@pytest.mark.parametrize("assistant_text", ["root = Stack([])", ""])
def test_followup_accepts_step_start_parts(assistant_text, load_app):
    """Accept step-start markers when sending conversation follow-ups."""
    assistant = {"id": "assistant-1", "role": "assistant", "parts": [{"type": "step-start"}]}
    if assistant_text:
        assistant["parts"].append({"type": "text", "text": assistant_text, "state": "done"})

    def upstream(request):
        expected = [{"role": "user", "content": "Hello"}]
        if assistant_text:
            expected.append({"role": "assistant", "content": assistant_text})
        expected.append({"role": "user", "content": "Tell me more"})
        assert json.loads(request.content)["messages"][1:] == expected
        return httpx2.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"root = Stack([])"}}]}\n\n'
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                "data: [DONE]\n\n"
            ),
        )

    app = load_app(settings(), httpx2.MockTransport(upstream))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [message(), assistant, message("Tell me more")]})
        assert response.status_code == 200
        assert events(response)[-1] == {"type": "finish", "finishReason": "stop"}


def test_provider_error_is_sanitized(load_app):
    """Keep provider error bodies out of client responses."""
    transport = httpx2.MockTransport(lambda request: httpx2.Response(401, text="secret-key"))
    app = load_app(settings(), transport)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 502
        assert response.json() == {"error": ERROR_MESSAGE}
        assert "secret-key" not in response.text


def test_connection_failure(load_app):
    """Return a sanitized error when the provider cannot be reached."""

    def upstream(request):
        raise httpx2.ConnectError("secret-key", request=request)

    app = load_app(settings(), httpx2.MockTransport(upstream))
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 502
        assert response.json() == {"error": ERROR_MESSAGE}


@pytest.mark.parametrize("stream", ["data: invalid\n\n", 'data: {"error":"secret-key"}\n\n', ""])
def test_invalid_stream_is_sanitized(stream, load_app):
    """Convert malformed or incomplete streams into sanitized error events."""
    transport = httpx2.MockTransport(lambda request: httpx2.Response(200, text=stream))
    app = load_app(settings(), transport)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert events(response)[-1] == {"type": "error", "errorText": ERROR_MESSAGE}
        assert "secret-key" not in response.text
