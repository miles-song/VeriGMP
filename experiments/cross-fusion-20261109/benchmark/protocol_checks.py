#!/usr/bin/env python3
"""Synthetic, untimed checks of the preregistered rejection rules."""
import datetime
import unittest

from measure import stability
from review_telemetry import evaluate_series, timestamp


def stamp(seconds):
    return (datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
            + datetime.timedelta(seconds=seconds)).isoformat()


def blocks(abba, baab):
    return [dict(sequence=direction, ratio=value)
            for direction, values in (('ABBA', abba), ('BAAB', baab)) for value in values]


def rows(kind='wsl', times=range(9), competing=0.0, reuse=False):
    result = []
    for index, t in enumerate(times):
        if kind == 'wsl':
            processes = [dict(pid=1, start_ticks=10, name='monitor', cpu_ticks=index),
                         dict(pid=100, start_ticks=21 if reuse else 20, name='other',
                              cpu_ticks=round(index * competing * 100))]
            result.append(dict(utc_start=stamp(t), utc_end=stamp(t + 0.001),
                               monotonic_ns=int(t * 1e9), processes=processes,
                               ticks_per_second=100, errors=[], vanished=[],
                               proc_stat=f'cpu {index * 10} 0 0 0 0 0 0 0 0 0\n',
                               memory_pressure='some avg10=0.00 avg60=0.00 total=0'))
        else:
            processes = [dict(pid=0, start_100ns=1, name='', cpu_100ns=index * 10_000_000),
                         dict(pid=2, start_100ns=2, name='vmmemWSL', cpu_100ns=index * 10_000_000),
                         dict(pid=3, start_100ns=3, name='other',
                              cpu_100ns=round(index * competing * 10_000_000))]
            result.append(dict(utc_start=stamp(t), utc_end=stamp(t + 0.001),
                               monotonic_ms=int(t * 1000), processes=processes,
                               memory=dict(load_percent=50)))
    return result


class ProtocolChecks(unittest.TestCase):
    def assess(self, data, kind='wsl', allowed=frozenset(), lifetimes=()):
        return evaluate_series(data, kind, timestamp(stamp(1)), timestamp(stamp(7)), allowed, lifetimes)

    def test_stable_improvement(self):
        result = stability(blocks((0.96, 0.97), (0.96, 0.97)))
        self.assertTrue(result['stable'] and result['improvement'] and result['no_regression'])

    def test_opposing_order_cannot_hide_in_median(self):
        result = stability(blocks((0.94, 0.94), (1.00, 1.00)))
        self.assertAlmostEqual(result['median'], 0.97)
        self.assertFalse(result['stable'])
        self.assertFalse(result['improvement'])

    def test_same_order_noise_rejected(self):
        result = stability(blocks((0.96, 0.99), (0.975, 0.975)))
        self.assertFalse(result['stable'])

    def test_one_direction_regression_rejected(self):
        result = stability(blocks((1.034, 1.034), (1.025, 1.025)))
        self.assertLessEqual(result['median'], 1.03)
        self.assertTrue(result['stable'])
        self.assertFalse(result['no_regression'])

    def test_monitor_gap_and_coverage_rejected(self):
        self.assertTrue(self.assess(rows(times=(0, 1, 4, 5, 6, 7, 8)))['failures'])
        self.assertTrue(self.assess(rows(times=(2, 3, 4, 5, 6, 7, 8)))['failures'])
        self.assertTrue(self.assess(rows('host', times=(0, 1, 4, 5, 6, 7, 8)), 'host')['failures'])

    def test_competing_cpu_rejected_on_both_hosts(self):
        self.assertTrue(self.assess(rows(competing=0.3))['failures'])
        self.assertTrue(self.assess(rows('host', competing=0.3), 'host')['failures'])

    def test_missing_memory_is_inconclusive(self):
        data = rows('host')
        del data[3]['memory']
        self.assertTrue(self.assess(data, 'host')['unknown'])

    def test_memory_pressure_rejected(self):
        data = rows('host')
        for row in data:
            row['memory']['load_percent'] = 90
        self.assertTrue(self.assess(data, 'host')['failures'])

    def test_vanished_process_requires_lifetime(self):
        data = rows()
        data[3]['vanished'] = [dict(pid=100, utc=stamp(3))]
        self.assertTrue(self.assess(data)['unknown'])
        life = dict(pid=100, start_ticks=20, start=timestamp(stamp(2)),
                    end=timestamp(stamp(4)), cpu_seconds=0.01)
        self.assertFalse(self.assess(data, lifetimes=[life])['unknown'])

    def test_unexplained_aggregate_cpu_rejected(self):
        data = rows()
        for index, row in enumerate(data):
            row['proc_stat'] = f'cpu {index * 50} 0 0 0 0 0 0 0 0 0\n'
        self.assertTrue(self.assess(data)['failures'])

    def test_pid_reuse_is_not_exempt(self):
        result = self.assess(rows(competing=0.3, reuse=True), allowed={(100, 20)})
        self.assertTrue(result['failures'])
        self.assertTrue(any(p['pid'] == 100 and p['start'] == 21
                            for interval in result['intervals'] for p in interval['competitors']))

    def test_exact_process_identity_is_exempt(self):
        result = self.assess(rows(competing=0.3), allowed={(100, 20)})
        self.assertFalse(result['failures'])
        self.assertFalse(result['unknown'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
