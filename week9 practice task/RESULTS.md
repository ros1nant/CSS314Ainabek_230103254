# Week 9 practice: empirical Karp-Flatt diagnostics

Ainabek Aisultan. Original student ID: 230103254; lab ID: 30103254.

- CPU: Intel64 Family 6 Model 183 Stepping 1, GenuineIntel
- Logical execution cores: 20
- OS: Windows-11-10.0.26200-SP0
- Python: 3.13.7
- Multiprocessing start method: spawn. Process startup is included.
- Each time is the median of three independent runs; raw samples are in results/*.json.

| Experiment | T1 (s) | T2 (s) | T4 (s) | e(2) | e(4) | E4 (%) |
|---|---:|---:|---:|---:|---:|---:|
| A | 4.889762 | 3.581686 | 2.117754 | 0.464973 | 0.244133 | 57.72 |
| B | 5.571464 | 20.525056 | 18.927475 | 6.367922 | 4.196290 | 7.36 |
| C | 0.567910 | 0.352123 | 0.278073 | 0.240065 | 0.319524 | 51.06 |

## Findings and checks

- A: e(4)/e(2) = 0.5250. Handout flatness interval [0.80, 1.25]: NOT OBSERVED.
- B: T4 > T1: True; e(4) > e(2): False. Per-increment mutex coordination is the deliberately introduced bottleneck.
- C: T4 < T1: True; E4 > 70%: False. e(4) <= 0.03: False.

A includes the prescribed 0.40-second serial pause, but its measured fraction also includes process startup and dispatch. The advertised e=0.10-0.14 is hardware-dependent. B uses the synchronized Value and explicit Lock from the handout, including their nested synchronization costs. C removes per-increment shared state, but pool startup, result transfer and reduction remain. Small workloads and Windows spawn overhead can prevent near-linear speedup. Karp-Flatt diagnoses aggregate overhead; these timings alone do not identify individual cache-coherence events.

B uses 2,000,000 increments while C uses 20,000,000 as specified. Their absolute times are not a fixed-work speedup comparison. Each experiment keeps work fixed across P=1,2,4. All counter totals were checked exactly on every run; all A task results were checked for agreement and finiteness. No timings were adjusted to match the illustrative table.
