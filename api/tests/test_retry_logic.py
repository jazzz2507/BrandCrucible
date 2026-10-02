import json
import pytest
import asyncio
from google.genai import errors
from llm import call_stage_llm, LLMError
from schemas import DiscoverSchema

class FakeResponse:
    def __init__(self, text: str):
        self.text = text

class FakeModels:
    def __init__(self, handler):
        self.handler = handler

    def generate_content(self, model, contents, config):
        return self.handler(model, contents, config)

class FakeGenAIClient:
    def __init__(self, handler):
        self.models = FakeModels(handler)

VALID_DISCOVER_JSON = json.dumps({
    "audience": {"primary": "Founders", "secondary": "Designers"},
    "problem_statement": "Branding is difficult",
    "constraints": ["Limited budget"],
    "assumptions": ["Market exists"],
    "open_questions": ["Pricing model?"]
})

@pytest.mark.asyncio
async def test_retry_429_with_suggested_delay(monkeypatch):
    # 429 uses the suggested delay + 1s
    sleep_calls = []

    async def mock_sleep(d):
        sleep_calls.append(d)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    calls = 0
    def handler(model, contents, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise errors.APIError(
                code=429,
                response_json={"error": {"message": "ResourceExhausted: retryDelay: 5.5s"}}
            )
        return FakeResponse(VALID_DISCOVER_JSON)

    client = FakeGenAIClient(handler)
    res = await call_stage_llm("Discover", "Initial prompt", DiscoverSchema, client=client)

    assert isinstance(res, DiscoverSchema)
    assert calls == 2
    # 5.5s suggested delay + 1s = 6.5s
    assert sleep_calls == [6.5]

@pytest.mark.asyncio
async def test_retry_429_without_suggestion_stops_after_3_retries(monkeypatch):
    # without a suggestion it uses 20/40/60s and stops after 3 retries
    sleep_calls = []

    async def mock_sleep(d):
        sleep_calls.append(d)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    calls = 0
    def handler(model, contents, config):
        nonlocal calls
        calls += 1
        raise errors.APIError(
            code=429,
            response_json={"error": {"message": "ResourceExhausted: Rate limit exceeded without delay info"}}
        )

    client = FakeGenAIClient(handler)
    with pytest.raises(LLMError, match="Exceeded 3 429 retries"):
        await call_stage_llm("Discover", "Initial prompt", DiscoverSchema, client=client)

    assert sleep_calls == [20.0, 40.0, 60.0]

@pytest.mark.asyncio
async def test_retry_503_backoff_schedule(monkeypatch):
    # 503 uses min(attempt*15, 60)
    sleep_calls = []

    async def mock_sleep(d):
        sleep_calls.append(d)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    calls = 0
    def handler(model, contents, config):
        nonlocal calls
        calls += 1
        if calls <= 5:
            raise errors.APIError(
                code=503,
                response_json={"error": {"message": "ServiceUnavailable: Backend overloaded"}}
            )
        return FakeResponse(VALID_DISCOVER_JSON)

    client = FakeGenAIClient(handler)
    res = await call_stage_llm("Discover", "Initial prompt", DiscoverSchema, client=client)

    assert isinstance(res, DiscoverSchema)
    # Attempt 1: min(1*15, 60) = 15.0
    # Attempt 2: min(2*15, 60) = 30.0
    # Attempt 3: min(3*15, 60) = 45.0
    # Attempt 4: min(4*15, 60) = 60.0
    # Attempt 5: min(5*15, 60) = 60.0
    assert sleep_calls == [15.0, 30.0, 45.0, 60.0, 60.0]

@pytest.mark.asyncio
async def test_validation_failure_appends_repair_note_and_gives_up_after_8_attempts(monkeypatch):
    # a validation failure appends the repair note and gives up after 8 attempts
    prompts_received = []

    def handler(model, contents, config):
        prompts_received.append(contents)
        # Return invalid schema that triggers ValidationError
        return FakeResponse(json.dumps({"invalid_field": 123}))

    client = FakeGenAIClient(handler)
    with pytest.raises(LLMError, match="after 8 attempts"):
        await call_stage_llm("Discover", "Original prompt text", DiscoverSchema, client=client)

    assert len(prompts_received) == 8
    # Attempt 1 gets the original prompt
    assert prompts_received[0] == "Original prompt text"

    # Subsequent attempts get the repair note appended
    for prompt in prompts_received[1:]:
        assert "Original prompt text\n\nYour previous output failed:" in prompt
        assert "Fix the problem and return corrected JSON only." in prompt

@pytest.mark.asyncio
async def test_connection_error_retries_on_503_schedule(monkeypatch):
    sleep_calls = []
    async def mock_sleep(d):
        sleep_calls.append(d)
    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    calls = 0
    def handler(model, contents, config):
        nonlocal calls
        calls += 1
        if calls <= 3:
            raise Exception("connection reset by peer")
        return FakeResponse(VALID_DISCOVER_JSON)

    client = FakeGenAIClient(handler)
    res = await call_stage_llm("Discover", "Prompt", DiscoverSchema, client=client)

    assert isinstance(res, DiscoverSchema)
    # min(1*15, 60)=15, min(2*15, 60)=30, min(3*15, 60)=45
    assert sleep_calls == [15.0, 30.0, 45.0]

@pytest.mark.asyncio
async def test_fast_failure_400_401_404(monkeypatch):
    sleep_calls = []
    async def mock_sleep(d):
        sleep_calls.append(d)
    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    def handler(model, contents, config):
        raise errors.APIError(
            code=400,
            response_json={"error": {"message": "Bad Request"}}
        )

    client = FakeGenAIClient(handler)
    with pytest.raises(LLMError, match="Fatal API error"):
        await call_stage_llm("Discover", "Prompt", DiscoverSchema, client=client)

    assert sleep_calls == []

@pytest.mark.asyncio
async def test_complex_mixed_failure_success_sequence(monkeypatch):
    sleep_calls = []
    async def mock_sleep(d):
        sleep_calls.append(d)
    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    calls = 0
    def handler(model, contents, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            # 1: 503 error
            raise errors.APIError(code=503, response_json={})
        elif calls == 2:
            # 2: validation error
            return FakeResponse(json.dumps({"invalid_field": 123}))
        elif calls == 3:
            # 3: connection error
            raise Exception("connection dropped")
        elif calls == 4:
            # 4: 429 error without suggestion
            raise errors.APIError(code=429, response_json={})
        # 5: Success
        return FakeResponse(VALID_DISCOVER_JSON)

    client = FakeGenAIClient(handler)
    res = await call_stage_llm("Discover", "Prompt", DiscoverSchema, client=client)

    assert isinstance(res, DiscoverSchema)
    assert calls == 5
    # Call 1 (attempt 1, 503): 15s
    # Call 2 (attempt 2, validation): no sleep
    # Call 3 (attempt 3, connection): 45s (min(3*15, 60))
    # Call 4 (attempt 4, 429 without suggestion): uses retries_429 schedule. It is the first 429, so [0] => 20.0s
    assert sleep_calls == [15.0, 45.0, 20.0]
