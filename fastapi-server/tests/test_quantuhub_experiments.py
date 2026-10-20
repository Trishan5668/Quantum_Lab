"""Integration tests for QuantHub experiments executed by the real QEC engine."""

from __future__ import annotations

import io
import json
import time
import zipfile
from collections.abc import Iterator
from typing import Any

import pytest
from app.main import create_app
from app.quanthub import db as hub_db
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("QUANTHUB_ENV", "test")
    monkeypatch.setenv("QUANTHUB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("QUANTHUB_TRUST_CLIENT_IDENTITY", "1")
    monkeypatch.setenv("QUANTHUB_NEWS_FEEDS", "")
    hub_db.reset_init_cache()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def auth(handle: str = "alice") -> dict[str, str]:
    return {"X-QuantHub-User": handle, "X-QuantHub-Name": handle.title()}


def make_project(client: TestClient, **overrides: Any) -> dict[str, Any]:
    payload = {"name": "QEC Sandbox", "description": "Experiments", "visibility": "public", **overrides}
    response = client.post("/api/v1/projects", json=payload, headers=auth())
    assert response.status_code == 201, response.text
    return response.json()["data"]


def template_protocol(client: TestClient, template_id: str) -> dict[str, Any]:
    templates = client.get("/api/v1/experiments/templates").json()["data"]["templates"]
    for template in templates:
        if template["id"] == template_id:
            return template["protocol"]
    raise AssertionError(f"template {template_id} missing")


def wait_for(
    client: TestClient, base: str, run_id: str, *, timeout: float = 90.0
) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        response = client.get(f"{base}/runs/{run_id}", headers=auth())
        assert response.status_code == 200, response.text
        last = response.json()["data"]
        if last["status"] in {"completed", "failed", "cancelled"}:
            return last
        time.sleep(0.4)
    raise AssertionError(f"run {run_id} did not finish: {last}")


def test_templates_and_capabilities(client: TestClient) -> None:
    payload = client.get("/api/v1/experiments/templates").json()["data"]
    ids = {template["id"] for template in payload["templates"]}
    assert {"repetition-capacity-d3", "surface-code-stim-d3", "steane-phenomenological"} <= ids
    capabilities = client.get("/api/v1/capabilities/qec").json()["data"]
    assert capabilities["engine"]["available"] is True
    assert capabilities["decoders"]
    assert "mwpm" in {decoder["id"] for decoder in capabilities["ui_decoders"]}
    # Every template that ships must itself validate.
    for template in payload["templates"]:
        if not template["available"]:
            continue
        response = client.post(
            "/api/v1/experiments/validate", json={"protocol": template["protocol"]}
        )
        assert response.status_code == 200, (template["id"], response.text)


def test_invalid_protocols_are_rejected_with_precise_errors(client: TestClient) -> None:
    good = template_protocol(client, "repetition-capacity-d3")

    misspelled = json.loads(json.dumps(good))
    misspelled["noise"]["parameters"] = {"physical_error_rate": 0.1}
    response = client.post("/api/v1/experiments/validate", json={"protocol": misspelled})
    assert response.status_code == 400
    assert "p" in response.json()["error"]["message"]

    even_distance = json.loads(json.dumps(good))
    even_distance["code"]["distance"] = 4
    response = client.post("/api/v1/experiments/validate", json={"protocol": even_distance})
    assert response.status_code == 400

    bad_decoder = json.loads(json.dumps(good))
    bad_decoder["decoders"] = [{"name": "majority_vote"}]
    bad_decoder["code"]["family"] = "steane"
    bad_decoder["code"]["distance"] = 3
    response = client.post("/api/v1/experiments/validate", json={"protocol": bad_decoder})
    assert response.status_code == 400
    assert "majority_vote" in response.json()["error"]["message"]

    unknown_key = json.loads(json.dumps(good))
    unknown_key["surprise"] = True
    response = client.post("/api/v1/experiments/validate", json={"protocol": unknown_key})
    assert response.status_code == 400
    assert "unknown keys" in response.json()["error"]["message"]


def test_experiment_spec_lifecycle(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")

    created = client.post(
        f"{base}/experiments",
        json={"name": "Baseline d3", "description": "first", "protocol": protocol},
        headers=auth(),
    )
    assert created.status_code == 201, created.text
    spec = created.json()["data"]
    assert spec["config_hash"]
    assert spec["run_count"] == 0

    listing = client.get(f"{base}/experiments").json()["data"]
    assert [item["id"] for item in listing["experiments"]] == [spec["id"]]

    patched = client.patch(
        f"{base}/experiments/{spec['id']}",
        json={"name": "Renamed d3"},
        headers=auth(),
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "Renamed d3"

    deleted = client.delete(f"{base}/experiments/{spec['id']}", headers=auth())
    assert deleted.status_code == 200
    assert client.get(f"{base}/experiments").json()["data"]["experiments"] == []


def test_invalid_spec_creation_is_rejected(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")
    protocol["experiment"]["shots"] = 0
    response = client.post(
        f"{base}/experiments", json={"name": "bad", "protocol": protocol}, headers=auth()
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "InvalidProtocol"


def test_real_run_produces_traceable_artifacts(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")
    protocol["experiment"]["shots"] = 400
    spec = client.post(
        f"{base}/experiments", json={"name": "Runnable", "protocol": protocol}, headers=auth()
    ).json()["data"]

    started = client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth())
    assert started.status_code == 202, started.text
    run_id = started.json()["data"]["id"]
    assert started.json()["data"]["status"] in {"queued", "running"}

    finished = wait_for(client, base, run_id)
    assert finished["status"] == "completed", finished
    assert finished["exit_code"] == 0
    assert finished["config_hash"] == spec["config_hash"]
    assert finished["scientific_status"] in {
        "NOT_INDEPENDENTLY_VALIDATED",
        "PENDING_VALIDATION",
    }

    results = finished["results"]
    assert results["backend"] == "pauli"
    assert results["shots"] == 400
    decoder_names = {row["decoder"] for row in results["decoders"]}
    assert {"exact", "majority_vote", "no_correction"} <= decoder_names
    for row in results["decoders"]:
        assert row["trials"] == 400
        assert row["probability"] == pytest.approx(
            (row["operational_failures"] or 0) / 400
        )
        assert row["interval_low"] <= row["probability"] <= row["interval_high"]

    artifacts = {item["name"]: item for item in finished["artifacts"]}
    assert {"summary.json", "config.json", "manifest.json", "checksums.sha256", "report.md"} <= set(artifacts)
    assert finished["manifest"]["files"]["summary.json"]["sha256"] == artifacts["summary.json"]["sha256"]

    integrity = client.post(f"{base}/runs/{run_id}/verify", headers=auth())
    assert integrity.status_code == 200, integrity.text
    assert integrity.json()["data"]["ok"] is True

    claims = client.get(f"{base}/runs/{run_id}/claims", headers=auth())
    assert claims.status_code == 200
    assert claims.json()["data"]["status"] in {"PASS", "FAIL"}

    artifact = client.get(f"{base}/runs/{run_id}/artifacts/summary.json", headers=auth())
    assert artifact.status_code == 200
    assert json.loads(artifact.content)["experiment_id"] == run_id

    traversal = client.get(f"{base}/runs/{run_id}/artifacts/..%2F..%2Fetc%2Fpasswd", headers=auth())
    assert traversal.status_code in {400, 404}

    exported = client.get(f"{base}/runs/{run_id}/export", headers=auth())
    assert exported.status_code == 200
    assert exported.json()["run"]["id"] == run_id

    bundle = client.get(f"{base}/runs/{run_id}/bundle", headers=auth())
    assert bundle.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        names = archive.namelist()
    assert "summary.json" in names
    assert "quanthub-run.json" in names


def test_rerun_preserves_previous_evidence(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")
    protocol["experiment"]["shots"] = 150
    spec = client.post(
        f"{base}/experiments", json={"name": "Repeatable", "protocol": protocol}, headers=auth()
    ).json()["data"]

    first = client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth()).json()["data"]
    wait_for(client, base, first["id"])
    second = client.post(
        f"{base}/experiments/{spec['id']}/runs",
        json={"reproduce_run": first["id"]},
        headers=auth(),
    ).json()["data"]
    assert second["reproduction_of"] == first["id"]
    wait_for(client, base, second["id"])

    runs = client.get(f"{base}/runs").json()["data"]["runs"]
    ids = {run["id"] for run in runs}
    assert {first["id"], second["id"]} <= ids
    reopened = client.get(f"{base}/runs/{first['id']}", headers=auth())
    assert reopened.status_code == 200
    assert reopened.json()["data"]["status"] == "completed"

    blocked = client.delete(f"{base}/experiments/{spec['id']}", headers=auth())
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "ExperimentHasRuns"


def test_run_access_control(client: TestClient) -> None:
    project = make_project(client, visibility="private")
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")
    protocol["experiment"]["shots"] = 120
    spec = client.post(
        f"{base}/experiments", json={"name": "Private", "protocol": protocol}, headers=auth()
    ).json()["data"]
    run = client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth()).json()["data"]
    wait_for(client, base, run["id"])

    assert client.get(f"{base}/runs/{run['id']}").status_code == 403
    assert client.get(f"{base}/runs/{run['id']}", headers=auth("mallory")).status_code == 403
    assert client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth("mallory")).status_code == 403


def test_cancel_rules(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")
    protocol["experiment"]["shots"] = 120
    spec = client.post(
        f"{base}/experiments", json={"name": "Cancelable", "protocol": protocol}, headers=auth()
    ).json()["data"]
    run = client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth()).json()["data"]
    wait_for(client, base, run["id"])

    response = client.post(f"{base}/runs/{run['id']}/cancel", headers=auth())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RunFinished"

    denied = client.post(f"{base}/runs/{run['id']}/cancel", headers=auth("mallory"))
    assert denied.status_code == 403


def test_cancel_a_long_running_experiment(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "repetition-capacity-d3")
    protocol["experiment"]["shots"] = 2_000_000
    protocol["experiment"]["max_runtime_seconds"] = 600
    spec = client.post(
        f"{base}/experiments", json={"name": "Long", "protocol": protocol}, headers=auth()
    ).json()["data"]
    run = client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth()).json()["data"]

    cancel = client.post(f"{base}/runs/{run['id']}/cancel", headers=auth())
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["data"]["status"] in {"cancelling", "cancelled"}

    deadline = time.time() + 60
    status = None
    while time.time() < deadline:
        status = client.get(f"{base}/runs/{run['id']}", headers=auth()).json()["data"]["status"]
        if status in {"cancelled", "failed", "completed"}:
            break
        time.sleep(0.4)
    assert status == "cancelled", status


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("stim")
    or not __import__("importlib").util.find_spec("pymatching"),
    reason="Stim/PyMatching are not installed",
)
def test_surface_code_run_uses_stim_backend(client: TestClient) -> None:
    project = make_project(client)
    base = f"/api/v1/projects/alice/{project['slug']}"
    protocol = template_protocol(client, "surface-code-stim-d3")
    protocol["experiment"]["shots"] = 400
    spec = client.post(
        f"{base}/experiments", json={"name": "Stim d3", "protocol": protocol}, headers=auth()
    ).json()["data"]
    run = client.post(f"{base}/experiments/{spec['id']}/runs", json={}, headers=auth()).json()["data"]
    finished = wait_for(client, base, run["id"], timeout=180)
    assert finished["status"] == "completed", finished
    assert finished["results"]["backend"].startswith("stim")
    decoders = {row["decoder"]: row for row in finished["results"]["decoders"]}
    assert "mwpm" in decoders
    names = {item["name"] for item in finished["artifacts"]}
    assert {"circuit.stim", "detector_error_model.dem"} <= names
