import math
import multiprocessing as mp
from multiprocessing import shared_memory

from common import parser, prepare, read_json, write_json, write_tsv, measure, digest, karp_flatt
import numpy as np


def stencil(a):
    return (a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1]
            + a[1:-1, :-2] + a[1:-1, 2:]) * 0.2


def chunk(task):
    name, n, lo, hi, iterations = task
    shm = shared_memory.SharedMemory(name=name)
    a = np.ndarray((n, n), dtype=np.float64, buffer=shm.buf)
    try:
        for _ in range(iterations):
            result = stencil(a[lo - 1:hi + 1, :])
        return result
    finally:
        del a
        shm.close()


def run_case(n, p, seed, iterations, student_id, out, mode):
    a = np.random.default_rng(seed).random((n, n))
    reference = stencil(a)
    shm = shared_memory.SharedMemory(create=True, size=a.nbytes)
    shared = np.ndarray(a.shape, dtype=a.dtype, buffer=shm.buf)
    shared[:] = a
    edges = np.linspace(1, n - 1, p + 1, dtype=int)
    tasks = [(shm.name, n, int(edges[i]), int(edges[i + 1]), iterations) for i in range(p)]
    try:
        # One persistent pool per case; startup excluded, IPC and result assembly included.
        with mp.get_context('spawn').Pool(p) as pool:
            result, median, samples = measure(lambda: np.concatenate(pool.map(chunk, tasks)), warmups=1)
        np.testing.assert_allclose(result, reference, rtol=0, atol=1e-12)
        np.savez_compressed(out / f'stencil_{mode}_{p}.npz', result=result)
        return {'mode': mode, 'processes': p, 'N': n, 'iterations': iterations,
                'work': (n - 2)**2 * iterations, 'time_ns': median,
                'samples_ns': ','.join(map(str, samples)),
                'result_digest': digest(result, student_id),
                'reference_digest': digest(reference, student_id)}
    finally:
        del shared
        shm.close()
        shm.unlink()


def main():
    p = parser('Strong and weak scaling of a five-point stencil')
    p.add_argument('--peak-bandwidth-gbs', type=float)
    p.add_argument('--peak-gflops', type=float)
    args = p.parse_args()
    for value in (args.peak_bandwidth_gbs, args.peak_gflops):
        if value is not None and (not math.isfinite(value) or value <= 0):
            p.error('Hardware peaks must be finite positive numbers')
    out = prepare(args)
    params, host = read_json(out / 'salted_params.json'), read_json(out / 'host_profile.json')
    n = 32 if args.smoke else params['N']
    maximum = min(2, host['physical_cores']) if args.smoke else host['physical_cores']
    workers = sorted(set([2**i for i in range(maximum.bit_length()) if 2**i <= maximum] + [maximum]))
    iterations = 2 if args.smoke else 50
    rows = []
    for mode in ('strong', 'weak'):
        t1, work1 = None, None
        for count in workers:
            dimension = n if mode == 'strong' else math.ceil(n * math.sqrt(count))
            row = run_case(dimension, count, params['seed'], iterations, params['student_id'], out, mode)
            if count == 1:
                t1, work1 = row['time_ns'], row['work']
            ratio = t1 / row['time_ns']
            row.update(speedup=ratio, efficiency_percent=100 * ratio / count,
                       effective_serial_fraction=karp_flatt(t1, row['time_ns'], count),
                       assignment_scaled_speedup=count * work1 * t1 / (row['work'] * row['time_ns']),
                       throughput_scaled_speedup=(row['work'] / work1) * ratio,
                       weak_efficiency_percent=100 * ratio, smoke=args.smoke)
            rows.append(row)
            print(f'{mode}, P={count}, N={dimension}: {row["time_ns"] / 1e6:.3f} ms', flush=True)
    strong = [r for r in rows if r['mode'] == 'strong' and r['processes'] > 1]
    # Least squares on T(P)/T(1) = 1/P + s*(1-1/P).
    x = np.array([1 - 1 / r['processes'] for r in strong])
    y = np.array([1 / r['speedup'] - 1 / r['processes'] for r in strong])
    serial_raw = float(x @ y / (x @ x)) if len(x) else None
    serial = min(1.0, max(0.0, serial_raw)) if serial_raw is not None else None
    for row in rows:
        row['gustafson_prediction'] = (row['processes'] - serial * (row['processes'] - 1)) if serial is not None else None
    write_tsv(out / 'scaling_metrics.tsv', rows)
    ai = 5 / 48  # Five reads, one write, four additions, one multiplication.
    bandwidth, compute = args.peak_bandwidth_gbs, args.peak_gflops
    regime = ('memory-bandwidth bound (model)' if ai * bandwidth < compute else 'compute bound (model)') if bandwidth and compute else 'undetermined: hardware peak bandwidth and peak FLOP/s required'
    best = min((r for r in rows if r['mode'] == 'strong'), key=lambda r: r['time_ns'])
    write_json(out / 'roofline_summary.json', {
        'flops_per_update': 5, 'logical_bytes_per_update': 48, 'arithmetic_intensity_logical': ai,
        'ideal_reuse_bytes_per_update': 16, 'arithmetic_intensity_ideal_reuse': 5 / 16,
        'traffic_note': '48 B is logical access traffic, not measured DRAM traffic. Cache reuse, NumPy temporaries, repeated immutable sweeps and IPC affect actual traffic.',
        'stencil_note': 'Repeated independent five-point sweeps of immutable input; not an evolving PDE simulation.',
        'matrix_bytes': n * n * 8, 'caches': host['caches'],
        'peak_bandwidth_gbs': bandwidth, 'peak_gflops': compute,
        'peak_source': 'user supplied' if bandwidth or compute else None,
        'classification': regime, 'model_roof_gflops': min(compute, ai * bandwidth) if bandwidth and compute else None,
        'best_observed_gflops': best['work'] * 5 / best['time_ns'],
        'amdahl_serial_fraction_unconstrained': serial_raw, 'amdahl_serial_fraction': serial,
        'asymptotic_speedup': 1 / serial if serial else None,
        'fit_note': 'Bounded fit in [0,1]. Null ceiling means zero serial fraction or insufficient data; overhead may violate Amdahl.',
        'smoke': args.smoke})


if __name__ == '__main__':
    mp.freeze_support()
    main()
