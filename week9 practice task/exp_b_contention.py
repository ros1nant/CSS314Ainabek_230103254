import multiprocessing as mp
import time
from common import benchmark, cli, context, split_work


def contended_worker(shared_counter, lock, iterations):
    for _ in range(iterations):
        with lock:
            shared_counter.value += 1


def run_contended(p, total_increments=2_000_000):
    ctx = context()
    counter, lock = ctx.Value('i', 0), ctx.Lock()
    procs = [ctx.Process(target=contended_worker, args=(counter, lock, count))
             for count in split_work(total_increments, p)]
    started = []
    t0 = time.perf_counter()
    try:
        for proc in procs:
            proc.start()
            started.append(proc)
        for proc in started:
            proc.join(timeout=300)
            if proc.exitcode != 0:
                raise RuntimeError(f'Counter worker failed or timed out: {proc.exitcode}')
        elapsed = time.perf_counter() - t0
        if counter.value != total_increments:
            raise AssertionError(f'{counter.value} != {total_increments}')
        return elapsed
    finally:
        for proc in started:
            if proc.is_alive():
                proc.terminate()
            proc.join()


if __name__ == '__main__':
    mp.freeze_support()
    benchmark('B', run_contended, dict(total_increments=2_000_000), cli().repeats)
