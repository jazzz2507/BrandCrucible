import pytest
import main
from main import ip_sessions

def test_idea_length_validation(client):
    # 1. 501-char idea exceeds MAX_IDEA_CHARS (500)
    long_idea = "A" * 501
    res = client.post("/api/interview/start", json={"idea": long_idea})
    assert res.status_code == 422
    assert "MAX_IDEA_CHARS" in res.json()["detail"]

    # 2. Idea with fewer than 10 chars fails
    short_idea = "A" * 9
    res_short = client.post("/api/interview/start", json={"idea": short_idea})
    assert res_short.status_code == 422
    assert "at least 10 characters" in res_short.json()["detail"]

    # 3. Valid idea succeeds
    valid_idea = "A valid idea string for neighborhood tool library"
    res_valid = client.post("/api/interview/start", json={"idea": valid_idea})
    assert res_valid.status_code == 200
    assert "sessionId" in res_valid.json()

def test_rate_limit(client, monkeypatch):
    # Rate limit: 5 sessions per hour
    monkeypatch.setattr(main, "RATE_LIMIT_SESSIONS_PER_HOUR", 5)
    ip_sessions.clear()

    # Create 5 sessions successfully
    for i in range(5):
        res = client.post("/api/interview/start", json={"idea": f"A valid startup idea number {i+1}"})
        assert res.status_code == 200, f"Attempt {i+1} failed"

    # 6th session should be rate limited (429)
    res_limit = client.post("/api/interview/start", json={"idea": "A 6th valid idea string here"})
    assert res_limit.status_code == 429
    assert "Rate limit exceeded" in res_limit.json()["detail"]
    assert "Retry-After" in res_limit.headers

def test_golden_demo_bypasses_limits(client, monkeypatch):
    # Enforce strict rate limit and exhaust it
    monkeypatch.setattr(main, "RATE_LIMIT_SESSIONS_PER_HOUR", 1)
    ip_sessions.clear()

    # First session succeeds
    res1 = client.post("/api/interview/start", json={"idea": "First session that consumes quota"})
    assert res1.status_code == 200

    # Normal session is now rate limited
    res_blocked = client.post("/api/interview/start", json={"idea": "Blocked session attempt"})
    assert res_blocked.status_code == 429

    # Golden demo bypasses rate limits on all endpoints
    res_golden_trace = client.get("/api/trace/golden-demo")
    assert res_golden_trace.status_code == 200
    assert res_golden_trace.json()["sessionId"] == "golden-demo"

    res_golden_kit = client.get("/api/brand-kit/golden-demo")
    assert res_golden_kit.status_code == 200

    # Golden demo pipeline stream also works despite interview rate limit
    with client.stream("GET", "/api/pipeline/stream/golden-demo") as response:
        assert response.status_code == 200
        first_line = next(response.iter_lines())
        assert first_line is not None
