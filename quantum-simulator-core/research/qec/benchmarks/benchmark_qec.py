"""Small, reproducible engineering benchmarks (not scientific claims)."""

from __future__ import annotations

import importlib.util
import json
import platform
import statistics
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quantumlab.research.qec.codes import repetition_code
from quantumlab.research.qec.decoders.exact import ExactDecoder
from quantumlab.research.qec.decoders.mwpm import DetectorMWPMDecoder
from quantumlab.research.qec.noise import CircuitLevelNoiseModel, bit_flip


def _median_time(function: Callable[[], Any], repeats: int = 3) -> float:
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        function()
        timings.append(time.perf_counter() - start)
    return float(statistics.median(timings))


def main() -> int:
    output: dict[str, Any] = {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "notice": (
            "Engineering timings on this sandbox only. They are not a "
            "performance comparison to published decoders."
        ),
        "benchmarks": {},
    }
    for distance in (3, 5, 7):
        code = repetition_code(distance)
        channel = bit_flip(0.05)
        build = _median_time(lambda c=code, ch=channel: ExactDecoder(c, ch))
        decoder = ExactDecoder(code, channel)
        syndromes = [
            tuple(
                (index >> (code.num_stabilizers - 1 - bit)) & 1
                for bit in range(code.num_stabilizers)
            )
            for index in range(2**code.num_stabilizers)
        ]
        decode = _median_time(
            lambda d=decoder, items=syndromes: [d.decode(syndrome) for syndrome in items]
        )
        output["benchmarks"][f"exact_d{distance}"] = {
            "table_build_seconds": build,
            "syndromes": len(syndromes),
            "decode_all_syndromes_seconds": decode,
            "microseconds_per_decode": 1e6 * decode / len(syndromes),
            "table_size": decoder.table_size,
        }
    if importlib.util.find_spec("stim") is not None and importlib.util.find_spec(
        "pymatching"
    ) is not None:
        for distance in (3, 5):
            circuit = CircuitLevelNoiseModel.uniform(0.01).stim_circuit(
                distance, distance, task="surface_code:rotated_memory_z"
            )
            error_model = circuit.detector_error_model(decompose_errors=True)
            decoder = DetectorMWPMDecoder(error_model)
            sampler = circuit.compile_detector_sampler(seed=1234)
            detectors, _ = sampler.sample(shots=2000, separate_observables=True)
            decode = _median_time(
                lambda d=decoder, shots=detectors: d.decode_batch(shots)
            )
            output["benchmarks"][f"mwpm_surface_d{distance}"] = {
                "detectors": int(error_model.num_detectors),
                "shots": 2000,
                "decode_batch_seconds": decode,
                "microseconds_per_shot": 1e6 * decode / 2000,
            }
    else:
        output["benchmarks"]["mwpm_surface"] = {
            "status": "BLOCKED",
            "reason": "stim or pymatching not installed",
        }
    destination = Path(__file__).with_name("results.json")
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
