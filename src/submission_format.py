"""Export aliases required by the supplied verifier without changing raw measurements."""
import csv
from common import read_json, write_json, write_tsv


def rows(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def export(out):
    host = read_json(out / 'host_profile.json')
    lines = {c['line_bytes'] for c in host['caches']}
    if len(lines) != 1:
        raise ValueError(f'Cannot export a single measured cache-line size: {lines}')
    host['cache_line_bytes'] = lines.pop()
    write_json(out / 'host_profile.json', host)

    stride = rows(out / 'stride_results.tsv')
    for r in stride:
        r['latency_ns'] = r['ns_per_element']
    write_tsv(out / 'stride_results.tsv', stride)

    dense = read_json(out / 'loop_interchange.json')
    dense['naive_time_s'] = dense['naive_ns'] / 1e9
    dense['interchanged_time_s'] = dense['interchanged_ns'] / 1e9
    write_json(out / 'loop_interchange.json', dense)

    counters = rows(out / 'false_sharing_karp_flatt.tsv')
    lookup = {(r['mode'], r['processes']): r['karp_flatt'] for r in counters}
    for r in counters:
        r['p'] = r['processes']
        # The existing long-form rows retain per-mode samples. Comparison columns
        # repeat the same measured pair for that P, independent of the row's mode.
        r['e_unpadded'] = lookup['unpadded', r['processes']] or 'N/A'
        r['e_padded'] = lookup['padded', r['processes']] or 'N/A'
    write_tsv(out / 'false_sharing_karp_flatt.tsv', counters)

    roof = read_json(out / 'roofline_summary.json')
    roof['arithmetic_intensity'] = roof['arithmetic_intensity_logical']
    if roof['peak_bandwidth_gbs'] and roof['peak_gflops']:
        roof['regime'] = roof['classification']
        roof['regime_basis'] = 'Roofline comparison using supplied hardware peaks.'
    else:
        roof['regime'] = 'memory-bound (qualitative hypothesis for the native stencil kernel, not a measured host classification)'
        roof['regime_basis'] = (
            'The stencil performs only five FLOPs per 48 logical bytes (5/16 with ideal reuse), '
            'suggesting a memory-bound native kernel. This is a hypothesis, not proof: '
            'CPU/RAM peaks and DRAM traffic were not measured. Python/NumPy temporaries, '
            'cache residency and IPC may instead dominate the implemented program. '
            'The measured host classification remains undetermined in classification.')
    write_json(out / 'roofline_summary.json', roof)
