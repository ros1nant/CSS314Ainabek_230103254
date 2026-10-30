"""Shared timing/reporting helpers; standard library only, Python 3.8+."""
import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent


def split_work(total, workers):
    if total < 0 or workers < 1:
        raise ValueError('Work must be nonnegative and workers positive')
    q, r = divmod(total, workers)
    return [q + (i < r) for i in range(workers)]


def benchmark(name, runner, parameters, repeats=3):
    if repeats < 1:
        raise ValueError('repeats must be positive')
    rows = []
    for p in (1, 2, 4):
        samples = [runner(p, **parameters) for _ in range(repeats)]
        elapsed = statistics.median(samples)
        t1 = elapsed if p == 1 else rows[0]['time_s']
        speedup = t1 / elapsed
        e = ((p * elapsed / t1) - 1) / (p - 1) if p > 1 else None
        rows.append(dict(workers=p, time_s=elapsed, samples_s=samples,
                         speedup=speedup, efficiency_percent=100 * speedup / p, karp_flatt=e))
        print(f'{name}: P={p}, T={elapsed:.6f}s, S={speedup:.3f}, e={e}', flush=True)
    payload = dict(experiment=name, parameters=parameters, rows=rows,
                   timestamp_utc=datetime.now(timezone.utc).isoformat(),
                   logical_cores=os.cpu_count(), cpu=platform.processor(),
                   os=platform.platform(), python=platform.python_version(),
                   start_method='spawn', timing='Includes process/pool startup and synchronization; median of independent runs.')
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    (out / (name + '.json')).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return payload


def cli():
    p = argparse.ArgumentParser()
    p.add_argument('--repeats', type=int, default=3)
    return p.parse_args()


def context():
    return mp.get_context('spawn')
