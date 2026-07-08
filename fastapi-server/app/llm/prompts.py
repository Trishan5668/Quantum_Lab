"""Shared prompt assembly for cloud-backed LLM providers.

Kept in its own module so the offline :class:`LocalProvider` can reuse
the same state-formatting helpers without depending on Gemini-specific
client wiring.
"""

from __future__ import annotations

from app.llm.base import ComplexAmplitude, ExplanationRequest


SYSTEM_PROMPT_BASE = (
    "You are QuantumLab's built-in tutor. Your audience is a 15-year-old "
    "with no prior quantum knowledge but strong curiosity.\n\n"
    "Rules:\n"
    "- Never use jargon without immediately defining it in plain English\n"
    "- Use vivid analogies from everyday life (coins, dice, radio waves, "
    "spinning tops)\n"
    "- Keep responses under 120 words\n"
    "- Always end with one \"wow fact\" - one mind-bending implication of "
    "what just happened\n"
    "- Format: one paragraph, no bullet points, no headers\n"
    "- Do NOT say \"As an AI\" or \"Great question\"\n"
    "- The explanation must reference the actual numerical values in the "
    "state (e.g., \"your qubit is now exactly 50/50\")"
)

DEEP_RIDER = (
    "\n\nThis is a 'deeper' request: you may use up to 300 words, but keep "
    "the tone friendly and analogy-driven."
)

HINT_RIDER = (
    "\n\nThis is a HINT request, not an explanation. The user is stuck on a "
    "mission. Nudge them toward the next correct gate WITHOUT spoiling the "
    "full solution. Stay under 60 words."
)

V2_TOPIC_RIDER = (
    "\n\nThe simulator now supports density-matrix mode, quantum noise "
    "(T1/T2 decoherence, depolarizing channels), fidelity metrics, and "
    "entanglement entropy. If the user asks about mixed states, decoherence, "
    "fidelity percentages, or von Neumann entropy, explain in plain language: "
    "T1 is energy decay (amplitude damping), T2 is loss of phase coherence, "
    "fidelity measures overlap with a target state, and entropy S=1 bit on one "
    "qubit of a Bell pair means maximal entanglement."
)


def system_prompt_for(req: ExplanationRequest) -> str:
    """Return the system prompt with mode-specific riders applied."""
    base = SYSTEM_PROMPT_BASE + V2_TOPIC_RIDER
    if req.mode == "deep":
        return base + DEEP_RIDER
    if req.mode == "hint":
        return base + HINT_RIDER
    return base


def format_state(amps: list[ComplexAmplitude], num_qubits: int) -> str:
    """Render only the non-negligible basis amplitudes as a compact string."""
    parts: list[str] = []
    for i, a in enumerate(amps):
        prob = a.real * a.real + a.imag * a.imag
        if prob > 1e-10:
            bits = format(i, f"0{num_qubits}b")
            parts.append(f"|{bits}> -> {a.real:+.3f}{a.imag:+.3f}i (P={prob:.3f})")
    return "; ".join(parts) if parts else "(empty)"


def user_message_for(req: ExplanationRequest) -> str:
    """Compose the user-turn message that grounds the LLM in real numbers."""
    if req.qubit is not None:
        qstr = f"q[{req.qubit}]"
    elif req.qubits:
        qstr = "q" + repr(req.qubits)
    else:
        qstr = "the register"
    before = format_state(req.state_before, req.num_qubits)
    after = format_state(req.state_after, req.num_qubits)
    return (
        f"Just applied {req.gate} to {qstr} in a {req.num_qubits}-qubit register. "
        f"State before: {before}. State after: {after}. "
        f"Context: {req.context}. "
        "Explain what just happened to a curious 15-year-old."
    )
