"""Wolfram-backed Research Mode verification.

QuantumLab remains the simulator. This package owns the independent
mathematical verification boundary used only by Research Mode.
"""

from app.wolfram.verification import verify_research_payload

__all__ = ["verify_research_payload"]
