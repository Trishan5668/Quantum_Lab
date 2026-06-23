from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert body["data"]["status"] == "ok"
    assert body["data"]["version"] == "1.0.0"


def test_circuit_run_bell_state(client: TestClient) -> None:
    payload = {
        "num_qubits": 2,
        "gates": [
            {
                "id": "g0",
                "gate_type": "H",
                "qubit_targets": [0],
                "params": {},
                "time_step": 0,
            },
            {
                "id": "g1",
                "gate_type": "CNOT",
                "qubit_targets": [0, 1],
                "params": {},
                "time_step": 1,
            },
        ],
    }
    r = client.post("/api/v1/circuit/run", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    probs = body["data"]["final_state"]["probabilities"]
    assert math.isclose(probs[0], 0.5, abs_tol=1e-9)
    assert math.isclose(probs[3], 0.5, abs_tol=1e-9)
    assert math.isclose(probs[1], 0.0, abs_tol=1e-9)
    assert math.isclose(probs[2], 0.0, abs_tol=1e-9)


def test_circuit_run_rejects_bad_qubit(client: TestClient) -> None:
    payload = {
        "num_qubits": 1,
        "gates": [
            {
                "id": "g0",
                "gate_type": "H",
                "qubit_targets": [5],
                "params": {},
                "time_step": 0,
            }
        ],
    }
    r = client.post("/api/v1/circuit/run", json=payload)
    assert r.status_code == 400
    body = r.json()
    assert body["data"] is None
    assert body["error"]["code"] == "QubitIndexError"


def test_visualize_bloch_plus_state(client: TestClient) -> None:
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    payload = {
        "num_qubits": 1,
        "amplitudes": [
            {"real": inv_sqrt2, "imag": 0.0},
            {"real": inv_sqrt2, "imag": 0.0},
        ],
    }
    r = client.post("/api/v1/visualize/bloch", json=payload)
    assert r.status_code == 200
    body = r.json()
    q0 = body["data"]["qubits"][0]
    assert math.isclose(q0["theta"], math.pi / 2.0, abs_tol=1e-6)
    assert math.isclose(q0["phi"], 0.0, abs_tol=1e-6)


def test_visualize_density(client: TestClient) -> None:
    payload = {
        "num_qubits": 1,
        "amplitudes": [
            {"real": 1.0, "imag": 0.0},
            {"real": 0.0, "imag": 0.0},
        ],
    }
    r = client.post("/api/v1/visualize/density", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["dim"] == 2
    assert body["data"]["real"][0][0] == 1.0
    assert body["data"]["real"][1][1] == 0.0


_EXPLAIN_PAYLOAD = {
    "gate": "H",
    "qubit": 0,
    "state_before": [
        {"real": 1.0, "imag": 0.0},
        {"real": 0.0, "imag": 0.0},
    ],
    "state_after": [
        {"real": 1.0 / math.sqrt(2.0), "imag": 0.0},
        {"real": 1.0 / math.sqrt(2.0), "imag": 0.0},
    ],
    "num_qubits": 1,
    "context": "first_gate",
    "mode": "normal",
}


def test_explain_gemini_without_key_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/api/v1/explain", json=_EXPLAIN_PAYLOAD)
    assert r.status_code == 503
    body = r.json()
    assert body["detail"]["error"]["code"] == "MissingApiKeyError"
    assert "GEMINI_API_KEY" in body["detail"]["error"]["message"]


def test_explain_local_streams_sse_tokens(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with client.stream("POST", "/api/v1/explain", json=_EXPLAIN_PAYLOAD) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body_text = "".join(chunk for chunk in resp.iter_text())
    assert "event: token" in body_text
    assert "event: done" in body_text
    assert "\"text\":" in body_text


def test_explain_auto_falls_back_to_local(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with client.stream("POST", "/api/v1/explain", json=_EXPLAIN_PAYLOAD) as resp:
        assert resp.status_code == 200
        body_text = "".join(chunk for chunk in resp.iter_text())
    assert "event: token" in body_text
    assert "event: done" in body_text


def test_explain_unsupported_provider_returns_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "totallybogus")
    r = client.post("/api/v1/explain", json=_EXPLAIN_PAYLOAD)
    assert r.status_code == 500
    body = r.json()
    assert body["detail"]["error"]["code"] == "LlmConfigurationError"
