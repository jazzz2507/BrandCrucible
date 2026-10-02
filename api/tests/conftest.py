import os
import sys
import pytest
import asyncio
from fastapi.testclient import TestClient

api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

# Ensure USE_MOCK_LLM is true by default for tests
os.environ["USE_MOCK_LLM"] = "true"

from main import app, ip_sessions
from store import store

@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """Ensure no tests actually wait for real sleeps."""
    recorded_sleeps = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay=0):
        recorded_sleeps.append(delay)
        # Yield control to event loop without real delay
        await real_sleep(0.0001)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded_sleeps

@pytest.fixture
def client(monkeypatch):
    """Provide a TestClient with clean store and rate limiting state."""
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    ip_sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
