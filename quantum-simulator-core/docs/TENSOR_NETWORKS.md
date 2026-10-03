# Tensor-network backend

QuantumLab's `mps` backend is a NumPy implementation of open-boundary,
pure-state matrix product states. Tensors have the explicit shape
`(left_bond, physical_dimension, right_bond)` and use the same big-endian
site order as the statevector engine.

Implemented operations are product/basis and statevector conversion,
left/right/mixed canonicalization, one- and two-qubit unitary gates, swap
routing for non-neighbour gates, SVD truncation, local reduced density
matrices, Pauli-string expectations, Schmidt/Renyi entropy, collapsed Born
sampling, and resource/truncation metadata. The API accepts `simulation_backend:
"mps"` and returns `tensor_network` metadata without materializing a statevector
above 12 qubits.

`max_bond_dimension` and `truncation_cutoff` control approximation. Every split
records discarded squared singular-value weight; the API reports its cumulative
sum, so an approximate result is never presented as exact.

Current limitations: this is a pure-state backend, so noise channels, density
MPOs, TEBD, DMRG, VQE, PEPS, and GPU acceleration are intentionally unavailable.
The frontend selector exposes MPS for the existing editor's eight-qubit canvas;
the API supports up to 256 MPS sites for programmatic low-entanglement circuits.
