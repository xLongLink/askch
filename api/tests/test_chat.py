import json

import httpx
import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.models.settings import Settings
from src.routes.chat import ERROR_MESSAGE


def message(text="Hello", role="user"):
    return {"id": "1", "role": role, "parts": [{"type": "text", "text": text}]}


def settings(key="test-key"):
    return Settings(_env_file=None, infomaniak_api_key=key)


def events(response):
    return [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


def test_health():
    with TestClient(create_app(settings(""))) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_missing_key():
    with TestClient(create_app(settings(""))) as client:
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
def test_invalid_messages(body):
    def unexpected_request(request):
        pytest.fail("Invalid messages must not reach the provider")

    with TestClient(create_app(settings(), httpx.MockTransport(unexpected_request))) as client:
        assert client.post("/api/chat", json=body).status_code == 422


def test_streaming_chat():
    def upstream(request):
        assert str(request.url) == (
            "https://api.infomaniak.com/2/ai/112804/openai/v1/chat/completions"
        )
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "swiss-ai/Apertus-v1.5-70B"
        assert body["messages"][0]["role"] == "system"
        assert "Chart(" in body["messages"][0]["content"]
        assert body["messages"][1:] == [{"role": "user", "content": "Hello"}]
        assert body["stream"] is True
        return httpx.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"root = Stack([])"}}]}\n\n'
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                "data: [DONE]\n\n"
            ),
        )

    with TestClient(create_app(settings(), httpx.MockTransport(upstream))) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 200
        assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
        chunks = events(response)
        assert chunks[0]["type"] == "start"
        assert chunks[0]["messageId"]
        assert chunks[1:] == [
            {"type": "start-step"},
            {"type": "text-start", "id": "0"},
            {"type": "text-delta", "id": "0", "delta": "root = Stack([])"},
            {"type": "text-end", "id": "0"},
            {"type": "finish-step"},
            {"type": "finish", "finishReason": "stop"},
        ]
        assert response.text.endswith("data: [DONE]\n\n")


@pytest.mark.parametrize("assistant_text", ["root = Stack([])", ""])
def test_followup_accepts_step_start_parts(assistant_text):
    assistant = {
        "id": "assistant-1",
        "role": "assistant",
        "parts": [{"type": "step-start"}],
    }
    if assistant_text:
        assistant["parts"].append({"type": "text", "text": assistant_text, "state": "done"})

    def upstream(request):
        expected = [{"role": "user", "content": "Hello"}]
        if assistant_text:
            expected.append({"role": "assistant", "content": assistant_text})
        expected.append({"role": "user", "content": "Tell me more"})
        assert json.loads(request.content)["messages"][1:] == expected
        return httpx.Response(200, text="data: [DONE]\n\n")

    with TestClient(create_app(settings(), httpx.MockTransport(upstream))) as client:
        response = client.post(
            "/api/chat",
            json={"messages": [message(), assistant, message("Tell me more")]},
        )
        assert response.status_code == 200
        assert events(response)[-1] == {"type": "finish", "finishReason": "stop"}


def test_provider_error_is_sanitized():
    transport = httpx.MockTransport(lambda request: httpx.Response(401, text="secret-key"))
    with TestClient(create_app(settings(), transport)) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 502
        assert response.json() == {"error": ERROR_MESSAGE}
        assert "secret-key" not in response.text


def test_connection_failure():
    def upstream(request):
        raise httpx.ConnectError("secret-key", request=request)

    with TestClient(create_app(settings(), httpx.MockTransport(upstream))) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert response.status_code == 502
        assert response.json() == {"error": ERROR_MESSAGE}


@pytest.mark.parametrize("stream", ["data: invalid\n\n", 'data: {"error":"secret-key"}\n\n', ""])
def test_invalid_stream_is_sanitized(stream):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=stream))
    with TestClient(create_app(settings(), transport)) as client:
        response = client.post("/api/chat", json={"messages": [message()]})
        assert events(response)[-1] == {"type": "error", "errorText": ERROR_MESSAGE}
        assert "secret-key" not in response.text
