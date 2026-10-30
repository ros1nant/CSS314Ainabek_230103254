# Week 9 practice tasks

Three standard-library multiprocessing experiments from the practice handout. Solutions and results are kept in this folder to separate them from the earlier practicum.

From this folder run:

```powershell
python run_all.py
```

This runs P=1,2,4 with three recorded repetitions and writes `results/A.json`, `results/B.json`, `results/C.json` and `RESULTS.md`. Each script can also be run individually, for example `python exp_a_serial.py`. No third-party dependencies are required. All entry points have Windows multiprocessing guards. Work partitioning also handles totals not divisible by the process count.

The workload sizes and timing boundaries follow the handout, including startup overhead. Measured performance targets are reported as observations, not asserted as universal properties. See [RESULTS.md](RESULTS.md) for the actual host measurements.

Run `python verify.py` after benchmarking to check work partitioning, exact reductions (including nondivisible totals), the sequential pause, and the arithmetic of all recorded speedups, efficiencies and Karp-Flatt metrics. All four checks passed on the recorded run. The solution branch is `practice-30103254`.
