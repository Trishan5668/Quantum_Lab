# QuantumLab Mathematical Foundations

## Chapter 1: Linear Algebra Foundations

### Complex vectors
An n-qubit pure state is a unit vector |ψ⟩ ∈ ℂ^(2^n). QuantumLab stores amplitudes as `numpy.complex128` arrays of shape `(2^n,)`.

### Inner product
⟨φ|ψ⟩ = Σᵢ φᵢ* ψᵢ. Normalization requires ⟨ψ|ψ⟩ = 1 (tolerance 1e−9).

### Outer product
|ψ⟩⟨φ| is a rank-1 operator. For pure states, ρ = |ψ⟩⟨ψ|.

### Tensor product
For single-qubit gates U on wire q of an n-qubit register:
U_full = G₀ ⊗ G₁ ⊗ … ⊗ G_{n−1} where Gᵢ = U if i = q, else I.

QuantumLab builds this via `numpy.kron` in `_operators.py`.

### Unitary matrices
A gate U satisfies U†U = I. Validated by `assert_valid_gate` with tolerance 1e−10.

---

## Chapter 2: Qubits and Measurement

### Computational basis
Big-endian convention: q[0] is the most significant bit.
```
|00⟩ index 0,  |01⟩ index 1,  |10⟩ index 2,  |11⟩ index 3
```

### Bloch sphere
Single-qubit pure states map to (θ, φ) via reduced density matrix:
ρ = (I + xX + yY + zZ)/2,  (x,y,z) = (sinθ cosφ, sinθ sinφ, cosθ).

### Born rule
Measurement probability of basis state |i⟩ is pᵢ = |aᵢ|² for pure states, or pᵢ = ρᵢᵢ for density matrices.

### Measurement in QuantumLab
The M gate is a visualization marker — it does not collapse the state. Probabilities are always computed from the full post-circuit state.

---

## Chapter 3: Gate Mathematics

### Pauli gates
```
X = [[0,1],[1,0]]     Y = [[0,-i],[i,0]]     Z = [[1,0],[0,-1]]
```

### Hadamard
```
H = (1/√2) [[1, 1], [1, -1]]
```
Maps |0⟩ → (|0⟩+|1⟩)/√2.

### Rotations (Qiskit convention)
```
RX(θ) = exp(-iθ/2 X)    RY(θ) = exp(-iθ/2 Y)    RZ(θ) = exp(-iθ/2 Z)
```

### CNOT
On |c,t⟩: CNOT|c,t⟩ = |c, c⊕t⟩.
```
CNOT = [[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]]
```

---

## Chapter 4: Tensor Products and Embedding

### Single-qubit embedding
Gate H on qubit 0 of 2-qubit system:
```
H_full = H ⊗ I    (big-endian: q[0] is left factor)
```

Gate H on qubit 1:
```
H_full = I ⊗ H
```

### Non-adjacent two-qubit gates
A 4×4 gate on wires (q₀, q₁) is embedded via SWAP permutation:
```
U_full = P† · (U ⊗ I ⊗ … ⊗ I) · P
```
where P routes wires q₀, q₁ to positions 0, 1.

---

## Chapter 5: Controlled Gates

### Projector formalism
```
C_U = |0⟩⟨0| ⊗ I + |1⟩⟨1| ⊗ U
```

### CNOT truth table
| Input | Output |
|-------|--------|
| |00⟩ | |00⟩ |
| |01⟩ | |01⟩ |
| |10⟩ | |11⟩ |
| |11⟩ | |10⟩ |

### Bell state construction
H on qubit 0, then CNOT(0,1):
```
|00⟩ → (|00⟩+|10⟩)/√2 → (|00⟩+|11⟩)/√2 = |Φ⁺⟩
```

---

## Chapter 6: Density Matrix Formalism

### Definition
ρ = Σᵢ pᵢ |ψᵢ⟩⟨ψᵢ| with Tr(ρ) = 1, ρ = ρ†, ρ ≥ 0.

### Evolution
ρ' = U ρ U† for unitary U.

### Partial trace
ρ_A = Tr_B(ρ_AB). QuantumLab traces out qubits not in `keep_qubits` (sorted ascending).

### Purity
P = Tr(ρ²). P = 1 for pure states; P < 1 for mixed states.

### Entanglement entropy
S(ρ_A) = −Tr(ρ_A log₂ ρ_A) in bits. Bell state: S = 1.

---

## Chapter 7: Noise and Kraus Operators

### CPTP maps
ρ' = Σᵢ Kᵢ ρ Kᵢ† with Σᵢ Kᵢ†Kᵢ = I.

### Amplitude damping (T1-like)
```
K₀ = [[1,0],[0,√(1-p)]],  K₁ = [[0,√p],[0,0]]
```

### Phase damping (T2-like)
```
K₀ = diag(1, √(1-γ)),  K₁ = diag(0, √γ)
```
Off-diagonals scale by √(1−γ). For Ramsey T2: γ = 1 − exp(−2t/T2).

### Depolarizing
```
K₀ = √(1-p) I,  K₁ = √(p/3) X,  K₂ = √(p/3) Y,  K₃ = √(p/3) Z
```

---

## Chapter 8: Quantum Algorithms

### Bell state
Circuit: H(0), CNOT(0,1). Probabilities: [0.5, 0, 0, 0.5].

### GHZ (3 qubit)
H(0), CNOT(0,1), CNOT(1,2). Probabilities: 0.5 at |000⟩ and |111⟩.

### Deutsch algorithm
Determines if f:{0,1}→{0,1} is constant or balanced in one query.

### Deutsch–Jozsa
Generalizes to n-bit functions; constant functions yield |0…0⟩.

### Bernstein–Vazirani
Recovers hidden bit string s from f(x) = s·x mod 2.

### Grover search
Amplitude amplification; one iteration on 2 qubits boosts marked state probability.

### Quantum Fourier Transform
Basis change |j⟩ → (1/√N) Σₖ e^(2πijk/N)|k⟩. Built from H and controlled RZ gates.

---

## Chapter 9: Verification Against Qiskit

### Methodology
1. Build identical circuit in QuantumLab and Qiskit
2. Apply wire remap: q_qiskit = n − 1 − q_qlab (endianness alignment)
3. Compare statevectors with atol = 1e−10 (global phase ignored)
4. Compare probabilities, fidelity, and entropy independently

### Test suite
150 pytest tests in `quantum-simulator-core/tests/` including:
- `test_math_validation.py` — unitarity, dimensions, Born rule, Kraus completeness
- `test_qiskit_reference.py` — algorithm cross-validation

### Bug fixed in this sprint
T2 phase damping: corrected γ mapping so coherence decays as exp(−t/T2), not exp(−t/(2T2)).

### Running validation
```
pip install -e "quantum-simulator-core[validation]"
pytest quantum-simulator-core/tests/ -v
python quantum-simulator-core/scripts/generate_math_pdf.py
```

---

*QuantumLab v2.0.0 — MIT License. This document accompanies the mathematical audit report.*
