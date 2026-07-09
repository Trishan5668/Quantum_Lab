#!/usr/bin/env python3
"""Generate QuantumLab Mathematical Foundations PDF from markdown source."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "QuantumLab_Mathematical_Foundations.md"
OUTPUT = ROOT / "docs" / "QuantumLab_Mathematical_Foundations.pdf"


class FoundationsPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "QuantumLab Mathematical Foundations", align="R")
        self.ln(10)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def chapter_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 30, 60)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 10, title)
        self.ln(2)

    def section_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(50, 50, 80)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 8, title)
        self.ln(1)

    def body_text(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.set_text_color(20, 20, 20)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 5.5, text)
        self.ln(2)

    def code_block(self, text: str) -> None:
        self.set_font("Courier", "", 9)
        self.set_fill_color(245, 245, 250)
        self.set_text_color(30, 30, 30)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 5, text, fill=True)
        self.ln(3)


def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("⟨", "<").replace("⟩", ">")
    text = text.replace("†", "+").replace("⊗", "x")
    text = text.replace("√", "sqrt").replace("ρ", "rho").replace("ψ", "psi")
    text = text.replace("φ", "phi").replace("θ", "theta").replace("γ", "gamma")
    text = text.replace("Σ", "Sum").replace("λ", "lambda").replace("ᵢ", "i")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def build_pdf(source: Path, output: Path) -> None:
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        sys.exit(1)

    pdf = FoundationsPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 20, 50)
    pdf.cell(0, 12, "QuantumLab", ln=True)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "Mathematical Foundations", ln=True)
    pdf.ln(4)
    pdf.body_text(
        "A rigorous reference for the mathematics implemented in the "
        "QuantumLab open-source quantum simulator. Version 2.0.0."
    )

    content = source.read_text(encoding="utf-8")
    in_code = False
    code_buf: list[str] = []

    for line in content.splitlines():
        if line.startswith("```"):
            if in_code:
                pdf.code_block(_strip_md("\n".join(code_buf)))
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue
        if line.startswith("# "):
            pdf.add_page()
            pdf.chapter_title(_strip_md(line[2:].strip()))
        elif line.startswith("## "):
            pdf.ln(2)
            pdf.section_title(_strip_md(line[3:].strip()))
        elif line.startswith("### "):
            pdf.section_title(_strip_md(line[4:].strip()))
        elif line.strip().startswith("|") or not line.strip():
            continue
        elif line.strip().startswith("- "):
            pdf.body_text("  * " + _strip_md(line.strip()[2:]))
        else:
            pdf.body_text(_strip_md(line.strip()))

    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))
    print(f"Wrote {output}")


if __name__ == "__main__":
    build_pdf(SOURCE, OUTPUT)
