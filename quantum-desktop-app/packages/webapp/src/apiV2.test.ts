import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchAIChat, type AIChatContextRequest } from "./apiV2";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchAIChat", () => {
  it("posts the deployed AI schema with lowercase learning mode and snake_case circuit fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      data: { answer: "The state starts as |0>.", model: "deepseek-ai/DeepSeek-V4-Flash" },
      error: null,
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const context: AIChatContextRequest = {
      learning_mode: "research",
      circuit: {
        num_qubits: 2,
        initial_basis_state: "00",
        gates: [{ id: "h-0", gate_type: "H", qubit_targets: [0], params: {}, time_step: 0, stack_count: 1 }],
      },
      simulation: { mode: "statevector", final_state: [], measurement_probabilities: [] },
      mathematics: {},
      physics: {},
      wolfram: { status: "PENDING", results: {} },
    };

    await fetchAIChat("Explain this circuit", context);

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      message: "Explain this circuit",
      context,
    });
  });
});
