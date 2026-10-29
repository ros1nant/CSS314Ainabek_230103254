import ctypes
import multiprocessing as mp
from multiprocessing import shared_memory
import statistics
import time

from common import parser, prepare, read_json, write_tsv, write_json, karp_flatt


def pin(mask):
    if mask:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
            raise ctypes.WinError(ctypes.get_last_error())


def worker(name, count, index, iterations, mode, barrier, lock, mask):
    pin(mask)
    shm = shared_memory.SharedMemory(name=name)
    counters = (ctypes.c_int64 * count).from_buffer(shm.buf)
    try:
        barrier.wait(timeout=120)
        if mode == 'privatized':
            local = 0
            for _ in range(iterations):
                local += 1
            with lock:
                counters[index] = local
        else:
            for _ in range(iterations):
                counters[index] += 1
        barrier.wait(timeout=600)
    finally:
        del counters
        shm.close()


def run(mode, p, iterations, stride, masks):
    ctx = mp.get_context('spawn')
    size = p * stride
    shm = shared_memory.SharedMemory(create=True, size=max(64, size * 8))
    shm.buf[:] = b'\0' * len(shm.buf)
    barrier, lock = ctx.Barrier(p + 1), ctx.Lock()
    processes = []
    try:
        address = ctypes.addressof(ctypes.c_char.from_buffer(shm.buf))
        if address % 64:
            raise RuntimeError('Shared allocation is not cache-line aligned')
        for rank in range(p):
            mask = masks[rank] & -masks[rank] if rank < len(masks) else 0
            proc = ctx.Process(target=worker, args=(shm.name, size, rank * stride,
                               iterations, mode, barrier, lock, mask))
            proc.start()
            processes.append(proc)
        # Startup is excluded. The interval includes barrier release and completion.
        start = time.perf_counter_ns()
        barrier.wait(timeout=120)
        ready = time.perf_counter_ns()
        barrier.wait(timeout=600)
        elapsed = time.perf_counter_ns() - ready
        startup = ready - start
        for proc in processes:
            proc.join(timeout=10)
            if proc.exitcode != 0:
                raise RuntimeError(f'Worker failed: {proc.exitcode}')
        values = (ctypes.c_int64 * size).from_buffer_copy(shm.buf)
        counts = [values[i * stride] for i in range(p)]
        if counts != [iterations] * p:
            raise AssertionError(f'Incorrect counters: {counts}')
        return elapsed, counts, startup
    finally:
        for proc in processes:
            if proc.is_alive():
                proc.terminate()
            proc.join()
        shm.close()
        shm.unlink()


def main():
    args = parser('False sharing with lock-free independent shared counters').parse_args()
    out = prepare(args)
    host = read_json(out / 'host_profile.json')
    lines = [c['line_bytes'] for c in host['caches']]
    line = max(lines, default=64)
    if line != 64:
        raise RuntimeError(f'Assignment assumes 64-byte lines; measured {line}')
    iterations = 10000 if args.smoke else 5_000_000
    rows, raw = [], []
    for mode in ('unpadded', 'padded', 'privatized'):
        t1 = None
        for p in (1, 2, 4, 8):
            runs = [run(mode, p, iterations, 1 if mode == 'unpadded' else 8,
                        host.get('core_masks', [])) for _ in range(3)]
            elapsed = statistics.median(r[0] for r in runs)
            t1 = elapsed if p == 1 else t1
            rows.append(dict(mode=mode, processes=p, iterations_per_worker=iterations,
                             time_ns=elapsed, samples_ns=','.join(str(r[0]) for r in runs),
                             total_count=p * iterations, speedup=t1 / elapsed,
                             karp_flatt=karp_flatt(t1, elapsed, p),
                             throughput_speedup=p * t1 / elapsed, smoke=args.smoke))
            raw.append({'mode': mode, 'processes': p, 'counts_per_run': [r[1] for r in runs],
                        'ready_wait_ns': [r[2] for r in runs]})
            print(f'{mode}, P={p}: {elapsed / 1e6:.3f} ms', flush=True)
    write_tsv(out / 'false_sharing_karp_flatt.tsv', rows)
    write_json(out / 'counter_checks.json', raw)


if __name__ == '__main__':
    mp.freeze_support()
    main()

