"""Execute all prescribed workloads and produce an honest empirical report."""
import json
import multiprocessing as mp
import os
import platform
from common import ROOT, benchmark, cli
from exp_a_serial import run_experiment
from exp_b_contention import run_contended
from exp_c_fixed import run_privatized


def report(data):
    lines = ['# Week 9 practice: empirical Karp-Flatt diagnostics', '',
             'Ainabek Aisultan. Original student ID: 230103254; lab ID: 30103254.', '',
             f'- CPU: {platform.processor()}', f'- Logical execution cores: {os.cpu_count()}',
             f'- OS: {platform.platform()}', f'- Python: {platform.python_version()}',
             '- Multiprocessing start method: spawn. Process startup is included.',
             '- Each time is the median of the independent runs recorded in results/*.json.', '',
             '| Experiment | T1 (s) | T2 (s) | T4 (s) | e(2) | e(4) | E4 (%) |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for name, payload in data.items():
        a, b, c = payload['rows']
        lines.append(f"| {name} | {a['time_s']:.6f} | {b['time_s']:.6f} | {c['time_s']:.6f} | {b['karp_flatt']:.6f} | {c['karp_flatt']:.6f} | {c['efficiency_percent']:.2f} |")
    a, b, c = [data[k]['rows'] for k in 'ABC']
    ratio = a[2]['karp_flatt'] / a[1]['karp_flatt'] if a[1]['karp_flatt'] else float('nan')
    lines += ['', '## Findings and checks', '',
              f"- A: e(4)/e(2) = {ratio:.4f}. Handout flatness interval [0.80, 1.25]: {'PASS' if 0.8 <= ratio <= 1.25 else 'NOT OBSERVED'}.",
              f"- B: T4 > T1: {b[2]['time_s'] > b[0]['time_s']}; e(4) > e(2): {b[2]['karp_flatt'] > b[1]['karp_flatt']}. Per-increment mutex coordination is the deliberately introduced bottleneck.",
              f"- C: T4 < T1: {c[2]['time_s'] < c[0]['time_s']}; E4 > 70%: {c[2]['efficiency_percent'] > 70}. e(4) <= 0.03: {c[2]['karp_flatt'] <= 0.03}.", '',
              'A includes the prescribed 0.40-second serial pause, but its measured fraction also includes process startup and dispatch. '
              'The advertised e=0.10-0.14 is hardware-dependent. B uses the synchronized Value and explicit Lock from the handout, '
              'including their nested synchronization costs. C removes per-increment shared state, but pool startup, result transfer and reduction remain. '
              'Small workloads and Windows spawn overhead can prevent near-linear speedup. Karp-Flatt diagnoses aggregate overhead; '
              'these timings alone do not identify individual cache-coherence events.', '',
              'B uses 2,000,000 increments while C uses 20,000,000 as specified. Their absolute times are not a fixed-work speedup comparison. '
              'Each experiment keeps work fixed across P=1,2,4. All counter totals were checked exactly on every run; '
              'all A task results were checked for agreement and finiteness. No timings were adjusted to match the illustrative table.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    mp.freeze_support()
    args = cli()
    data = {}
    for name, fn, params in [('A', run_experiment, dict(total_chunks=16, chunk_size=2_000_000)),
                             ('B', run_contended, dict(total_increments=2_000_000)),
                             ('C', run_privatized, dict(total_increments=20_000_000))]:
        data[name] = benchmark(name, fn, params, args.repeats)
    report(data)
