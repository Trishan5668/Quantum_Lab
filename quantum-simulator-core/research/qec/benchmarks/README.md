# Benchmarks

`benchmark_qec.py` records engineering timings on the audit sandbox:

- exact lookup-table build time for repetition d=3/5/7,
- exact decode time per syndrome,
- Stim/PyMatching MWPM batch decode time for d=3/5 surface-code circuits.

These are **not** scientific performance claims, not a comparison with
published decoders, and not portable across hardware. They are useful only
for detecting large regressions in this repository.

Run:

```bash
python research/qec/benchmarks/benchmark_qec.py
```

Results are written to `results.json` with the platform and Python version.
