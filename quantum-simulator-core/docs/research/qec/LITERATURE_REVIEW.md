# QEC literature review

**Status:** scoped, non-exhaustive review; no novelty claim is established.

The initial protocol is a reproduction-oriented engineering benchmark for a
standard repetition-code decoder. It is not presented as a new QEC method.
The review should be expanded before any surface-code or adaptive-decoding
claim is made.

## Closest foundations

- D. Gottesman, *Stabilizer Codes and Quantum Error Correction*, PhD thesis,
  Caltech (1997), arXiv:quant-ph/9705052. Establishes the stabilizer framework
  used by the code representation.
- E. Dennis, A. Kitaev, A. Landahl, and J. Preskill, “Topological quantum
  memory,” Journal of Mathematical Physics 43, 4452 (2002),
  DOI: 10.1063/1.1499754. Provides the surface-code and threshold context
  that this increment does not implement.
- A. G. Fowler et al., “Surface codes: Towards practical large-scale quantum
  computation,” Physical Review A 86, 032324 (2012),
  DOI: 10.1103/PhysRevA.86.032324. Describes circuit-level surface-code
  considerations and minimum-weight matching decoding.

## Search record and limits

The search terms for the next review pass are “surface code minimum weight
perfect matching decoder”, “noise-aware quantum error correction decoder”,
“adaptive quantum error correction”, “logical error rate benchmarking”, and
“resource-aware decoder selection”. Search date: 2026-10-19. This document
does not claim exhaustive database coverage or independent external review.

## Novelty gate

The current contribution is classified as **engineering implementation /
reproduction of a known result**. Passing tests or observing a lower
three-qubit logical error rate than an unencoded qubit would not establish
novelty. Any later noise-aware selection claim must compare against the
closest adaptive-decoding literature, predeclare the held-out protocol, and
preserve its raw evidence.
