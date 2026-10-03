"""NumPy tensor-network backend.

The initial public implementation is a pure-state, open-boundary MPS engine.
It deliberately does not claim mixed-state MPO, PEPS, or DMRG support.
"""

from quantumlab.tensor_networks.mps import MPS, MPSConfig, TruncationEvent

__all__ = ["MPS", "MPSConfig", "TruncationEvent"]
