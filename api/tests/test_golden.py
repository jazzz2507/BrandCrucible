import pytest

def test_golden_demo_endpoints(client):
    # Verify stream endpoint
    with client.stream("GET", "/api/pipeline/stream/golden-demo") as response:
        assert response.status_code == 200
        first_line = next(response.iter_lines())
        assert first_line is not None

    # Verify trace endpoint
    res_trace = client.get("/api/trace/golden-demo")
    assert res_trace.status_code == 200
    data = res_trace.json()
    assert data["sessionId"] == "golden-demo"
    assert "trace" in data

    # Verify brand kit endpoint
    res_kit = client.get("/api/brand-kit/golden-demo")
    assert res_kit.status_code == 200
    kit_data = res_kit.json()
    assert "brand" in kit_data or "brand_name" in kit_data
