"""Build processed tables from verified raw artifacts.

The script never edits raw results.  It refuses to process an artifact that
fails checksum verification and writes a manifest mapping each processed file
to its raw experiment ID and config hash.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from quantumlab.research.qec.artifacts import sha256_file, verify_artifact
from quantumlab.research.qec.claims import audit_artifact


def _latest(root: Path, predicate: Any) -> Path:
    candidates = []
    for directory in sorted(root.glob("2026*/")):
        summary = directory / "summary.json"
        if not summary.is_file():
            continue
        payload = json.loads(summary.read_text(encoding="utf-8"))
        if predicate(payload):
            candidates.append((directory.stat().st_mtime, directory))
    if not candidates:
        raise SystemExit(f"no matching raw artifact under {root}")
    return max(candidates)[1]


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    raw = base / "results" / "raw"
    processed = base / "results" / "processed"
    reports = base / "results" / "reports"
    processed.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    reproduction = _latest(raw, lambda s: "analysis" in s and "target" in s)
    calibration = _latest(
        raw, lambda s: s.get("config", {}).get("study") == "static_dem_mismatch_v1"
    )
    generalization = _latest(
        raw, lambda s: s.get("study") == "calibration_generalization_v2"
    )
    artifacts = {
        "reproduction": reproduction,
        "calibration_v1": calibration,
        "generalization_v2": generalization,
    }
    manifest: dict[str, Any] = {}
    for name, directory in artifacts.items():
        verify = verify_artifact(directory)
        claims = audit_artifact(directory)
        if not verify.ok:
            raise SystemExit(f"{name} failed integrity: {verify.errors}")
        manifest[name] = {
            "directory": directory.name,
            "config_hash": json.loads(
                (directory / "summary.json").read_text(encoding="utf-8")
            )["config_hash"],
            "integrity": verify.to_dict(),
            "claims": claims,
            "files_sha256": {
                path.name: sha256_file(path)
                for path in sorted(directory.iterdir())
                if path.is_file()
            },
        }

    repro_summary = json.loads((reproduction / "summary.json").read_text(encoding="utf-8"))
    with (processed / "phase2_threshold_points.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "stage",
                "distance",
                "p",
                "shots",
                "failures",
                "ler",
                "wilson_low",
                "wilson_high",
                "seed",
                "dem_sha256",
                "circuit_sha256",
            ]
        )
        for row in repro_summary["results"]:
            writer.writerow(
                [
                    row["stage"],
                    row["distance"],
                    row["p"],
                    row["shots"],
                    row["failures"],
                    row["probability"],
                    row["interval_low"],
                    row["interval_high"],
                    row["seed"],
                    row["dem_sha256"],
                    row["circuit_sha256"],
                ]
            )
    (processed / "phase2_threshold_analysis.json").write_text(
        json.dumps(repro_summary["analysis"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports / "PHASE2_REPRODUCTION.md").write_text(
        (reproduction / "report.md").read_text(encoding="utf-8"), encoding="utf-8"
    )

    cal_summary = json.loads((calibration / "summary.json").read_text(encoding="utf-8"))
    with (processed / "phase3_limitation.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "profile",
                "distance",
                "shots",
                "nominal_failures",
                "oracle_failures",
                "nominal_ler",
                "oracle_ler",
                "relative_excess",
                "risk_difference",
                "ci_low",
                "ci_high",
                "mcnemar_p",
            ]
        )
        for cell in cal_summary["phase3"]["cells"].values():
            comparison = cell["nominal_vs_oracle"]
            writer.writerow(
                [
                    cell["profile"]["name"],
                    cell["distance"],
                    comparison["trials"],
                    comparison["first_failures"],
                    comparison["second_failures"],
                    comparison["first_ler"],
                    comparison["second_ler"],
                    comparison["relative_excess"],
                    comparison["difference_first_minus_second"],
                    comparison["difference_bootstrap_ci"][0],
                    comparison["difference_bootstrap_ci"][1],
                    comparison["mcnemar"]["p_value"],
                ]
            )
    (processed / "phase3_verdict.json").write_text(
        json.dumps(cal_summary["phase3"]["verdict"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports / "PHASE3_LIMITATION.md").write_text(
        (calibration / "report.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (processed / "phase4_calibration_v1.json").write_text(
        json.dumps(
            {
                "status": cal_summary["phase4"]["status"],
                "selections": cal_summary["phase4"]["selections"],
                "gates": cal_summary["phase4"]["gates"],
                "claim_labels": cal_summary["claim_labels"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    gen_summary = json.loads((generalization / "summary.json").read_text(encoding="utf-8"))
    (processed / "phase4_calibration_v2_generalization.json").write_text(
        json.dumps(
            {
                "status": gen_summary["status"],
                "selections": gen_summary["selections"],
                "gates": gen_summary["gates"],
                "claim_labels": gen_summary["claim_labels"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (reports / "PHASE4_CANDIDATE.md").write_text(
        (generalization / "report.md").read_text(encoding="utf-8")
        + "\n\n---\n\n"
        + "## v1 identifiability result\n\n"
        + (calibration / "report.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (processed / "ARTIFACTS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Read the pre-declared study declaration as a final mutation guard.
    import yaml

    declaration = yaml.safe_load(
        (base / "protocol" / "static_dem_mismatch_v1.yaml").read_text(encoding="utf-8")
    )
    if declaration.get("study") != "static_dem_mismatch_v1":
        raise SystemExit("study declaration name mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
