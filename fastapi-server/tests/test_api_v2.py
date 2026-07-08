from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _bell_payload() -> dict[str, object]:
    return {
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


def test_v2_run_defaults_match_v1(client: TestClient) -> None:
    payload = _bell_payload()
    v1 = client.post("/api/v1/circuit/run", json=payload).json()["data"]
    v2 = client.post("/api/v2/circuit/run", json=payload).json()["data"]
    assert v1["final_state"]["probabilities"] == v2["final_state"]["probabilities"]


def test_v2_density_mode(client: TestClient) -> None:
    payload = _bell_payload()
    payload["simulation"] = {"mode": "density", "noise": {"enabled": False}}
    resp = client.post("/api/v2/circuit/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["simulation_mode"] == "density"
    assert data["final_density"] is not None
    assert data["purity"] == pytest.approx(1.0, abs=1e-6)


def test_v2_noisy_run_mixed(client: TestClient) -> None:
    payload = _bell_payload()
    payload["simulation"] = {
        "mode": "density",
        "noise": {"enabled": True, "channel": "depolarizing", "probability": 0.1},
    }
    data = client.post("/api/v2/circuit/run", json=payload).json()["data"]
    assert data["mixed_state"] is True
    assert data["purity"] < 1.0


def test_v2_fidelity_bell(client: TestClient) -> None:
    run = client.post(
        "/api/v2/circuit/run",
        json={
            **_bell_payload(),
            "simulation": {"mode": "density", "noise": {"enabled": False}},
        },
    ).json()["data"]
    amps = run["final_state"]["amplitudes"]
    resp = client.post(
        "/api/v2/metrics/fidelity",
        json={"num_qubits": 2, "amplitudes": amps, "target": "bell"},
    )
    data = resp.json()["data"]
    assert data["fidelity"] == pytest.approx(1.0, abs=1e-6)
    assert "Excellent" in data["interpretation"]


def test_v2_entropy_bell(client: TestClient) -> None:
    run = client.post(
        "/api/v2/circuit/run",
        json={
            **_bell_payload(),
            "simulation": {"mode": "density", "noise": {"enabled": False}},
        },
    ).json()["data"]
    dm = run["final_density"]
    resp = client.post(
        "/api/v2/metrics/entropy",
        json={
            "num_qubits": 2,
            "subsystem": [0],
            "density_real": dm["real"],
            "density_imag": dm["imag"],
        },
    )
    data = resp.json()["data"]
    assert data["entropy"] == pytest.approx(1.0, abs=1e-6)


def test_v2_purity(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/metrics/purity",
        json={
            "num_qubits": 1,
            "amplitudes": [{"real": 1.0, "imag": 0.0}, {"real": 0.0, "imag": 0.0}],
        },
    )
    data = resp.json()["data"]
    assert data["purity"] == pytest.approx(1.0, abs=1e-6)
