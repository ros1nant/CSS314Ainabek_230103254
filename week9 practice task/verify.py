"""Check remainder handling, process correctness and recorded metric arithmetic."""
import json
import math
import multiprocessing as mp
import statistics
import unittest
from common import ROOT, split_work
from exp_a_serial import heavy_math, run_experiment
from exp_b_contention import run_contended
from exp_c_fixed import private_worker, run_privatized


class Correctness(unittest.TestCase):
    def test_partition(self):
        for total in (0, 1, 3, 17, 1001):
            for p in (1, 2, 4):
                chunks = split_work(total, p)
                self.assertEqual(sum(chunks), total)
                self.assertLessEqual(max(chunks) - min(chunks), 1)

    def test_math_and_serial_pause(self):
        self.assertAlmostEqual(heavy_math(20), sum(math.sin(2 * i) / 2 for i in range(1, 20)))
        self.assertGreaterEqual(run_experiment(2, total_chunks=3, chunk_size=100), 0.4)

    def test_counters_with_remainder(self):
        self.assertEqual(private_worker(17), 17)
        for p in (1, 2, 4):
            self.assertGreater(run_contended(p, 1001), 0)
            self.assertGreater(run_privatized(p, 1001), 0)

    def test_recorded_metrics(self):
        for name in 'ABC':
            data = json.loads((ROOT / 'results' / (name + '.json')).read_text(encoding='utf-8'))
            self.assertEqual([r['workers'] for r in data['rows']], [1, 2, 4])
            t1 = data['rows'][0]['time_s']
            for row in data['rows']:
                p, elapsed = row['workers'], row['time_s']
                self.assertTrue(all(math.isfinite(t) and t > 0 for t in row['samples_s']))
                self.assertEqual(elapsed, statistics.median(row['samples_s']))
                self.assertAlmostEqual(row['speedup'], t1 / elapsed)
                self.assertAlmostEqual(row['efficiency_percent'], 100 * t1 / elapsed / p)
                if p > 1:
                    self.assertAlmostEqual(row['karp_flatt'], (p * elapsed / t1 - 1) / (p - 1))


if __name__ == '__main__':
    mp.freeze_support()
    unittest.main(verbosity=2)
