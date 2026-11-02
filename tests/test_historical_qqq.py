"""Regression tests for quote holdouts and benchmark source integrity."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import historical_qqq as h


class HistoricalQuoteTests(unittest.TestCase):
    def test_holdout_excludes_entire_strike_and_expiry(self):
        axes = [np.array([.8, .85, 1., 1.1, 1.2]), np.array([.1, .2, .4, .9, 1.8])]
        values = np.arange(25.).reshape(5, 5)
        a, train, q, truth = h.split_grid(axes, values)
        self.assertEqual(train.shape, (4, 4))
        self.assertEqual(len(truth), 9)
        self.assertFalse(set(train.ravel()) & set(truth))
        self.assertEqual(set(train.ravel()) | set(truth), set(values.ravel()))
        self.assertNotIn(axes[0][2], a[0])
        self.assertNotIn(axes[1][2], a[1])
        for j in range(2):
            self.assertTrue(np.all((q[:, j] >= a[j][0]) & (q[:, j] <= a[j][-1])))

    def test_linear_recovers_bilinear_holdouts(self):
        a = [np.linspace(.8, 1.2, 7), np.array([.1, .2, .3, .5, .8, 1., 1.5])]
        x, t = np.meshgrid(*a, indexing='ij')
        values = .2 + .04 * x + .01 * t + .02 * x * t
        axes, train, q, truth = h.split_grid(a, values)
        actual = h.interpolate_surface(axes, train, q, method='linear')
        np.testing.assert_allclose(actual, truth, atol=1e-14, rtol=1e-14)

    def test_nonpositive_predictions_are_counted_not_logged(self):
        m = h.metrics(np.array([.2, -.1, np.nan]), np.array([.2, .3, .4]))
        self.assertEqual((m['finite'], m['nonpositive'], m['log_pairs']), (2, 1, 1))
        self.assertEqual(m['rmse_log_iv'], 0.)

    def test_cached_file_integrity_is_checked(self):
        data = b'example bytes'
        sha = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        with tempfile.TemporaryDirectory() as d, patch.dict(h.FILES, {'sample': (len(data), sha)}):
            path = Path(d) / 'sample'
            path.write_bytes(data)
            self.assertEqual(h.verified_file('sample', Path(d), False)[1]['git_blob_sha1'], sha)
            path.write_bytes(b'other bytes')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                h.verified_file('sample', Path(d), False)


if __name__ == '__main__':
    unittest.main()
