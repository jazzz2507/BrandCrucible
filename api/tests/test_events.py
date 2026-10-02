import json
import pytest

def test_golden_demo_stream_events(client):
    # Stream golden demo and collect all events
    events = []
    ids = []
    with client.stream("GET", "/api/pipeline/stream/golden-demo") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("id:"):
                ids.append(int(line.split("id:")[1].strip()))
            elif line.startswith("event:"):
                events.append(line.split("event:")[1].strip())

    # 7 stages * 2 (start + complete) + 1 (done) = 15 events
    assert len(events) == 15
    assert events[0] == "stage_start"
    assert events[1] == "stage_complete"
    assert events[-1] == "done"
    assert ids == list(range(15))

def test_last_event_id_replay(client):
    # 1. Ensure golden-demo events are loaded/streamed
    with client.stream("GET", "/api/pipeline/stream/golden-demo") as response:
        list(response.iter_lines())

    # 2. Replay with Last-Event-ID: "5" -> should receive events from id 6 to 14
    replayed_ids = []
    replayed_events = []
    with client.stream("GET", "/api/pipeline/stream/golden-demo", headers={"Last-Event-ID": "5"}) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("id:"):
                replayed_ids.append(int(line.split("id:")[1].strip()))
            elif line.startswith("event:"):
                replayed_events.append(line.split("event:")[1].strip())

    expected_ids = list(range(6, 15))
    assert replayed_ids == expected_ids
    assert len(replayed_events) == len(expected_ids)
    assert replayed_events[-1] == "done"
    # Ensure no events before id 6 were sent
    assert all(i >= 6 for i in replayed_ids)

    # 3. Last-Event-ID: "14" (the final event) -> no new events should be yielded
    end_ids = []
    with client.stream("GET", "/api/pipeline/stream/golden-demo", headers={"Last-Event-ID": "14"}) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("id:"):
                end_ids.append(int(line.split("id:")[1].strip()))

    assert end_ids == []

    # 4. Non-numeric Last-Event-ID should fallback to start_index = 0
    fallback_ids = []
    with client.stream("GET", "/api/pipeline/stream/golden-demo", headers={"Last-Event-ID": "invalid-id"}) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("id:"):
                fallback_ids.append(int(line.split("id:")[1].strip()))

    assert fallback_ids == list(range(15))
