from common import parser, prepare, read_json, write_json, measure, digest
import numpy as np


def naive(a, b, n, m):
    c = [0.0] * (m * m)
    for i in range(m):
        for j in range(m):
            total = 0.0
            for k in range(m):
                total += a[i * n + k] * b[k * n + j]
            c[i * m + j] = total
    return np.array(c).reshape(m, m)


def interchanged(a, b, n, m):
    c = [0.0] * (m * m)
    for i in range(m):
        ci, ai = i * m, i * n
        for k in range(m):
            aik, bk = a[ai + k], k * n
            for j in range(m):
                c[ci + j] += aik * b[bk + j]
    return np.array(c).reshape(m, m)


def main():
    args = parser('Explicit Python i-j-k and i-k-j multiplication (three runs each)').parse_args()
    out = prepare(args)
    params = read_json(out / 'salted_params.json')
    n = 24 if args.smoke else params['N']
    m = n // 2
    rng = np.random.default_rng(params['seed'])
    a, b = rng.random((n, n)), rng.random((n, n))
    # Flat lists avoid NumPy scalar dispatch while retaining the full row stride N.
    af, bf = a.ravel().tolist(), b.ravel().tolist()
    print(f'N={n}, M={m}; six explicit cubic Python runs may take several minutes.', flush=True)
    baseline, t0, s0 = measure(lambda: naive(af, bf, n, m))
    print('i-j-k finished.', flush=True)
    optimized, t1, s1 = measure(lambda: interchanged(af, bf, n, m))
    np.testing.assert_allclose(optimized, baseline, rtol=0, atol=1e-12)
    np.savez_compressed(out / 'dense_arrays.npz', baseline=baseline, optimized=optimized)
    write_json(out / 'loop_interchange.json', {
        'N': n, 'M': m, 'naive_ns': t0, 'interchanged_ns': t1, 'speedup': t0 / t1,
        'naive_samples_ns': s0, 'interchanged_samples_ns': s1,
        'max_abs_error': float(np.max(np.abs(baseline - optimized))),
        'baseline_digest': digest(baseline, params['student_id']),
        'optimized_digest': digest(optimized, params['student_id']),
        'implementation': 'Explicit Python loops over flat lists; interpreter and object costs included.',
        'smoke': args.smoke})
    print(f'Loop interchange speedup: {t0 / t1:.3f}')


if __name__ == '__main__':
    main()
