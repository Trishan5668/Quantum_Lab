"""Experiment specifications and runs backed by the real QEC engine.

The web layer never re-implements scientific logic.  Protocol validation is
performed by ``quantumlab.research.qec.protocol``; execution is performed by
``python -m quantumlab.research.qec run`` in a separate, resource-limited
process; integrity and claim checks reuse ``artifacts`` and ``claims``.

A run's evidence directory is written once and never rewritten.  Re-running an
experiment creates a new run that references the same specification (and
optionally the run it reproduces).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from app.quanthub import auth, config, db
from app.quanthub.errors import bad_request, conflict, not_found
from app.quanthub.service import ProjectContext

try:  # the scientific engine is an optional-at-import dependency of the API
    from quantumlab.research.qec.audit import repository_capabilities
    from quantumlab.research.qec.protocol import (
        ProtocolError,
        validate_experiment_protocol,
    )

    ENGINE_IMPORT_ERROR: str | None = None
except Exception as exc:  # noqa: BLE001 - reported to the UI as EngineUnavailable
    repository_capabilities = None  # type: ignore[assignment]
    validate_experiment_protocol = None  # type: ignore[assignment]
    ENGINE_IMPORT_ERROR = str(exc)


SUPPORTED_CODE_FAMILIES = ["repetition", "steane", "five_qubit", "surface_code", "repetition_stim"]
STIM_FAMILIES = {"surface_code", "repetition_stim", "surface_code_stim"}
PAULI_FAMILIES = {"repetition", "steane", "five_qubit"}

DECODER_INFO: dict[str, dict[str, Any]] = {
    "exact": {
        "label": "Exact minimum-weight",
        "backend": "pauli",
        "description": (
            "Exhaustive minimum-weight lookup over stabilizer cosets. Assumes "
            "independent Pauli errors; bounded by max_enumeration."
        ),
        "parameters": {"max_enumeration": 1_000_000},
    },
    "majority_vote": {
        "label": "Repetition majority vote",
        "backend": "pauli",
        "description": "Classical majority vote for the repetition code only.",
        "parameters": {},
    },
    "mwpm": {
        "label": "Minimum-weight perfect matching",
        "backend": "pauli|stim",
        "description": (
            "PyMatching on the detector error model for Stim-backed codes; a "
            "Pauli-algebra adapter for CSS codes with Z-type stabilizers."
        ),
        "parameters": {"error_probability": 0.01},
    },
    "no_correction": {
        "label": "No correction (baseline)",
        "backend": "pauli|stim",
        "description": "Reports raw logical failure counts with no decoding.",
        "parameters": {},
    },
}


NOISE_PARAMETER_KEYS: dict[str, tuple[set[str], set[str]]] = {
    "bit_flip": ({"p"}, set()),
    "phase_flip": ({"p"}, set()),
    "depolarizing": ({"p"}, set()),
    "pauli": (set(), {"p_x", "p_y", "p_z"}),
    "phenomenological": ({"data_channel"}, set()),
    "circuit_level": (set(), {"p_gate", "p_measurement", "p_reset", "p_round"}),
}


def engine_available() -> tuple[bool, str | None]:
    return ENGINE_IMPORT_ERROR is None, ENGINE_IMPORT_ERROR


def stim_available() -> bool:
    return (
        importlib.util.find_spec("stim") is not None
        and importlib.util.find_spec("pymatching") is not None
    )


def capabilities_payload() -> dict[str, Any]:
    available, error = engine_available()
    if not available or repository_capabilities is None:
        return {
            "engine": {"available": False, "error": error},
            "code_families": [],
            "decoders": [],
            "stim": False,
        }
    payload = repository_capabilities()
    payload["engine"] = {"available": True, "error": None}
    payload["stim"] = stim_available()
    payload["ui_code_families"] = [
        {
            "id": family,
            "available": stim_available() if family in STIM_FAMILIES else True,
            "backend": "stim" if family in STIM_FAMILIES else "pauli",
            "requires": "stim + pymatching" if family in STIM_FAMILIES else "numpy",
        }
        for family in SUPPORTED_CODE_FAMILIES
    ]
    payload["ui_decoders"] = [
        {
            "id": name,
            "label": info["label"],
            "backend": info["backend"],
            "description": info["description"],
            "parameters": info["parameters"],
            "available": (
                stim_available() if "stim" in str(info["backend"]) and name == "mwpm" else True
            ),
        }
        for name, info in DECODER_INFO.items()
    ]
    return payload


def _noise_parameter_error(noise: dict[str, Any]) -> str | None:
    model = str(noise.get("model", ""))
    parameters = noise.get("parameters")
    if not isinstance(parameters, dict):
        return "noise.parameters must be a mapping"
    spec = NOISE_PARAMETER_KEYS.get(model)
    if spec is None:
        return f"unsupported noise model '{model}'"
    required, optional = spec
    missing = required - set(parameters)
    if missing:
        return f"noise.parameters for '{model}' requires {sorted(missing)}"
    unknown = set(parameters) - required - optional
    if unknown:
        # A misspelled rate would silently disable the noise channel, so the
        # engine refuses it instead of running an unlabelled noiseless model.
        return f"unknown noise.parameters for '{model}': {sorted(unknown)}"
    if model == "pauli" and not optional & set(parameters):
        return "noise.parameters for 'pauli' requires at least one of p_x, p_y, p_z"
    return None


def validate_protocol_payload(raw: dict[str, Any]) -> dict[str, Any]:
    available, error = engine_available()
    if not available or validate_experiment_protocol is None:
        raise bad_request(
            "EngineUnavailable",
            f"The QEC engine is not importable: {error}",
        )
    if not isinstance(raw, dict):
        raise bad_request("InvalidProtocol", "The experiment protocol must be an object.")
    noise = raw.get("noise")
    if isinstance(noise, dict):
        problem = _noise_parameter_error(noise)
        if problem:
            raise bad_request("InvalidProtocol", problem)
    try:
        protocol = validate_experiment_protocol(raw)
    except ProtocolError as exc:
        raise bad_request("InvalidProtocol", str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise bad_request("InvalidProtocol", str(exc)) from exc

    family = protocol.code.family
    for decoder in protocol.decoders:
        if family in STIM_FAMILIES and decoder.name not in {"mwpm", "no_correction"}:
            raise bad_request(
                "InvalidDecoder",
                f"Stim-backed code families support only mwpm/no_correction; got '{decoder.name}'.",
            )
        if decoder.name == "majority_vote" and family != "repetition":
            raise bad_request(
                "InvalidDecoder",
                "majority_vote is only defined for the repetition code.",
            )
    if family in STIM_FAMILIES and not stim_available():
        raise bad_request(
            "StimUnavailable",
            "This environment does not have Stim and PyMatching installed, so "
            "circuit-level surface-code runs are unavailable.",
        )
    return {
        "protocol": protocol.raw,
        "config_hash": protocol.config_hash,
        "summary": {
            "name": protocol.name,
            "backend": "stim" if family in STIM_FAMILIES else "pauli",
            "code": protocol.code.to_dict(),
            "noise": protocol.noise.to_dict(),
            "decoders": [decoder.to_dict() for decoder in protocol.decoders],
            "shots": protocol.experiment.shots,
            "seed": protocol.experiment.seed,
            "partition": protocol.experiment.partition,
            "statistics": protocol.statistics.to_dict(),
        },
    }


TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "repetition-capacity-d3",
        "name": "Repetition code d=3 (code capacity)",
        "description": (
            "One ideal syndrome round, independent bit-flip noise, exact and "
            "majority-vote decoding. Fast, deterministic baseline."
        ),
        "requires_stim": False,
        "protocol": {
            "schema_version": "2.0",
            "name": "Repetition code d=3 code-capacity baseline",
            "research_question": (
                "Under a one-round ideal-syndrome bit-flip model, how do exact "
                "minimum-weight and majority-vote decoding compare?"
            ),
            "hypothesis": (
                "Exact minimum-weight decoding performs at least as well as "
                "majority voting on the distance-3 repetition code."
            ),
            "code": {"family": "repetition", "distance": 3, "rounds": 1, "task": "memory_z"},
            "noise": {
                "kind": "code_capacity",
                "model": "bit_flip",
                "parameters": {"p": 0.1},
            },
            "decoders": [
                {"name": "exact", "mode": "min_weight", "parameters": {}},
                {"name": "majority_vote", "mode": "min_weight", "parameters": {}},
                {"name": "no_correction", "mode": "min_weight", "parameters": {}},
            ],
            "comparisons": ["exact:majority_vote", "exact:no_correction"],
            "experiment": {
                "shots": 2000,
                "seed": 20261020,
                "partition": "development",
                "stopping_rule": "fixed_shots",
                "max_runtime_seconds": 120,
            },
            "statistics": {
                "method": "wilson",
                "confidence_level": 0.95,
                "primary_metric": "operational_failure_probability",
            },
            "resources": {"data_qubits": 3, "syndrome_bits": 2, "rounds": 1},
            "limitations": [
                "One ideal syndrome round; no measurement, gate, reset, idle, or leakage faults.",
                "Classical bit-flip noise only.",
            ],
        },
    },
    {
        "id": "surface-code-stim-d3",
        "name": "Rotated surface code d=3 (circuit level, Stim)",
        "description": (
            "Circuit-level depolarizing noise executed by Stim with a PyMatching "
            "MWPM decoder on the detector error model. Requires stim + pymatching."
        ),
        "requires_stim": True,
        "protocol": {
            "schema_version": "2.0",
            "name": "Rotated surface code d=3 circuit-level memory",
            "research_question": (
                "What logical failure probability does a distance-3 rotated "
                "surface-code memory show under circuit-level depolarizing noise?"
            ),
            "hypothesis": (
                "Below threshold, the d=3 logical failure probability is lower "
                "than the uncorrected data-qubit error probability."
            ),
            "code": {"family": "surface_code", "distance": 3, "rounds": 3, "task": "memory_z"},
            "noise": {
                "kind": "circuit_level",
                "model": "circuit_level",
                "parameters": {
                    "p_gate": 0.001,
                    "p_measurement": 0.001,
                    "p_reset": 0.001,
                    "p_round": 0.001,
                },
            },
            "decoders": [
                {"name": "mwpm", "mode": "min_weight", "parameters": {}},
                {"name": "no_correction", "mode": "min_weight", "parameters": {}},
            ],
            "comparisons": ["mwpm:no_correction"],
            "experiment": {
                "shots": 5000,
                "seed": 20261020,
                "partition": "development",
                "stopping_rule": "fixed_shots",
                "max_runtime_seconds": 300,
            },
            "statistics": {
                "method": "wilson",
                "confidence_level": 0.95,
                "primary_metric": "operational_failure_probability",
            },
            "resources": {"rounds": 3},
            "limitations": [
                "Circuit-level depolarizing model only; no leakage, drift, or correlated noise.",
                "Results are Stim/PyMatching results, not native QuantHub simulation.",
            ],
        },
    },
    {
        "id": "steane-phenomenological",
        "name": "Steane code, phenomenological noise",
        "description": (
            "Steane [[7,1,3]] code with a single syndrome round and classical "
            "measurement error. Exact and Pauli-MWPM decoders."
        ),
        "requires_stim": False,
        "protocol": {
            "schema_version": "2.0",
            "name": "Steane code phenomenological single-round",
            "research_question": (
                "How does exact decoding compare with MWPM on the Steane code "
                "with measurement error?"
            ),
            "hypothesis": (
                "Exact and MWPM decoding agree closely on a small CSS code with "
                "independent depolarizing data errors."
            ),
            "code": {"family": "steane", "distance": 3, "rounds": 1, "task": "memory_z"},
            "noise": {
                "kind": "phenomenological",
                "model": "phenomenological",
                "parameters": {"data_channel": {"model": "depolarizing", "p": 0.02}},
                "measurement_error": 0.005,
                "rounds": 1,
            },
            "decoders": [
                {"name": "exact", "mode": "min_weight", "parameters": {}},
                {"name": "mwpm", "mode": "min_weight", "parameters": {"error_probability": 0.02}},
            ],
            "comparisons": ["exact:mwpm"],
            "experiment": {
                "shots": 1000,
                "seed": 20261020,
                "partition": "development",
                "stopping_rule": "fixed_shots",
                "max_runtime_seconds": 180,
            },
            "statistics": {
                "method": "wilson",
                "confidence_level": 0.95,
                "primary_metric": "operational_failure_probability",
            },
            "resources": {"rounds": 1},
            "limitations": [
                "A single phenomenological syndrome round; no circuit-level faults.",
                "The exact decoder ignores measurement faults in its likelihood — a documented mismatch baseline.",
            ],
        },
    },
)


def templates_payload() -> list[dict[str, Any]]:
    available = stim_available()
    return [
        {
            "id": template["id"],
            "name": template["name"],
            "description": template["description"],
            "requires_stim": template["requires_stim"],
            "available": available if template["requires_stim"] else True,
            "protocol": template["protocol"],
        }
        for template in TEMPLATES
    ]


# ---------------------------------------------------------------------------
# Experiment specifications
# ---------------------------------------------------------------------------


def _spec_payload(row: sqlite3.Row, run_stats: sqlite3.Row | None = None) -> dict[str, Any]:
    protocol = db.json_load(row["protocol"], {})
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "slug": row["slug"],
        "name": row["name"],
        "description": row["description"],
        "protocol": protocol,
        "config_hash": row["config_hash"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "created_by": row["created_by"],
        "run_count": int(run_stats["n"]) if run_stats else 0,
        "last_run_at": run_stats["last_run_at"] if run_stats else None,
        "last_status": run_stats["last_status"] if run_stats else None,
    }


def _unique_spec_slug(conn: sqlite3.Connection, project_id: str, base: str) -> str:
    slug = base
    index = 0
    while conn.execute(
        "SELECT 1 FROM experiment_specs WHERE project_id = ? AND slug = ?",
        (project_id, slug),
    ).fetchone():
        index += 1
        slug = f"{base[:70]}-{index}"
    return slug


def list_specs(conn: sqlite3.Connection, ctx: ProjectContext) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM experiment_specs WHERE project_id = ? ORDER BY updated_at DESC",
        (ctx.id,),
    ).fetchall()
    payload = []
    for row in rows:
        stats = conn.execute(
            "SELECT COUNT(*) AS n, MAX(created_at) AS last_run_at,"
            " (SELECT status FROM runs r2 WHERE r2.spec_id = ? ORDER BY created_at DESC LIMIT 1) AS last_status"
            " FROM runs WHERE spec_id = ?",
            (row["id"], row["id"]),
        ).fetchone()
        payload.append(_spec_payload(row, stats))
    return payload


def get_spec(conn: sqlite3.Connection, ctx: ProjectContext, spec_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM experiment_specs WHERE id = ? AND project_id = ?", (spec_id, ctx.id)
    ).fetchone()
    if row is None:
        raise not_found("Experiment not found.")
    stats = conn.execute(
        "SELECT COUNT(*) AS n, MAX(created_at) AS last_run_at,"
        " (SELECT status FROM runs r2 WHERE r2.spec_id = ? ORDER BY created_at DESC LIMIT 1) AS last_status"
        " FROM runs WHERE spec_id = ?",
        (spec_id, spec_id),
    ).fetchone()
    return _spec_payload(row, stats)


def create_spec(
    conn: sqlite3.Connection, ctx: ProjectContext, principal: auth.Principal, payload: dict[str, Any]
) -> dict[str, Any]:
    raw = payload.get("protocol")
    validated = validate_protocol_payload(raw if isinstance(raw, dict) else {})
    protocol = validated["protocol"]
    name = str(payload.get("name") or protocol["name"]).strip()[:120]
    description = str(payload.get("description") or "").strip()[:1000]
    slug_base = payload.get("slug") or _slugify(name)
    spec_id = "e_" + uuid.uuid4().hex[:16]
    now = db.utc_now()
    conn.execute(
        "INSERT INTO experiment_specs (id, project_id, slug, name, description, protocol,"
        " config_hash, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            spec_id,
            ctx.id,
            _unique_spec_slug(conn, ctx.id, slug_base),
            name,
            description,
            json.dumps(protocol, sort_keys=True),
            validated["config_hash"],
            principal.handle,
            now,
            now,
        ),
    )
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="experiment.created",
        payload={"experiment_id": spec_id, "name": name, "config_hash": validated["config_hash"]},
    )
    return get_spec(conn, ctx, spec_id)


def update_spec(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    spec_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = get_spec(conn, ctx, spec_id)
    fields: list[str] = []
    values: list[Any] = []
    if "protocol" in payload:
        validated = validate_protocol_payload(payload.get("protocol") or {})
        fields.extend(["protocol = ?", "config_hash = ?"])
        values.extend([json.dumps(validated["protocol"], sort_keys=True), validated["config_hash"]])
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise bad_request("InvalidExperimentName", "An experiment name is required.")
        fields.append("name = ?")
        values.append(name[:120])
    if "description" in payload:
        fields.append("description = ?")
        values.append(str(payload.get("description") or "").strip()[:1000])
    if not fields:
        raise bad_request("NoChanges", "No supported fields were provided.")
    fields.append("updated_at = ?")
    values.append(db.utc_now())
    conn.execute(
        f"UPDATE experiment_specs SET {', '.join(fields)} WHERE id = ? AND project_id = ?",
        [*values, spec_id, ctx.id],
    )
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="experiment.updated",
        payload={"experiment_id": spec_id, "name": existing["name"]},
    )
    return get_spec(conn, ctx, spec_id)


def delete_spec(
    conn: sqlite3.Connection, ctx: ProjectContext, principal: auth.Principal, spec_id: str
) -> dict[str, Any]:
    existing = get_spec(conn, ctx, spec_id)
    runs = conn.execute("SELECT COUNT(*) AS n FROM runs WHERE spec_id = ?", (spec_id,)).fetchone()
    if runs and int(runs["n"]) > 0:
        raise conflict(
            "ExperimentHasRuns",
            "This experiment has recorded runs. Its evidence must be preserved, so it "
            "cannot be deleted; archive the project instead.",
            runs=int(runs["n"]),
        )
    conn.execute("DELETE FROM experiment_specs WHERE id = ? AND project_id = ?", (spec_id, ctx.id))
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="experiment.deleted",
        payload={"experiment_id": spec_id, "name": existing["name"]},
    )
    return {"deleted": spec_id}


def _slugify(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in cleaned.split("-") if part)[:70] or "experiment"


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

RUN_TERMINAL = {"completed", "failed", "cancelled"}
RUN_ACTIVE = {"queued", "running", "cancelling"}


def artifacts_root(ctx: ProjectContext) -> Path:
    root = config.projects_dir() / ctx.id / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_workspace(ctx: ProjectContext, run_id: str) -> Path:
    path = config.projects_dir() / ctx.id / "runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_payload(row: sqlite3.Row, *, include_summary: bool = False) -> dict[str, Any]:
    summary = db.json_load(row["summary"], None)
    protocol = db.json_load(row["protocol"], {})
    payload: dict[str, Any] = {
        "id": row["id"],
        "project_id": row["project_id"],
        "spec_id": row["spec_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "config_hash": row["config_hash"],
        "project_revision": row["project_revision"],
        "error": row["error"],
        "exit_code": row["exit_code"],
        "software_revision": row["software_revision"],
        "reproduction_of": row["reproduction_of"],
        "actor": row["actor_handle"],
        "scientific_status": (summary or {}).get("scientific_status"),
        "protocol": protocol if include_summary else None,
        "artifacts_available": bool(row["artifacts_path"] and Path(row["artifacts_path"]).is_dir()),
    }
    if include_summary:
        payload["summary"] = summary
        payload["results"] = result_view(summary or {})
    return payload


def result_view(summary: dict[str, Any]) -> dict[str, Any] | None:
    """Normalise engine output for the UI without inventing any numbers."""
    result = summary.get("result")
    if not isinstance(result, dict):
        return None
    decoders = result.get("decoders")
    rows: list[dict[str, Any]] = []
    if isinstance(decoders, dict):
        for name, payload in decoders.items():
            if not isinstance(payload, dict):
                continue
            rows.append(
                {
                    "decoder": name,
                    "trials": payload.get("trials"),
                    "operational_failures": payload.get("operational_failures"),
                    "logical_failures": payload.get("logical_failures"),
                    "probability": payload.get("probability"),
                    "interval_low": payload.get("interval_low"),
                    "interval_high": payload.get("interval_high"),
                    "method": payload.get("method"),
                    "confidence_level": payload.get("confidence_level"),
                    "zero_failure_upper_bound": payload.get("zero_failure_upper_bound"),
                    "status_counts": payload.get("status_counts"),
                    "interpretation": payload.get("interpretation"),
                }
            )
    comparisons = result.get("comparisons")
    return {
        "backend": result.get("backend"),
        "shots": result.get("shots"),
        "task": result.get("task"),
        "code": result.get("code"),
        "noise": result.get("noise"),
        "decoders": rows,
        "comparisons": comparisons if isinstance(comparisons, list) else [],
        "decoder_limits": result.get("decoder_limits"),
        "seed_streams": result.get("seed_streams"),
        "record_encoding": result.get("record_encoding"),
    }


def get_run(conn: sqlite3.Connection, ctx: ProjectContext, run_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM runs WHERE id = ? AND project_id = ?", (run_id, ctx.id)
    ).fetchone()
    if row is None:
        raise not_found("Run not found.")
    return row


def list_runs(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    *,
    spec_id: str | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    if spec_id:
        rows = conn.execute(
            "SELECT * FROM runs WHERE project_id = ? AND spec_id = ? ORDER BY created_at DESC LIMIT ?",
            (ctx.id, spec_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM runs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (ctx.id, limit),
        ).fetchall()
    return [_run_payload(row) for row in rows]


def create_run(
    conn: sqlite3.Connection,
    ctx: ProjectContext,
    principal: auth.Principal,
    spec_id: str,
    *,
    reproduction_of: str | None = None,
    protocol_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = get_spec(conn, ctx, spec_id)
    raw = protocol_override or spec["protocol"]
    validated = validate_protocol_payload(raw)
    run_id = "r_" + uuid.uuid4().hex[:16]
    now = db.utc_now()
    workspace = run_workspace(ctx, run_id)
    protocol_path = workspace / "protocol.json"
    protocol_path.write_text(json.dumps(validated["protocol"], indent=2, sort_keys=True), encoding="utf-8")
    log_path = workspace / "run.log"
    revision = ctx.project.get("revision")
    conn.execute(
        "INSERT INTO runs (id, project_id, spec_id, status, created_at, config_hash,"
        " project_revision, log_path, protocol, reproduction_of, actor_id, actor_handle)"
        " VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            ctx.id,
            spec_id,
            now,
            validated["config_hash"],
            revision,
            str(log_path),
            json.dumps(validated["protocol"], sort_keys=True),
            reproduction_of,
            principal.id,
            principal.handle,
        ),
    )
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="run.queued",
        payload={
            "run_id": run_id,
            "experiment_id": spec_id,
            "experiment": spec["name"],
            "config_hash": validated["config_hash"],
        },
    )
    from app.quanthub import jobs

    jobs.submit(ctx, run_id, protocol_path, artifacts_root(ctx), log_path)
    return _run_payload(get_run(conn, ctx, run_id))


def cancel_run(
    conn: sqlite3.Connection, ctx: ProjectContext, principal: auth.Principal, run_id: str
) -> dict[str, Any]:
    row = get_run(conn, ctx, run_id)
    if row["status"] in RUN_TERMINAL:
        raise conflict("RunFinished", f"This run already finished with status '{row['status']}'.")
    from app.quanthub import jobs

    jobs.request_cancel(run_id)
    conn.execute(
        "UPDATE runs SET status = 'cancelling', cancel_requested = 1 WHERE id = ?", (run_id,)
    )
    db.record_activity(
        conn,
        project_id=ctx.id,
        actor_id=principal.id,
        actor_handle=principal.handle,
        event_type="run.cancelled",
        payload={"run_id": run_id},
    )
    return _run_payload(get_run(conn, ctx, run_id))


def artifact_files(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        return []
    items = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 128), b""):
                digest.update(chunk)
        items.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    return items


def run_detail(
    conn: sqlite3.Connection, ctx: ProjectContext, run_id: str
) -> dict[str, Any]:
    row = get_run(conn, ctx, run_id)
    payload = _run_payload(row, include_summary=True)
    directory = Path(row["artifacts_path"]) if row["artifacts_path"] else None
    payload["artifacts"] = artifact_files(directory) if directory else []
    payload["log_available"] = bool(row["log_path"] and Path(row["log_path"]).is_file())
    payload["manifest"] = None
    if directory and (directory / "manifest.json").is_file():
        payload["manifest"] = db.json_load(
            (directory / "manifest.json").read_text(encoding="utf-8"), None
        )
    return payload


def run_log(ctx: ProjectContext, run_id: str, *, max_bytes: int = 64_000) -> dict[str, Any]:
    path = config.projects_dir() / ctx.id / "runs" / run_id / "run.log"
    if not path.is_file():
        return {"content": "", "truncated": False}
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(size - max_bytes)
            content = handle.read().decode("utf-8", "replace")
            return {"content": content, "truncated": True, "size": size}
        return {"content": handle.read().decode("utf-8", "replace"), "truncated": False, "size": size}


def verify_run(ctx: ProjectContext, run_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    row = get_run(conn, ctx, run_id)
    directory = Path(row["artifacts_path"] or "")
    if not directory.is_dir():
        raise not_found("This run has no committed artifacts to verify.")
    from quantumlab.research.qec.artifacts import verify_artifact

    report = verify_artifact(directory)
    return report.to_dict()


def claims_run(ctx: ProjectContext, run_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    row = get_run(conn, ctx, run_id)
    directory = Path(row["artifacts_path"] or "")
    if not directory.is_dir():
        raise not_found("This run has no committed artifacts to audit.")
    from quantumlab.research.qec.claims import audit_artifact

    return audit_artifact(directory)


def package_run(ctx: ProjectContext, run_id: str, conn: sqlite3.Connection) -> Path:
    row = get_run(conn, ctx, run_id)
    directory = Path(row["artifacts_path"] or "")
    if not directory.is_dir():
        raise not_found("This run has no committed artifacts to package.")
    from quantumlab.research.qec.artifacts import package_artifact

    destination_root = config.data_dir() / "tmp"
    destination_root.mkdir(parents=True, exist_ok=True)
    return package_artifact(directory, destination_root)


def artifact_path(ctx: ProjectContext, run_id: str, name: str, conn: sqlite3.Connection) -> Path:
    row = get_run(conn, ctx, run_id)
    directory = Path(row["artifacts_path"] or "")
    if not directory.is_dir():
        raise not_found("This run has no committed artifacts.")
    if "/" in name or name in {"", ".", ".."} or name.startswith("."):
        raise bad_request("InvalidArtifactName", "Artifact names are flat file names.")
    path = directory / name
    if not path.is_file():
        raise not_found("That artifact does not exist.")
    return path


def summary_for_export(conn: sqlite3.Connection, ctx: ProjectContext, run_id: str) -> dict[str, Any]:
    row = get_run(conn, ctx, run_id)
    return {
        "run": _run_payload(row),
        "summary": db.json_load(row["summary"], None),
        "protocol": db.json_load(row["protocol"], {}),
    }


def materialise_reproduction_bundle(
    conn: sqlite3.Connection, ctx: ProjectContext, run_id: str
) -> Path:
    """Export config, metadata and results as a portable research bundle."""
    row = get_run(conn, ctx, run_id)
    directory = Path(row["artifacts_path"] or "")
    if not directory.is_dir():
        raise not_found("This run has no committed artifacts to bundle.")
    bundle_root = config.data_dir() / "tmp"
    bundle_root.mkdir(parents=True, exist_ok=True)
    target = bundle_root / f"{ctx.owner_handle}-{ctx.project['slug']}-{run_id}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for path in directory.iterdir():
        if path.is_file():
            shutil.copy2(path, target / path.name)
    metadata = {
        "quanthub": {
            "project": f"{ctx.owner_handle}/{ctx.project['slug']}",
            "project_revision": row["project_revision"],
            "run_id": row["id"],
            "config_hash": row["config_hash"],
            "created_at": row["created_at"],
            "software_revision": row["software_revision"],
            "reproduction_of": row["reproduction_of"],
        }
    }
    (target / "quanthub-run.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.make_archive(str(target), "zip", root_dir=target)
    archive = target.with_suffix(target.suffix + ".zip")
    shutil.rmtree(target, ignore_errors=True)
    return archive


def project_run_stats(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed"
        " FROM runs WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    return {"total": int(row["total"] or 0) if row else 0, "completed": int(row["completed"] or 0) if row else 0}


__all__ = [
    "TEMPLATES",
    "artifact_path",
    "artifacts_root",
    "cancel_run",
    "capabilities_payload",
    "claims_run",
    "create_run",
    "create_spec",
    "delete_spec",
    "get_run",
    "get_spec",
    "list_runs",
    "list_specs",
    "package_run",
    "result_view",
    "run_detail",
    "run_log",
    "summary_for_export",
    "templates_payload",
    "update_spec",
    "validate_protocol_payload",
    "verify_run",
]

