from __future__ import annotations

import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ComplexAmplitude, GatePlacementIn
from app.models_v2 import ResearchVerifyRequest, SimulationConfigIn
from app.wolfram.client import WolframClient, WolframConfig, WolframUnavailableError, _extract_json_result
from app.wolfram.symbolic import wolfram_language_payload
from app.wolfram.verification import _structured_input
from app.wolfram.verification import verify_research_payload


class UnavailableClient:
    async def evaluate_research(self, *, cache_key: str, wolfram_language: str) -> dict[str, object]:
        raise WolframUnavailableError("test unavailable")


class CanonicalClient:
    async def evaluate_research(self, *, cache_key: str, wolfram_language: str) -> dict[str, object]:
        return {
            "calculations": {
                "gates": [
                    {
                        "gate_id": "cnot",
                        "gate_type": "CNOT",
                        "status": "VERIFIED",
                        "unitarity": "VERIFIED",
                        "eigenvalues": ["1", "1", "1", "-1"],
                        "determinant": "-1",
                        "trace": "2",
                        "rank": "4",
                        "characteristicPolynomial": "(-1 + x)^3 (1 + x)",
                        "minimalPolynomial": "(-1 + x) (1 + x)",
                    }
                ],
                "circuitUnitary": {
                    "status": "VERIFIED",
                    "eigenvalues": ["1", "1", "1", "-1"],
                    "determinant": "-1",
                    "trace": "2",
                    "rank": "4",
                },
                "densityMatrix": {"status": "VERIFIED"},
                "schmidt": {"status": "VERIFIED"},
                "partialTrace": {"status": "VERIFIED"},
                "entropy": {"status": "VERIFIED"},
                "fidelity": {"status": "VERIFIED"},
                "traceDistance": {"status": "VERIFIED"},
                "purity": {"status": "VERIFIED"},
                "correlations": {"status": "VERIFIED"},
            },
            "finalState": [
                {"real": 1.0, "imag": 0.0},
                {"real": 0.0, "imag": 0.0},
                {"real": 0.0, "imag": 0.0},
                {"real": 0.0, "imag": 0.0},
            ],
        }


def _wolfram_v2_payload(plaintext: str) -> dict[str, object]:
    return {
        "queryresult": {
            "success": True,
            "error": False,
            "numpods": 2,
            "inputstring": "integral of x^2",
            "pods": [
                {
                    "title": "Input",
                    "scanner": "Identity",
                    "subpods": [{"plaintext": "integral x^2 dx"}],
                },
                {
                    "title": "Result",
                    "scanner": "Integral",
                    "subpods": [{"title": "Indefinite integral", "plaintext": plaintext}],
                },
            ],
        }
    }


def _request(
    *,
    num_qubits: int = 1,
    gates: list[GatePlacementIn] | None = None,
    initial_basis_state: str = "0",
    final_state: list[ComplexAmplitude] | None = None,
) -> ResearchVerifyRequest:
    return ResearchVerifyRequest(
        num_qubits=num_qubits,
        initial_basis_state=initial_basis_state,
        gates=gates or [],
        simulation=SimulationConfigIn(),
        final_state=final_state
        or [ComplexAmplitude(real=1.0, imag=0.0), ComplexAmplitude(real=0.0, imag=0.0)],
        measurement_probabilities=[1.0, 0.0],
    )


def test_wolfram_query_builder_uses_valid_matrix_calculator_query() -> None:
    structured = _structured_input(_request(), [])
    query = wolfram_language_payload(structured)
    assert query == "matrix calculator for {{1, 0}, {0, 0}}"
    assert "QuantumLabResearchVerify" not in query
    assert "ImportString" not in query


def test_wolfram_parser_accepts_v2_json_with_machine_readable_plaintext() -> None:
    payload = _wolfram_v2_payload(
        '{"calculations":{"circuitUnitary":{"status":"VERIFIED"}},"finalState":[]}'
    )
    parsed = _extract_json_result(payload)
    assert parsed["calculations"]["circuitUnitary"]["status"] == "VERIFIED"


def test_wolfram_parser_accepts_successful_plaintext_without_json() -> None:
    payload = _wolfram_v2_payload("x^3/3 + constant")
    parsed = _extract_json_result(payload)
    wolfram = parsed["calculations"]["wolframAlpha"]
    assert wolfram["status"] == "VERIFIED"
    assert wolfram["pods"][1]["title"] == "Result"
    assert wolfram["pods"][1]["scanner"] == "Integral"
    assert wolfram["pods"][1]["subpods"][0]["title"] == "Indefinite integral"
    assert wolfram["pods"][1]["subpods"][0]["plaintext"] == "x^3/3 + constant"
    assert parsed["calculations"]["circuitUnitary"]["status"] == "UNAVAILABLE"


def test_wolfram_parser_accepts_string_boolean_fields() -> None:
    payload = _wolfram_v2_payload("4")
    query = payload["queryresult"]
    assert isinstance(query, dict)
    query["success"] = "true"
    query["error"] = "false"
    parsed = _extract_json_result(payload)
    assert parsed["calculations"]["wolframAlpha"]["status"] == "VERIFIED"


def test_wolfram_parser_rejects_success_false() -> None:
    payload = {"queryresult": {"success": False, "error": False, "pods": []}}
    with pytest.raises(WolframUnavailableError, match="successful computation"):
        _extract_json_result(payload)


def test_wolfram_parser_rejects_missing_required_fields() -> None:
    with pytest.raises(WolframUnavailableError, match="successful computation"):
        _extract_json_result({"unexpected": {}})


def test_wolfram_parser_rejects_missing_pods() -> None:
    payload = {"queryresult": {"success": True, "error": False}}
    with pytest.raises(WolframUnavailableError, match="result pods"):
        _extract_json_result(payload)


@pytest.mark.asyncio
async def test_wolfram_client_reports_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOLFRAM_APP_ID", "dummy-app-id")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.wolframalpha.com"
        assert request.url.params["appid"] == "dummy-app-id"
        assert request.url.params["output"] == "json"
        assert request.url.params["format"] == "plaintext"
        return httpx.Response(500, json={"queryresult": {"success": False}})

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def async_client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)
    client = WolframClient(WolframConfig.from_env())
    with pytest.raises(WolframUnavailableError, match="Wolfram HTTP error 500"):
        await client.evaluate_research(cache_key="http-error", wolfram_language="integral of x^2")


@pytest.mark.asyncio
async def test_wolfram_client_reports_malformed_success_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOLFRAM_APP_ID", "dummy-app-id")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_wolfram_v2_payload("x^3/3 + constant"))

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def async_client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)
    client = WolframClient(WolframConfig.from_env())
    result = await client.evaluate_research(cache_key="normal-plaintext", wolfram_language="integral of x^2")
    assert result["calculations"]["wolframAlpha"]["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_wolfram_client_reports_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOLFRAM_APP_ID", "dummy-app-id")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{not-json", headers={"content-type": "application/json"})

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def async_client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)
    client = WolframClient(WolframConfig.from_env())
    with pytest.raises(WolframUnavailableError, match="not valid JSON"):
        await client.evaluate_research(cache_key="malformed-json", wolfram_language="integral of x^2")


@pytest.mark.asyncio
async def test_wolfram_client_reports_missing_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOLFRAM_APP_ID", "dummy-app-id")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"queryresult": {"success": True, "error": False}})

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def async_client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)
    client = WolframClient(WolframConfig.from_env())
    with pytest.raises(WolframUnavailableError, match="result pods"):
        await client.evaluate_research(cache_key="missing-fields", wolfram_language="integral of x^2")


@pytest.mark.asyncio
async def test_research_verification_fails_closed_when_wolfram_unavailable() -> None:
    result = await verify_research_payload(_request(), client=UnavailableClient())  # type: ignore[arg-type]
    assert result["status"] == "UNAVAILABLE"
    assert "Wolfram verification is unavailable" in result["warnings"][0]["message"]
    assert result["calculations"]["circuitUnitary"]["status"] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_research_verification_cnot_spectrum_from_wolfram() -> None:
    req = _request(
        num_qubits=2,
        gates=[
            GatePlacementIn(
                id="cnot",
                gate_type="CNOT",
                qubit_targets=[0, 1],
                params={},
                time_step=0,
            )
        ],
        initial_basis_state="00",
        final_state=[
            ComplexAmplitude(real=1.0, imag=0.0),
            ComplexAmplitude(real=0.0, imag=0.0),
            ComplexAmplitude(real=0.0, imag=0.0),
            ComplexAmplitude(real=0.0, imag=0.0),
        ],
    )
    result = await verify_research_payload(req, client=CanonicalClient())  # type: ignore[arg-type]
    gate = result["calculations"]["gates"][0]
    assert result["status"] == "VERIFIED"
    assert gate["eigenvalues"] == ["1", "1", "1", "-1"]
    assert gate["unitarity"] == "VERIFIED"
    assert gate["determinant"] == "-1"


def test_research_verify_route_returns_unavailable_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOLFRAM_APP_ID", raising=False)
    client = TestClient(create_app())
    resp = client.post(
        "/api/v2/research/verify",
        json={
            "num_qubits": 1,
            "initial_basis_state": "0",
            "gates": [],
            "final_state": [{"real": 1.0, "imag": 0.0}, {"real": 0.0, "imag": 0.0}],
            "measurement_probabilities": [1.0, 0.0],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    ("name", "num_qubits", "gates", "initial", "final"),
    [
        ("zero", 1, [], "0", [(1, 0), (0, 0)]),
        ("one", 1, [], "1", [(0, 0), (1, 0)]),
        ("x_zero", 1, [("X", [0], {})], "0", [(0, 0), (1, 0)]),
        ("h_zero", 1, [("H", [0], {})], "0", [(2**-0.5, 0), (2**-0.5, 0)]),
        ("bell", 2, [("H", [0], {}), ("CNOT", [0, 1], {})], "00", [(2**-0.5, 0), (0, 0), (0, 0), (2**-0.5, 0)]),
        ("ghz", 3, [("H", [0], {}), ("CNOT", [0, 1], {}), ("CNOT", [1, 2], {})], "000", [(2**-0.5, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (2**-0.5, 0)]),
        ("swap", 2, [("CNOT", [0, 1], {}), ("CNOT", [1, 0], {}), ("CNOT", [0, 1], {})], "01", [(0, 0), (0, 0), (1, 0), (0, 0)]),
        ("stacked", 1, [("X", [0], {}), ("X", [0], {})], "0", [(1, 0), (0, 0)]),
        ("rotation", 1, [("RY", [0], {"theta": 1.5707963267948966})], "0", [(2**-0.5, 0), (2**-0.5, 0)]),
    ],
)
@pytest.mark.asyncio
async def test_canonical_structured_research_inputs_are_accepted(
    name: str,
    num_qubits: int,
    gates: list[tuple[str, list[int], dict[str, float]]],
    initial: str,
    final: list[tuple[float, float]],
) -> None:
    placements = [
        GatePlacementIn(
            id=f"{name}-{index}",
            gate_type=gate_type,  # type: ignore[arg-type]
            qubit_targets=targets,
            params=params,
            time_step=index,
        )
        for index, (gate_type, targets, params) in enumerate(gates)
    ]
    req = _request(
        num_qubits=num_qubits,
        gates=placements,
        initial_basis_state=initial,
        final_state=[ComplexAmplitude(real=re, imag=im) for re, im in final],
    )
    result = await verify_research_payload(req, client=UnavailableClient())  # type: ignore[arg-type]
    assert result["status"] == "UNAVAILABLE"
    structured = result["structured_input"]
    assert structured["numQubits"] == num_qubits
    assert structured["basisConvention"].startswith("big-endian")
