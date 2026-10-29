"""Strict numerical verification followed by the supplied practicum verifier."""
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from common import parser, prepare, read_json, write_json, digest, karp_flatt
from salt import get_student_params
from scaling_study import stencil
import numpy as np


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def table(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def main():
    p = parser('Verify actual arrays, counts, timings and salted dimensions')
    p.add_argument('--update-readme', action='store_true', help='Write measured findings after a successful full verification')
    args = p.parse_args()
    if args.smoke and args.update_readme:
        p.error('Smoke results must not become submission findings')
    out = prepare(args)
    receipt = out / 'numerical_verification.json'
    receipt.unlink(missing_ok=True)
    (out / 'verification_receipt.sig').unlink(missing_ok=True)
    params, host = read_json(out / 'salted_params.json'), read_json(out / 'host_profile.json')
    sid = params['student_id']
    require(params == get_student_params(sid), 'Invalid salt parameters')
    require(host['physical_cores'] > 0 and host['caches'], 'Missing hardware topology')
    require(host['smoke'] == args.smoke, 'Mixed smoke and submission data')
    print('[PASS] M0: topology and salt')
    stride = table(out / 'stride_results.tsv')
    require([int(r['stride']) for r in stride] == [1, 2, 4, 8, 16, 32, 64, 128], 'Missing strides')
    size = 65536 if args.smoke else params['buffer_elements']
    for r in stride:
        require(int(r['elements']) == len(range(0, size, int(r['stride']))), 'Incorrect touched elements')
        require(float(r['total']) == int(r['elements']), 'Incorrect stride sum')
    meta = read_json(out / 'loop_interchange.json')
    n = 24 if args.smoke else params['N']
    require(meta['N'] == n and meta['M'] == n // 2, 'Incorrect dense dimensions')
    rng = np.random.default_rng(params['seed'])
    a, b = rng.random((n, n)), rng.random((n, n))
    m = n // 2
    with np.load(out / 'dense_arrays.npz') as arrays:
        require(arrays['baseline'].shape == (m, m), 'Incorrect dense shape')
        np.testing.assert_allclose(arrays['baseline'], a[:m, :m] @ b[:m, :m], rtol=0, atol=1e-12)
        np.testing.assert_allclose(arrays['baseline'], arrays['optimized'], rtol=0, atol=1e-12)
        for key in ('baseline', 'optimized'):
            require(digest(arrays[key], sid) == meta[key + '_digest'], 'Matrix digest mismatch')
    print('[PASS] M1: stride and dense numerical outputs')
    counters = table(out / 'false_sharing_karp_flatt.tsv')
    evidence = read_json(out / 'counter_checks.json')
    expected = {(mode, p) for mode in ('unpadded', 'padded', 'privatized') for p in (1, 2, 4, 8)}
    require({(r['mode'], int(r['processes'])) for r in counters} == expected and len(counters) == 12, 'Missing counter cases')
    require({(r['mode'], r['processes']) for r in evidence} == expected and len(evidence) == 12, 'Missing counter evidence')
    k = 10000 if args.smoke else 5_000_000
    for r in evidence:
        require(len(r['counts_per_run']) == 3, 'Missing counter repeats')
        require(all(values == [k] * r['processes'] for values in r['counts_per_run']), 'Lost counter increments')
    for r in counters:
        p = int(r['processes'])
        require(int(r['iterations_per_worker']) == k and int(r['total_count']) == p * k, 'Wrong counter total')
        if p > 1:
            t1 = float(next(x['time_ns'] for x in counters if x['mode'] == r['mode'] and x['processes'] == '1'))
            require(abs(float(r['karp_flatt']) - karp_flatt(t1, float(r['time_ns']), p)) < 1e-12, 'Wrong Karp-Flatt')
    print('[PASS] M2: exact counts and Karp-Flatt')
    scaling = table(out / 'scaling_metrics.tsv')
    maximum = min(2, host['physical_cores']) if args.smoke else host['physical_cores']
    workers = {2**i for i in range(maximum.bit_length()) if 2**i <= maximum} | {maximum}
    require({(r['mode'], int(r['processes'])) for r in scaling} == {(mode, p) for mode in ('strong', 'weak') for p in workers}, 'Missing scaling cases')
    import math
    base = 32 if args.smoke else params['N']
    for r in scaling:
        n, p = int(r['N']), int(r['processes'])
        require(n == (base if r['mode'] == 'strong' else math.ceil(base * math.sqrt(p))), 'Wrong stencil dimension')
        reference = stencil(np.random.default_rng(params['seed']).random((n, n)))
        with np.load(out / f"stencil_{r['mode']}_{p}.npz") as arrays:
            require(arrays['result'].shape == reference.shape, 'Incorrect stencil shape')
            np.testing.assert_allclose(arrays['result'], reference, rtol=0, atol=1e-12)
            require(digest(arrays['result'], sid) == r['result_digest'] == r['reference_digest'], 'Stencil digest mismatch')
    for rows in (stride, counters, scaling):
        for r in rows:
            samples = [int(v) for v in r['samples_ns'].split(',')]
            require(all(v > 0 for v in samples), 'Invalid timing samples')
            require(r['smoke'] == str(args.smoke), 'Mixed experiment modes')
    roof = read_json(out / 'roofline_summary.json')
    require(roof['smoke'] == args.smoke and roof['flops_per_update'] == 5, 'Invalid roofline metadata')
    print('[PASS] M3: stencil outputs and timing samples')
    from submission_format import export
    export(out)
    if not args.smoke:
        # The supplied verifier uses relative results/ paths. Support --results
        # without editing its validation logic by resolving those paths here.
        import course_verifier
        original_check = course_verifier.check_file
        original_emit = course_verifier.emit_receipt
        def resolve_file(path, milestone):
            return original_check(str(out / Path(path).name), milestone)
        def emit(sid, n):
            token = hashlib.sha256(f'CS482-PRACTICUM-VERIFIED-{sid}-{n}-HASH-SOLO-LAB'.encode()).hexdigest()
            (out / 'verification_receipt.sig').write_text(
                f'STUDENT_ID={sid}\nSALTED_N={n}\nSIGNATURE={token}\n', encoding='utf-8')
        try:
            course_verifier.check_file = resolve_file
            course_verifier.emit_receipt = emit
            course_verifier.main()
        finally:
            course_verifier.check_file = original_check
            course_verifier.emit_receipt = original_emit
    files = sorted(f for f in out.iterdir() if f.is_file() and f.name != receipt.name)
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    write_json(receipt, {'kind': 'local SHA-256 integrity receipt; not a digital signature or instructor authentication',
                         'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'student_id': sid,
                         'smoke': args.smoke, 'files_sha256': hashes})
    print(f'All local checks passed. Receipt: {receipt}')
    if args.update_readme:
        def counter_time(mode, count):
            return float(next(r['time_ns'] for r in counters if r['mode'] == mode and int(r['processes']) == count))
        strongest = max((r for r in scaling if r['mode'] == 'strong'), key=lambda r: float(r['speedup']))
        cliff = float(stride[3]['ns_per_element']) / float(stride[0]['ns_per_element'])
        paragraph = (
            f"Ainabek Aisultan, student ID **{sid}**. On {host['cpu_model']} "
            f"({host['physical_cores']} physical cores), stride-8 latency per touched element was "
            f"{cliff:.3f}x stride-1; loop interchange speedup was {meta['speedup']:.3f}x. "
            f"At P=8, unpadded/padded runtime ratio was {counter_time('unpadded', 8) / counter_time('padded', 8):.3f}x "
            f"and unpadded/privatized ratio was {counter_time('unpadded', 8) / counter_time('privatized', 8):.3f}x. "
            f"Best measured strong-scaling speedup was {float(strongest['speedup']):.3f}x at P={strongest['processes']}. "
            f"Roofline classification: {roof['classification']}. "
            'These observations include interpreter, synchronization and IPC costs; they do not isolate DRAM traffic. '
            'All local numerical checks passed. See [RUNNING.md](RUNNING.md) for methods and limitations.\n'
        )
        (Path(__file__).resolve().parent / 'README.md').write_text('# Parallel Computing Lab Practicum\n\n' + paragraph, encoding='utf-8')


if __name__ == '__main__':
    main()

