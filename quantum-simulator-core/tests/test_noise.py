from __future__ import annotations

import numpy as np
import pytest

from quantumlab.density import DensityMatrix
from quantumlab.gates import X
from quantumlab.noise import (
    AmplitudeDampingChannel,
    BitFlipChannel,
    DepolarizingChannel,
    NoiseConfig,
    PhaseDampingChannel,
    PhaseFlipChannel,
    T1T2NoiseModel,
    apply_noise,
    build_channel,
)
from quantumlab.state import StateVector


def _one_state() -> DensityMatrix:
    sv = StateVector.from_amplitudes(np.array([0.0, 1.0], dtype=np.complex128))
    return DensityMatrix.from_statevector(sv)


def test_amplitude_damping_p1_gives_zero() -> None:
    rho = _one_state()
    channel = AmplitudeDampingChannel(1.0)
    out = channel.apply(rho, 0)
    assert out.probabilities()[0] == pytest.approx(1.0, abs=1e-10)
    assert out.probabilities()[1] == pytest.approx(0.0, abs=1e-10)


def test_depolarizing_high_p_reduces_purity() -> None:
    rho = DensityMatrix.from_statevector(StateVector.zero(1))
    channel = DepolarizingChannel(1.0)
    out = channel.apply(rho, 0)
    assert out.purity() < 1.0
    assert float(np.real(np.trace(out.matrix))) == pytest.approx(1.0, abs=1e-10)


def test_bit_flip_p1_applies_x() -> None:
    rho = DensityMatrix.from_statevector(StateVector.zero(1))
    channel = BitFlipChannel(1.0)
    out = channel.apply(rho, 0)
    expected = DensityMatrix.from_statevector(
        StateVector.zero(1).apply_gate(X(), [0])
    )
    assert np.allclose(out.matrix, expected.matrix, atol=1e-10)


def test_phase_flip_preserves_diagonal() -> None:
    sv = StateVector.from_amplitudes(
        np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
    )
    rho = DensityMatrix.from_statevector(sv)
    channel = PhaseFlipChannel(0.5)
    out = channel.apply(rho, 0)
    assert np.allclose(np.diag(out.matrix), np.diag(rho.matrix), atol=1e-10)


def test_channels_preserve_trace() -> None:
    rho = _one_state()
    for channel in [
        AmplitudeDampingChannel(0.3),
        PhaseDampingChannel(0.2),
        DepolarizingChannel(0.1),
        BitFlipChannel(0.15),
        PhaseFlipChannel(0.15),
    ]:
        out = channel.apply(rho, 0)
        assert float(np.real(np.trace(out.matrix))) == pytest.approx(1.0, abs=1e-10)


def test_t1_t2_reduces_purity() -> None:
    sv = StateVector.from_amplitudes(
        np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
    )
    rho = DensityMatrix.from_statevector(sv)
    channel = T1T2NoiseModel(t1_us=50.0, t2_us=25.0, gate_time_ns=1000.0)
    out = channel.apply(rho, 0)
    assert out.purity() < 1.0


def test_build_channel_from_config() -> None:
    cfg = NoiseConfig(enabled=True, channel="depolarizing", probability=0.05)
    channel = build_channel(cfg)
    assert isinstance(channel, DepolarizingChannel)


def test_apply_noise_all_qubits() -> None:
    rho = DensityMatrix.from_statevector(StateVector.zero(2))
    channel = DepolarizingChannel(0.0)
    out = apply_noise(rho, channel, wires=None)
    assert out.purity() == pytest.approx(1.0, abs=1e-10)
