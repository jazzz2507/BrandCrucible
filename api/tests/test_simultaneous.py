import pytest
import concurrent.futures
from store import store

def test_simultaneous_listeners(client):
    # Create a session
    res = client.post("/api/interview/start", json={"idea": "A neighborhood tool library test idea with enough length"})
    assert res.status_code == 200
    session_id = res.json()["sessionId"]

    def listen():
        events = []
        with client.stream("GET", f"/api/pipeline/stream/{session_id}") as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if line.startswith("event:"):
                    events.append(line)
                if "event: done" in line or "event: error" in line:
                    break
        return events

    # Run two listeners simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(listen)
        f2 = executor.submit(listen)
        events_1 = f1.result(timeout=10)
        events_2 = f2.result(timeout=10)

    # Both listeners should receive all 15 events (7 stages * 2 + 1 done)
    assert len(events_1) == 15
    assert len(events_2) == 15
    assert events_1[-1] == "event: done"
    assert events_2[-1] == "event: done"

    # Verify session trace endpoint
    res_trace = client.get(f"/api/trace/{session_id}")
    assert res_trace.status_code == 200
    assert "trace" in res_trace.json()
