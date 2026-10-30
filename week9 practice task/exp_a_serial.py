import math
import multiprocessing as mp
import time
from common import benchmark, cli, context


def heavy_math(n):
    return sum(math.sin(i) * math.cos(i) for i in range(1, n))


def run_experiment(workers, total_chunks=16, chunk_size=2_000_000):
    t0 = time.perf_counter()
    time.sleep(0.40)
    with context().Pool(processes=workers) as pool:
        values = pool.map(heavy_math, [chunk_size] * total_chunks)
    elapsed = time.perf_counter() - t0
    if len(values) != total_chunks or not all(math.isfinite(v) and v == values[0] for v in values):
        raise AssertionError('Missing or inconsistent math results')
    return elapsed


if __name__ == '__main__':
    mp.freeze_support()
    benchmark('A', run_experiment, dict(total_chunks=16, chunk_size=2_000_000), cli().repeats)
