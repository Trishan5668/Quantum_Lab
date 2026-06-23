# ==============================
# ADVANCED QUANTUM SIMULATOR
# M.Tech Level Upgrade (All Core Gates Added)
# ==============================

import numpy as np
import tkinter as tk
from collections import Counter
import json

def optimize_circuit(instructions):
    optimized: list[str] = []  
    for inst in instructions:
        if optimized and optimized[-1] == inst:
            continue
        optimized.append(inst)
    return optimized# -----------------------------
# BASIC GATES
# -----------------------------
I = np.eye(2, dtype=complex)
H = (1/np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)

# Rotation Gates

def RX(theta):
    return np.array([
        [np.cos(theta/2), -1j*np.sin(theta/2)],
        [-1j*np.sin(theta/2), np.cos(theta/2)]
    ], dtype=complex)

def RY(theta):
    return np.array([
        [np.cos(theta/2), -np.sin(theta/2)],
        [np.sin(theta/2), np.cos(theta/2)]
    ], dtype=complex)

def RZ(theta):
    return np.array([
        [np.exp(-1j*theta/2), 0],
        [0, np.exp(1j*theta/2)]
    ], dtype=complex)

# -----------------------------
# DENSITY MATRIX SIMULATOR
# -----------------------------
class QuantumSimulator:

    def __init__(self, n_qubits):
        self.n = n_qubits
        psi = np.zeros(2**n_qubits, dtype=complex)
        psi[0] = 1
        self.rho = np.outer(psi, psi.conj())

    # -----------------------------
    # SINGLE QUBIT GATE
    # -----------------------------
    def apply_gate(self, gate, qubit):
        op = np.array([[1.0]], dtype=complex)
        for i in range(self.n):
            op = np.kron(op, gate if i == qubit else I)
        # Note: Density matrix update uses conjugate transpose (hermitian adjoint)
        self.rho = op @ self.rho @ op.conj().T

    # -----------------------------
    # CNOT (CONTROLLED-X)
    # -----------------------------
    def apply_cnot(self, control, target):
        size = 2**self.n
        U = np.zeros((size, size), dtype=complex)

        for i in range(size):
            if ((i >> control) & 1):
                flipped = i ^ (1 << target)
                U[flipped][i] = 1
            else:
                U[i][i] = 1

        self.rho = U @ self.rho @ U.conj().T

    # -----------------------------
    # CZ (CONTROLLED-Z)
    # -----------------------------
    def apply_cz(self, control, target):
        size = 2**self.n
        U = np.eye(size, dtype=complex)

        for i in range(size):
            if ((i >> control) & 1) and ((i >> target) & 1):
                U[i][i] = -1

        self.rho = U @ self.rho @ U.conj().T

    # -----------------------------
    # REALISTIC NOISE (KRAUS)
    # -----------------------------
    def apply_depolarizing_noise(self, p=0.05):
        K0 = np.sqrt(1-p) * I
        K1 = np.sqrt(p/3) * X
        K2 = np.sqrt(p/3) * Y
        K3 = np.sqrt(p/3) * Z

        new_rho = np.zeros_like(self.rho)
        for K in [K0, K1, K2, K3]:
            op = np.array([[1.0]], dtype=complex)
            for _ in range(self.n):
                op = np.kron(op, K)
            new_rho += op @ self.rho @ op.conj().T

        self.rho = new_rho

    # -----------------------------
    # MEASUREMENT (SHOTS)
    # -----------------------------
    def measure(self, shots=1024):
        probs = np.real(np.diag(self.rho))
        probs = probs / np.sum(probs)
        outcomes = np.random.choice(len(probs), shots, p=probs)
        counts = Counter(outcomes)

        return {bin(k)[2:].zfill(self.n): int(v) for k, v in counts.items()}

# -----------------------------
# CIRCUIT OPTIMIZER
# -----------------------------
def optimize_circuit(instructions):
    optimized = []
    for inst in instructions:
        if optimized and optimized[-1] == inst:
            continue
        optimized.append(inst)
    return optimized

# -----------------------------
# CIRCUIT RUNNER
# -----------------------------
def run_circuit(sim, instructions):
    instructions = optimize_circuit(instructions)

    for inst in instructions:
        parts = inst.split()

        if parts[0] == "H":
            sim.apply_gate(H, int(parts[1]))

        elif parts[0] == "X":
            sim.apply_gate(X, int(parts[1]))

        elif parts[0] == "Y":
            sim.apply_gate(Y, int(parts[1]))

        elif parts[0] == "Z":
            sim.apply_gate(Z, int(parts[1]))

        elif parts[0] == "RX":
            sim.apply_gate(RX(float(parts[2])), int(parts[1]))

        elif parts[0] == "RY":
            sim.apply_gate(RY(float(parts[2])), int(parts[1]))

        elif parts[0] == "RZ":
            sim.apply_gate(RZ(float(parts[2])), int(parts[1]))

        elif parts[0] == "CNOT":
            sim.apply_cnot(int(parts[1]), int(parts[2]))

        elif parts[0] == "CZ":
            sim.apply_cz(int(parts[1]), int(parts[2]))

        elif parts[0] == "NOISE":
            sim.apply_depolarizing_noise(float(parts[1]))

# -----------------------------
# GUI (UPGRADED)
# -----------------------------
class QuantumGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Advanced Quantum Simulator")

        self.instructions = []

        tk.Button(self.root, text="H q0", command=lambda: self.add("H 0")).pack()
        tk.Button(self.root, text="X q0", command=lambda: self.add("X 0")).pack()
        tk.Button(self.root, text="Y q0", command=lambda: self.add("Y 0")).pack()
        tk.Button(self.root, text="Z q0", command=lambda: self.add("Z 0")).pack()
        tk.Button(self.root, text="CNOT 0→1", command=lambda: self.add("CNOT 0 1")).pack()
        tk.Button(self.root, text="CZ 0→1", command=lambda: self.add("CZ 0 1")).pack()
        tk.Button(self.root, text="RX q0 1.57", command=lambda: self.add("RX 0 1.57")).pack()

        self.text = tk.Text(self.root, height=12)
        self.text.pack()

        tk.Button(self.root, text="Run", command=self.run).pack()

    def add(self, cmd):
        self.instructions.append(cmd)
        self.text.insert(tk.END, cmd + "\n")

    def run(self):
        sim = QuantumSimulator(2)
        run_circuit(sim, self.instructions)
        results = sim.measure(1024)

        output = {
            "circuit": self.instructions,
            "results": results
        }
        print(json.dumps(output))  # 🔥 This is what Java reads

    def start(self):
        self.root.mainloop()

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    QuantumGUI().start()
    
    
class ThreeDCavity:

    def __init__(
        self,
        f_c=8.0035e9,   # cavity frequency (Hz)
        f_q=6.808e9,    # qubit frequency (Hz)
        g=138e6,        # coupling (Hz)
        T1=60e-6,       # seconds
        T2=18e-6
    ):

        self.fc = f_c
        self.fq = f_q

        self.wc = 2 * np.pi * f_c
        self.wq = 2 * np.pi * f_q
        self.g = 2 * np.pi * g

        self.delta = self.wc - self.wq

        if abs(self.delta) <= self.g:
            raise ValueError("Not in dispersive regime.")

        self.chi = self.g**2 / self.delta

        self.T1 = T1
        self.T2 = T2

        self.gamma1 = 1 / T1
        self.gamma_phi = max(
            0,
            1 / T2 - 1 / (2 * T1)
        )

    def cavity_shift(self):
        return self.chi / (2 * np.pi)

    def info(self):
        return {
            "f_c (GHz)": self.fc / 1e9,
            "f_q (GHz)": self.fq / 1e9,
            "g (MHz)": self.g / (2 * np.pi * 1e6),
            "delta (MHz)": self.delta / (2 * np.pi * 1e6),
            "chi (MHz)": self.chi / (2 * np.pi * 1e6),
            "T1 (us)": self.T1 * 1e6,
            "T2 (us)": self.T2 * 1e6
        }