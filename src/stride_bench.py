from common import parser, prepare, read_json, measure, write_tsv
import numpy as np


def main():
    args = parser('Stride reduction: five warmups and five measured iterations').parse_args()
    out = prepare(args)
    params = read_json(out / 'salted_params.json')
    n = 65536 if args.smoke else params['buffer_elements']
    data = np.ones(n, dtype=np.float64)
    rows = []
    for stride in (1, 2, 4, 8, 16, 32, 64, 128):
        view = data[::stride]
        total, median, samples = measure(lambda: float(np.sum(view)), repeats=5, warmups=5)
        if total != view.size:
            raise AssertionError('Stride reduction mismatch')
        rows.append(dict(stride=stride, elements=int(view.size), time_ns=median,
                         ns_per_element=median / view.size, total=total,
                         samples_ns=','.join(map(str, samples)), smoke=args.smoke))
        print(f'Stride {stride}: {median / view.size:.3f} ns/element', flush=True)
    write_tsv(out / 'stride_results.tsv', rows)


if __name__ == '__main__':
    main()

