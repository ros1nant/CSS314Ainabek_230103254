import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import time

# Set before importing NumPy, including in spawned Windows workers.
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

ROOT = Path(__file__).resolve().parents[1]


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--results', type=Path, default=ROOT / 'results')
    p.add_argument('--smoke', action='store_true', help='Small correctness run; not submission measurements')
    return p


def prepare(args):
    if args.smoke and args.results.resolve() == (ROOT / 'results').resolve():
        args.results = ROOT / 'smoke-results'
    args.results.mkdir(parents=True, exist_ok=True)
    return args.results


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_tsv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


def measure(fn, repeats=3, warmups=0):
    for _ in range(warmups):
        fn()
    times = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        result = fn()
        times.append(time.perf_counter_ns() - start)
    return result, statistics.median(times), times


def digest(values, student_id):
    import numpy as np
    rounded = np.round(np.asarray(values, dtype=np.float64), 6)
    rounded[rounded == 0] = 0  # Canonicalize negative zero.
    return hashlib.sha256(student_id.encode() + b'\0' + rounded.astype('<f8').tobytes(order='C')).hexdigest()


def karp_flatt(t1, tp, p):
    return (p * tp / t1 - 1) / (p - 1) if p > 1 else None

