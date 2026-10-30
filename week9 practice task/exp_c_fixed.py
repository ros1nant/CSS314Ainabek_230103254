import multiprocessing as mp
import time
from common import benchmark, cli, context, split_work


def private_worker(iterations):
    local_sum = 0
    for _ in range(iterations):
        local_sum += 1
    return local_sum


def run_privatized(p, total_increments=20_000_000):
    tasks = split_work(total_increments, p)
    t0 = time.perf_counter()
    with context().Pool(processes=p) as pool:
        results = pool.map(private_worker, tasks)
    total = sum(results)
    elapsed = time.perf_counter() - t0
    if results != tasks or total != total_increments:
        raise AssertionError('Privatized reduction mismatch')
    return elapsed


if __name__ == '__main__':
    mp.freeze_support()
    benchmark('C', run_privatized, dict(total_increments=20_000_000), cli().repeats)
