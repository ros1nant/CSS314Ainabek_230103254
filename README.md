# Parallel Computing Lab Practicum

Ainabek Aisultan, student ID **230103254**. This repository implements host profiling, salted memory-stride and loop-interchange experiments, shared-memory false sharing with padding and privatization, and strong/weak scaling of a five-point stencil. Empirical bottleneck findings are pending the full run on the submission machine: interpret the recorded stride latency, padding recovery, Amdahl fit and Roofline assumptions rather than presuming a speedup. Python interpreter overhead, process communication, cache reuse and hybrid CPU scheduling can dominate these experiments. See [RUNNING.md](RUNNING.md) for execution, verification, measurement limitations and Git submission instructions.

