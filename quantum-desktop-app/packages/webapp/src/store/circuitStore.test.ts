import { describe, expect, it, beforeEach } from "vitest";
import { useCircuitStore } from "./circuitStore";

describe("circuit store", () => {
  beforeEach(() => {
    useCircuitStore.getState().clearCircuit();
    useCircuitStore.getState().setNumQubits(1);
  });

  it("starts with 1 qubit and no gates", () => {
    const s = useCircuitStore.getState();
    expect(s.numQubits).toBe(1);
    expect(s.gates.length).toBe(0);
    expect(s.results).toBeNull();
  });

  it("adds qubits up to a maximum of 8", () => {
    const { addQubit } = useCircuitStore.getState();
    for (let i = 0; i < 12; i++) addQubit();
    expect(useCircuitStore.getState().numQubits).toBe(8);
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

  it("drops gates that target removed qubits when shrinking", () => {
    useCircuitStore.getState().setNumQubits(3);
    useCircuitStore.getState().addGate("H", [2], 0);
    useCircuitStore.getState().setNumQubits(2);
    expect(useCircuitStore.getState().gates).toHaveLength(0);
  });
});
