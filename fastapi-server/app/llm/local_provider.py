"""Deterministic offline ELI15 explanations.

Used when ``LLM_PROVIDER=local`` is set, or when ``GEMINI_API_KEY`` is
absent. Every explanation is generated from a small template library
grounded in the actual numerical state, so the output is always
reproducible and never hits an external API.

Hard constraints:

* Total word count is kept under 120 words (verified by tests).
* All nine standard gate ids -- ``H``, ``X``, ``Y``, ``Z``, ``RX``,
  ``RY``, ``RZ``, ``CNOT`` and the measurement pseudo-gate ``M`` --
  receive a tailored explanation. Anything else gets a safe generic
  fallback.
* Tokens are streamed one whitespace-delimited word at a time so the
  SSE contract from the cloud provider is preserved.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.llm.base import (
    ComplexAmplitude,
    ExplanationProvider,
    ExplanationRequest,
)


_MAX_WORDS = 119
"""Tight upper bound; the spec requires strictly under 120 words."""


def _qubit_label(req: ExplanationRequest) -> str:
    if req.qubit is not None:
        return f"qubit {req.qubit}"
    if req.qubits:
        return "qubits " + ", ".join(str(q) for q in req.qubits)
    return "the register"


def _dominant_basis(amps: list[ComplexAmplitude], num_qubits: int) -> str:
    best_idx = 0
    best_p = -1.0
    for i, a in enumerate(amps):
        p = a.real * a.real + a.imag * a.imag
        if p > best_p:
            best_p = p
            best_idx = i
    return format(best_idx, f"0{num_qubits}b")


def _probability_summary(amps: list[ComplexAmplitude], num_qubits: int) -> str:
    pairs: list[tuple[str, float]] = []
    for i, a in enumerate(amps):
        p = a.real * a.real + a.imag * a.imag
        if p > 1e-6:
            pairs.append((format(i, f"0{num_qubits}b"), p))
    pairs.sort(key=lambda kv: -kv[1])
    pairs = pairs[:4]
    return ", ".join(f"|{b}>={p*100:.0f}%" for b, p in pairs) or "no significant outcomes"


def _is_superposition(amps: list[ComplexAmplitude]) -> bool:
    nonzero = sum(1 for a in amps if (a.real * a.real + a.imag * a.imag) > 1e-6)
    return nonzero >= 2


def _build_explanation(req: ExplanationRequest) -> str:
    gate = req.gate.upper()
    q = _qubit_label(req)
    after_summary = _probability_summary(req.state_after, req.num_qubits)
    dominant_after = _dominant_basis(req.state_after, req.num_qubits)

    if gate == "H":
        if _is_superposition(req.state_after):
            return (
                f"The Hadamard gate just flipped {q} into perfect superposition. "
                "Think of a coin spinning in mid-air: it's not heads or tails, "
                "it's genuinely both at once. The numbers confirm it: "
                f"{after_summary}. "
                "Wow fact: until you peek, that qubit doesn't have a definite "
                "value -- nature itself has not decided yet."
            )
        return (
            f"H normally creates a 50/50 superposition on {q}, but applied to "
            "the current state it cancelled back to a single outcome: "
            f"|{dominant_after}>. "
            "That's quantum interference -- like two waves crashing into each "
            "other and going flat. "
            "Wow fact: H is its own undo button -- apply it twice and you're back."
        )

    if gate == "X":
        return (
            f"The X gate is the quantum NOT: it flipped {q} from 0 to 1 (or vice "
            f"versa). After the flip the state is dominated by |{dominant_after}>. "
            "Think of turning a light switch upside down. "
            "Wow fact: on a qubit already in superposition, X swaps the |0> and "
            "|1> parts, like reading a page in a mirror."
        )

    if gate == "Y":
        return (
            f"The Y gate flipped {q} like X does, but it also painted in an "
            "imaginary phase -- a kind of invisible spin direction. Outcomes now "
            f"sit at {after_summary}. "
            "Imagine spinning a top, then giving it a sideways nudge so it "
            "wobbles too. "
            "Wow fact: that imaginary phase is invisible to your eyes but rules "
            "everything when this qubit later interferes with another."
        )

    if gate == "Z":
        return (
            f"The Z gate didn't change which outcomes are possible for {q} -- "
            "probabilities look the same. It secretly added a minus sign to "
            "the |1> branch. "
            "Imagine two singers in tune, then one shifts half a beat: nothing "
            "obvious until they meet. "
            "Wow fact: that hidden flip rewrites how this qubit interferes "
            "later, even though right now you cannot tell."
        )

    if gate == "RX":
        return (
            f"RX rotated {q} around the X axis of its Bloch sphere -- think of "
            "tilting a spinning top sideways by a precise angle. The new "
            f"probability mix is {after_summary}. "
            "Bigger angle, bigger flip. "
            "Wow fact: this gate is continuous -- not a yes/no switch but a "
            "smooth dial, which is why quantum hardware lives or dies on its "
            "precision."
        )

    if gate == "RY":
        return (
            f"RY tilted {q} around the Y axis. Unlike RZ it actually changes "
            f"the chances of 0 vs 1 -- you can now see {after_summary}. "
            "Picture pushing a swing forward by a precise angle. "
            "Wow fact: RY can take a definite 0 and gradually morph it into a "
            "definite 1, passing through every superposition in between."
        )

    if gate == "RZ":
        return (
            f"RZ spun {q} around the Z axis. Look at the probabilities -- they "
            "barely moved -- but the phase between |0> and |1> shifted. "
            "Imagine two synchronized swimmers staying in their lanes while one "
            "rotates underwater. "
            "Wow fact: this invisible-looking rotation is what lets quantum "
            "computers cancel wrong answers and amplify right ones."
        )

    if gate == "CNOT":
        return (
            f"CNOT just entangled {q}: the control decides whether the target "
            f"flips. The joint state now reads {after_summary}. "
            "If those probabilities are split across multiple basis states, the "
            "qubits are now linked -- measuring one instantly tells you the other. "
            "Wow fact: Einstein called this 'spooky action at a distance.'"
        )

    if gate == "M":
        return (
            f"You just measured {q}. The wavefunction collapsed -- the dice "
            f"stopped rolling and chose {dominant_after}. From this point on "
            "that qubit behaves like ordinary classical information. "
            "Wow fact: the measurement itself is irreversible. The other "
            "possibilities didn't fade out, they vanished entirely from "
            "your branch of reality."
        )

    return (
        f"The {gate} gate acted on {q}. Probabilities shifted to "
        f"{after_summary}. Think of it as a precise nudge that reshapes the "
        "cloud of possible outcomes. "
        "Wow fact: every quantum gate is reversible -- given the new state "
        "you could in principle recover the old one."
    )


def _truncate(words: list[str], limit: int) -> list[str]:
    if len(words) <= limit:
        return words
    return words[:limit]


class LocalProvider(ExplanationProvider):
    """Generates concise (<120-word) deterministic explanations offline."""

    async def stream_explanation(
        self,
        request: ExplanationRequest,
    ) -> AsyncIterator[str]:
        text = _build_explanation(request)
        words = _truncate(text.split(), _MAX_WORDS)
        for i, word in enumerate(words):
            yield word if i == 0 else f" {word}"
            # Tiny yield so other tasks (heartbeats, client cancellation) get
            # a chance; keeps the stream feeling token-paced without blocking
            # the event loop.
            await asyncio.sleep(0)
