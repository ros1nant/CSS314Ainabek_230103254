# Run on Windows (PowerShell)

Python 3.10+ and NumPy are required. Run from this repository:

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\run_lab.ps1 -Smoke
powershell -ExecutionPolicy Bypass -File .\run_lab.ps1 -CommitMilestones
git status
git log --oneline --decorate
git push origin main --tags
```

The last command is manual. The runner never pushes. `-CommitMilestones` creates five real commits and tags only after the corresponding commands succeed. Configure your own Git author name/email if Git requests it. Existing milestone tags are never overwritten. To rerun measurements without creating commits, omit `-CommitMilestones`. Use `--results PATH` on individual Python scripts to isolate experiments. The default lab student ID is **30103254** (eight digits): the first digit 2 is removed from the original ID 230103254 before salting.

The full run uses the prescribed salted N, 2^24 stride elements, M=N/2, five warmups plus five stride samples, three matrix samples, 5,000,000 increments per worker, and P=1,2,4,8 for contention. Scaling uses powers of two through the physical core count and includes that count when it is not a power of two. Dense Python loops can take several minutes. Keep the computer plugged in and avoid competing workloads. Smoke mode uses small dimensions, saves only to `smoke-results/`, and cannot create submission tags.

## Measurements and interpretation

- `profile_env.py` queries real Windows topology/cache descriptors and CIM CPU information (Linux uses sysfs/lscpu). Null microarchitecture and base clock mean unavailable, not invented. Windows topology is limited to the current processor group; this is intended for this laptop, not machines exceeding 64 logical CPUs. Mixed performance/efficiency cores can influence scaling.
- Stride reduction uses NumPy's native strided sum, avoiding a Python loop that would mask memory latency. It measures useful-element throughput; a cliff is an experimental outcome, not guaranteed.
- Dense multiplication uses explicit flat Python lists and identical k accumulation order. Object and interpreter overhead mean this is not an isolated native-memory bandwidth measurement. Both arrays are checked against an independent NumPy matrix product at absolute tolerance 1e-12.
- False-sharing counters are page-aligned shared int64 data with no global per-increment lock. Windows workers are pinned to one logical CPU per detected physical core when available. Padded counters are 64 bytes apart; private counters publish once under a lock. Timing excludes startup but includes barrier synchronization. Three raw runs and every worker's exact count are retained. Eight workers may oversubscribe machines with fewer physical cores.
- The PDF's counter work is K **per worker**, so total work grows with P. The requested T1/TP and Karp-Flatt are reported literally, but cannot be interpreted as a fixed-work serial fraction; ideal weak scaling would already give e=1. `throughput_speedup=P*T1/TP` is also provided. Negative speedup or a particular contention penalty is never fabricated.
- The stencil is four additions and one multiplication per interior cell. Workers read an immutable shared input with halos and return disjoint output rows. Fifty independent sweeps increase timing stability; these are not successive time steps. Each case uses one persistent process pool, one warmup and three measured runs. Pool startup/input allocation are excluded; dispatch, result transfer and assembly are included. NumPy library thread counts are fixed to one before import.
- Strong scaling uses T1/TP and efficiency S/P. A least-squares Amdahl fit is reported both unconstrained and bounded to [0,1]. Bad fits can indicate overhead or cache effects. Weak scaling records the exact formula printed in the PDF as `assignment_scaled_speedup`; its value approaches 1, not P, under ideal weak scaling. The standard throughput-scaled speedup is `(Work(P)/Work(1))*T1/TP`. Gustafson's prediction uses the fitted serial fraction as an illustrative comparison, not an independent fit.
- Five loads plus one store give a **logical** intensity of 5/48 FLOP/B. Ideal input reuse gives approximately 5/16; write allocation, temporary arrays and IPC alter real traffic. No DRAM counters are available in this implementation. CPU model/cache capacity alone cannot determine theoretical RAM bandwidth. Supply independently established hardware peaks with `-PeakBandwidthGBs VALUE -PeakGflops VALUE` for a model Roofline classification. Without them the classification remains undetermined. No hardware counters, base frequencies or memory specifications are guessed.

## Verification and artifacts

`python verify_outputs.py --update-readme` first checks actual numerical arrays and exact counters, then exports field aliases and runs the supplied practicum verifier. No benchmark timings are changed by this export. `course_verifier.py` preserves the supplied checks; only chat prefixes, a broken indentation and `if __name__ == "__main__"` were repaired. Run it independently with `python course_verifier.py` after the main verification.

`verification_receipt.sig` now follows the supplied STUDENT_ID / SALTED_N / SIGNATURE format. Its token is a deterministic public hash, not an authenticated signature or proof of execution. The stronger local file-hash record is stored separately as `numerical_verification.json`. Smoke mode never emits a submission signature. Rounded numerical digests hash UTF-8 student ID, a zero separator and row-major little-endian float64 values rounded to six places.

For the supplied checker's required `regime`, the low-intensity native stencil is described as **memory-bound as a qualitative hypothesis**. This does not establish that the actual Python program is DRAM-bound. `classification` remains undetermined without hardware peaks; `regime_basis` documents this distinction. The supplied checker only checks whether the text contains "bound" and does not prove the hypothesis. It also does not compare numerical arrays, which is why the stricter local checks are retained.

After correcting the student ID or output format, existing milestone tags still describe the original run. Keep that history; record corrected results in a new commit rather than silently moving old tags:

```powershell
python verify_outputs.py --update-readme
git add .
git commit -m "Fix student ID and align outputs with supplied verifier"
git push origin main --tags
```


Raw arrays (`results/*.npz`) remain local and are ignored by Git to avoid oversized submissions; tables, metadata, digests and receipt are tracked. Regenerate arrays before rerunning verification on another machine; timings and receipt will then differ. If the instructor requires raw arrays in Git, add them explicitly after checking repository size limits. The runner updates the README bottleneck paragraph with actual full-run findings after successful verification, before the final milestone commit. Inspect those findings before pushing. The code does not falsify the lab's 180-minute chronology or backdate tags.

