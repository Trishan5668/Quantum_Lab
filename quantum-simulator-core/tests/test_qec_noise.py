from __future__ import annotations

import math

import numpy as np
import pytest

from quantumlab.noise import (
    AmplitudeDampingChannel,
    BitFlipChannel,
    DepolarizingChannel,
    PhaseDampingChannel,
    PhaseFlipChannel,
    T1T2NoiseModel,
)
from quantumlab.research.qec.noise import (
    CircuitLevelNoiseModel,
    MeasurementErrorModel,
    NoiseModelError,
    PauliChannel,
    PhenomenologicalNoiseModel,
    biased_pauli,
    bit_flip,
    choi_matrix,
    cptp_report,
    depolarizing,
    kraus_completeness_error,
    noise_model_from_dict,
    require_supported_noise,
    validate_cptp,
)
from quantumlab.research.qec.pauli import Pauli


def test_depolarizing_convention_and_identity() -> None:
    channel = depolarizing(0.3)
    assert channel.p_x == pytest.approx(0.1)
    assert channel.p_y == pytest.approx(0.1)
    assert channel.p_z == pytest.approx(0.1)
    assert channel.p_identity == pytest.approx(0.7)
    assert sum(channel.probabilities) == pytest.approx(1.0)
    assert depolarizing(0.0).p_identity == 1.0
    assert depolarizing(1.0).p_identity == 0.0


def test_biased_channel_probabilities() -> None:
    channel = biased_pauli(0.2, 0.1, 0.3)
    assert channel.probabilities == pytest.approx((0.4, 0.2, 0.3, 0.1))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"p_x": -0.1},
        {"p_x": 0.5, "p_y": 0.5, "p_z": 0.5},
        {"p_x": float("nan")},
        {"p_x": float("inf")},
        {"p_y": "0.1"},
        {"p_z": True},
    ],
)
def test_invalid_pauli_channel_parameters(kwargs) -> None:
    with pytest.raises(NoiseModelError):
        PauliChannel(**kwargs)


def test_measurement_error_validation_and_sampling() -> None:
    with pytest.raises(NoiseModelError):
        MeasurementErrorModel(-0.1)
    with pytest.raises(NoiseModelError):
        MeasurementErrorModel(1.1)
    model = MeasurementErrorModel(1.0)
    bits = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    flipped = model.flips(bits, np.random.default_rng(0))
    assert np.array_equal(flipped, 1 - bits)
    with pytest.raises(NoiseModelError):
        model.flips(np.array([2]), np.random.default_rng(0))


def test_sampling_matches_declared_probabilities() -> None:
    channel = biased_pauli(0.2, 0.1, 0.3)
    rng = np.random.default_rng(20261019)
    shots = 200_000
    codes = channel.sample_labels(rng, (shots,))
    counts = np.bincount(codes, minlength=4) / shots
    expected = np.array(channel.probabilities)
    sigma = np.sqrt(expected * (1.0 - expected) / shots)
    assert np.all(np.abs(counts - expected) < 6.0 * sigma)


def test_zero_noise_returns_identity() -> None:
    rng = np.random.default_rng(1)
    channel = PauliChannel()
    for _ in range(100):
        assert channel.sample_pauli(rng, 5).is_identity()
    assert channel.sample_labels(rng, (100, 3)).sum() == 0


def test_log_probability_matches_product() -> None:
    channel = biased_pauli(0.2, 0.1, 0.3)
    pauli = Pauli.from_string("XYZI")
    expected = math.log(0.2) + math.log(0.1) + math.log(0.3) + math.log(0.4)
    assert channel.log_probability(pauli) == pytest.approx(expected, rel=1e-12)
    impossible = Pauli.from_string("XXXX")
    zero_channel = bit_flip(0.0)
    assert zero_channel.log_probability(impossible) == -math.inf


@pytest.mark.parametrize(
    "channel",
    [
        AmplitudeDampingChannel(0.1),
        PhaseDampingChannel(0.2),
        DepolarizingChannel(0.3),
        BitFlipChannel(0.2),
        PhaseFlipChannel(0.2),
        T1T2NoiseModel(50.0, 25.0, 1000.0),
    ],
)
def test_core_channels_are_cptp(channel) -> None:
    report = cptp_report(channel.kraus_operators())
    assert report["trace_preserving"]
    assert report["completely_positive"]
    assert report["cptp"]
    assert report["completeness_error"] < 1e-10
    assert report["choi_trace"] == pytest.approx(2.0, rel=1e-12)
    validate_cptp(channel.kraus_operators())


def test_choi_matrix_of_identity_is_rank_one() -> None:
    choi = choi_matrix([np.eye(2, dtype=np.complex128)])
    assert np.linalg.matrix_rank(choi) == 1
    assert np.trace(choi) == pytest.approx(2.0)
    assert kraus_completeness_error([np.eye(2, dtype=np.complex128)]) == pytest.approx(0.0)


def test_non_cptp_map_is_rejected() -> None:
    # A non-trace-preserving, non-CP "map" must not pass validation.
    bad = [np.array([[1.0, 0.0], [0.0, 1.5]], dtype=np.complex128)]
    with pytest.raises(NoiseModelError):
        validate_cptp(bad)


def test_phenomenological_model_metadata_is_explicit() -> None:
    model = PhenomenologicalNoiseModel(
        data_channel=depolarizing(0.01), measurement_error=0.02, rounds=3
    )
    metadata = model.to_dict()
    assert metadata["kind"] == "phenomenological"
    assert metadata["gate_error"] is False
    assert metadata["leakage"] is False
    assert metadata["correlated"] is False
    assert metadata["measurement_error"] == 0.02
    require_supported_noise(model)
    with pytest.raises(NoiseModelError):
        PhenomenologicalNoiseModel(depolarizing(0.1), measurement_error=-0.1, rounds=1)
    with pytest.raises(NoiseModelError):
        PhenomenologicalNoiseModel(depolarizing(0.1), rounds=0)


def test_circuit_level_model_metadata_and_validation() -> None:
    model = CircuitLevelNoiseModel.uniform(0.001)
    metadata = model.to_dict()
    assert metadata["kind"] == "circuit_level"
    assert metadata["executor"] == "stim"
    assert metadata["native_sampling"] is False
    assert metadata["leakage"] is False
    with pytest.raises(NoiseModelError):
        CircuitLevelNoiseModel(-0.1, 0.1, 0.1, 0.1)
    with pytest.raises(NoiseModelError):
        CircuitLevelNoiseModel(0.1, 0.1, 0.1, 0.1).stim_circuit(1, 1)


def test_circuit_level_stim_circuit_if_available() -> None:
    pytest.importorskip("stim")
    circuit = CircuitLevelNoiseModel.uniform(0.001).stim_circuit(3, 3)
    assert circuit.num_detectors > 0
    assert circuit.num_observables >= 1


def test_unsupported_noise_object_is_rejected() -> None:
    with pytest.raises(NoiseModelError):
        require_supported_noise(object())


def test_noise_model_from_dict_round_trip() -> None:
    model = noise_model_from_dict({"model": "depolarizing", "p": 0.03})
    assert isinstance(model, PauliChannel)
    assert model.p_x == pytest.approx(0.01)
    phenomenological = noise_model_from_dict(
        {
            "model": "phenomenological",
            "data_channel": {"model": "bit_flip", "p": 0.02},
            "measurement_error": 0.01,
            "rounds": 2,
        }
    )
    assert isinstance(phenomenological, PhenomenologicalNoiseModel)
    assert phenomenological.data_channel.p_x == pytest.approx(0.02)
    circuit = noise_model_from_dict(
        {"model": "circuit_level", "p_gate": 0.001, "p_measurement": 0.002}
    )
    assert isinstance(circuit, CircuitLevelNoiseModel)
    with pytest.raises(NoiseModelError):
        noise_model_from_dict({"model": "leakage"})
