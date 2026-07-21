import { describe, expect, it, beforeEach, vi } from "vitest";
import { useCircuitStore, normalizeV2ToSimulationResult, selectCurrentState } from "./circuitStore";
import type { SimulationResultV2 } from "../types";
import { basisStateSnapshot } from "../utils/basisState";

describe("circuit store", () => {
  beforeEach(() => {
    useCircuitStore.getState().clearCircuit();
    useCircuitStore.getState().setNumQubits(1);
  });

  it("starts with 1 qubit and no gates", () => {
    const s = useCircuitStore.getState();
    expect(s.numQubits).toBe(1);
    expect(s.gates.length).toBe(0);
    expect(s.initialBasisState).toBe("0");
  });

  it("adds qubits up to a maximum of 8", () => {
    const { addQubit } = useCircuitStore.getState();
    for (let i = 0; i < 12; i++) addQubit();
    expect(useCircuitStore.getState().numQubits).toBe(8);
  });

  it("adds a qubit with the selected computational basis state", () => {
    useCircuitStore.getState().addQubitWithBasisState("10");
    const s = useCircuitStore.getState();
    const snapshot = selectCurrentState(s);
    expect(s.numQubits).toBe(2);
    expect(s.initialBasisState).toBe("10");
    expect(snapshot?.amplitudes.map((a) => a.real)).toEqual([0, 0, 1, 0]);
    expect(snapshot?.probabilities).toEqual([0, 0, 1, 0]);
  });

  it("maps a selected 3-qubit basis state to the matching big-endian index", () => {
    useCircuitStore.getState().setNumQubits(3);
    useCircuitStore.getState().setInitialBasisState("101");
    const snapshot = selectCurrentState(useCircuitStore.getState());
    expect(snapshot?.amplitudes.map((a) => a.real)).toEqual([0, 0, 0, 0, 0, 1, 0, 0]);
  });

  it("maps selected basis states to the matching index for 1 through 5 qubits", () => {
    for (let n = 1; n <= 5; n += 1) {
      const basis = `${"1"}${"0".repeat(Math.max(0, n - 2))}${n > 1 ? "1" : ""}`.slice(0, n);
      const snapshot = basisStateSnapshot(n, basis);
      const expectedIndex = Number.parseInt(basis, 2);
      expect(snapshot.amplitudes[expectedIndex].real).toBe(1);
      expect(snapshot.probabilities[expectedIndex]).toBe(1);
      expect(snapshot.amplitudes.filter((amp) => amp.real === 1)).toHaveLength(1);
    }
  });

  it("changes the initial basis state without removing existing gates", () => {
    useCircuitStore.getState().setNumQubits(3);
    useCircuitStore.getState().addGate("H", [0], 0);
    useCircuitStore.getState().setInitialBasisState("101");
    let state = useCircuitStore.getState();
    expect(state.gates).toHaveLength(1);
    expect(state.initialBasisState).toBe("101");
    expect(state.results?.steps).toHaveLength(0);
    expect(state.results?.final_state.probabilities).toEqual([0, 0, 0, 0, 0, 1, 0, 0]);

    useCircuitStore.getState().resetInitialBasisState();
    state = useCircuitStore.getState();
    expect(state.gates).toHaveLength(1);
    expect(state.initialBasisState).toBe("000");
    expect(state.results?.final_state.probabilities).toEqual([1, 0, 0, 0, 0, 0, 0, 0]);

    const randomSpy = vi.spyOn(Math, "random").mockReturnValue(5 / 8);
    useCircuitStore.getState().randomizeInitialBasisState();
    randomSpy.mockRestore();
    state = useCircuitStore.getState();
    expect(state.gates).toHaveLength(1);
    expect(state.initialBasisState).toBe("101");
    expect(state.results?.final_state.probabilities).toEqual([0, 0, 0, 0, 0, 1, 0, 0]);
  });

  it("places single-qubit gates at the given time step", () => {
    useCircuitStore.getState().addGate("H", [0], 2);
    const gates = useCircuitStore.getState().gates;
    expect(gates).toHaveLength(1);
    expect(gates[0].gateType).toBe("H");
    expect(gates[0].timeStep).toBe(2);
  });

  it("removes a gate by id", () => {
    useCircuitStore.getState().addGate("X", [0], 0);
    const id = useCircuitStore.getState().gates[0].id;
    useCircuitStore.getState().removeGate(id);
    expect(useCircuitStore.getState().gates).toHaveLength(0);
  });

  it("rejects gate placements with out-of-range qubits", () => {
    useCircuitStore.getState().addGate("H", [99], 0);
    expect(useCircuitStore.getState().gates).toHaveLength(0);
  });

  it("defaults simulation to statevector with noise off", () => {
    const s = useCircuitStore.getState();
    expect(s.simulationMode).toBe("statevector");
    expect(s.noiseEnabled).toBe(false);
  });

  it("updates simulation mode", () => {
    useCircuitStore.getState().setSimulationMode("density");
    expect(useCircuitStore.getState().simulationMode).toBe("density");
  });

  it("normalizes v2 density steps to state_after snapshots", () => {
    const v2 = {
      num_qubits: 1,
      execution_time_ms: 1,
      simulation_mode: "density" as const,
      steps: [
        {
          gate_id: "g0",
          gate_type: "H",
          qubit_targets: [0],
          params: {},
          time_step: 0,
          density_after: {
            num_qubits: 1,
            dim: 2,
            real: [[0.5, 0.5], [0.5, 0.5]],
            imag: [[0, 0], [0, 0]],
            probabilities: [0.5, 0.5],
            purity: 1,
            basis_labels: ["|0>", "|1>"],
            amplitudes: [
              { real: 0.7071, imag: 0 },
              { real: 0.7071, imag: 0 },
            ],
          },
          probabilities: [0.5, 0.5],
          purity: 1,
        },
      ],
      final_state: {
        num_qubits: 1,
        amplitudes: [
          { real: 0.7071, imag: 0 },
          { real: 0.7071, imag: 0 },
        ],
        probabilities: [0.5, 0.5],
        basis_labels: ["|0>", "|1>"],
      },
    } as unknown as SimulationResultV2;
    const mapped = normalizeV2ToSimulationResult(v2);
    expect(mapped.steps[0].state_after.amplitudes).toHaveLength(2);
    expect(mapped.steps[0].state_after.probabilities).toEqual([0.5, 0.5]);
  });
});
