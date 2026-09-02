from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


QISKIT_BELL = """\
from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

print(qc)
"""

QISKIT_INVALID = """\
from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
print(undefined_variable)
"""

QSHARP_BELL = """\
operation Main() : Unit {
    use qs = Qubit[2];
    H(qs[0]);
    CNOT(qs[0], qs[1]);
    let r0 = MResetZ(qs[0]);
    let r1 = MResetZ(qs[1]);
    Message($"Bell results: {r0}, {r1}");
}
"""

QSHARP_INVALID = """\
operation Main() : Unit {
    Message(undefined_symbol);
}
"""


def test_editor_run_valid_qiskit(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "qiskit", "code": QISKIT_BELL},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["language"] == "qiskit"
    assert data["status"] == "success"
    assert "q_0" in data["stdout"] or "H" in data["stdout"]


def test_editor_run_invalid_qiskit(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "qiskit", "code": QISKIT_INVALID},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "error"
    assert data["stderr"]


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("qdk") is None,
    reason="qdk not installed",
)
def test_editor_run_valid_qsharp(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "qsharp", "code": QSHARP_BELL},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["language"] == "qsharp"
    assert data["status"] == "success"
    assert "Bell results" in data["stdout"]


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("qdk") is None,
    reason="qdk not installed",
)
def test_editor_run_invalid_qsharp(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "qsharp", "code": QSHARP_INVALID},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "error"
    assert data["stderr"]


def test_editor_run_empty_code(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "qiskit", "code": "   "},
    )
    assert resp.status_code == 422


def test_editor_run_unsupported_language(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/editor/run",
        json={"language": "cirq", "code": "print(1)"},
    )
    assert resp.status_code == 422
