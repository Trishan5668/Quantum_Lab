from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


PENNYLANE_BELL = """\
import pennylane as qml

dev = qml.device("default.qubit", wires=2)

@qml.qnode(dev)
def bell_circuit():
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    return qml.probs()

print(bell_circuit())
"""

PENNYLANE_INVALID = """\
import pennylane as qml

dev = qml.device("default.qubit", wires=2)
print(undefined_variable)
"""


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("pennylane") is None,
    reason="pennylane not installed",
)
def test_editor_run_valid_pennylane(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "pennylane", "code": PENNYLANE_BELL},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["language"] == "pennylane"
    assert data["status"] == "success"
    assert "0.5" in data["stdout"]


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("pennylane") is None,
    reason="pennylane not installed",
)
def test_editor_run_invalid_pennylane(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "pennylane", "code": PENNYLANE_INVALID},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "error"
    assert data["stderr"]
