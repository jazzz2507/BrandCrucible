import pytest
import asyncio
from main import get_pipeline_semaphore, MAX_CONCURRENT_PIPELINES
from store import store
import os
import time

@pytest.fixture(autouse=True)
def reset_semaphore():
    import main
    # Reset semaphore state before each test
    main.pipeline_semaphore = None
    main.queue_waiters = 0
    yield
    main.pipeline_semaphore = None
    main.queue_waiters = 0

def test_golden_demo_ignores_semaphore(client):
    # Occupy all semaphore slots manually
    sem = get_pipeline_semaphore()
    
    # We must acquire in a new event loop or using a sync wrapper since this is sync pytest,
    # but FastAPI TestClient uses a separate loop for the app.
    # We can just manually set the internal value to simulate it being fully locked.
    if hasattr(sem, "_value"):
        sem._value = 0
    
    start = time.time()
    events = []
    # Trigger the golden demo
    with client.stream("GET", "/api/pipeline/stream/golden-demo") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event:"):
                events.append(line)
            if "event: done" in line or "event: error" in line:
                break
                
    duration = time.time() - start
    
    # Assert golden demo completed fast despite 0 semaphore slots
    assert duration < 2.0
    assert "event: done" in events
    
def test_semaphore_release_on_exception(client, monkeypatch):
    import main
    
    # Mock run_stage to raise an exception
    async def mock_run_stage(stage, session):
        raise RuntimeError("Mock error in pipeline")
        
    monkeypatch.setattr(main, "run_stage", mock_run_stage)
    
    sem = main.get_pipeline_semaphore()
    if hasattr(sem, "_value"):
        initial_slots = sem._value
    
    res = client.post("/api/interview/start", json={"idea": "A test idea that will crash on purpose"})
    session_id = res.json()["sessionId"]
    
    events = []
    with client.stream("GET", f"/api/pipeline/stream/{session_id}") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event:"):
                events.append(line)
            if "event: done" in line or "event: error" in line:
                break
                
    # Verify exception resulted in error event
    assert "event: error" in events
    
    # Verify semaphore was released
    if hasattr(sem, "_value"):
        assert sem._value == initial_slots
        
def test_pipeline_timeout_handling(client, monkeypatch):
    import main
    
    # Set pipeline timeout very low
    monkeypatch.setenv("PIPELINE_TIMEOUT_SECONDS", "1")
    
    async def mock_run_stage(stage, session):
        await asyncio.sleep(2)
        return {}
        
    monkeypatch.setattr(main, "run_stage", mock_run_stage)
    
    res = client.post("/api/interview/start", json={"idea": "A test idea that will timeout on purpose"})
    session_id = res.json()["sessionId"]
    
    events = []
    with client.stream("GET", f"/api/pipeline/stream/{session_id}") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("event:"):
                events.append(line)
            if "event: done" in line or "event: error" in line:
                break
                
    assert "event: error" in events
