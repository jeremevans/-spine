"""Leakage, calendar, transformation, estimation and native-evidence tests."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from spline_equivalence.forecast import (fit_pca_ar1, log_surfaces, subspace_distance,
                                         walk_forward)
from forecast_qqq import freeze_axes, evaluate_at_quotes, error_stats, quote_mask
from verify_forecast import compare_native


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(4091)
        self.x = self.rng.normal(size=(40, 12)) * .05 - 1.7
        self.months = np.arange(40)

    def test_future_mutations_cannot_change_prior_forecast_or_fit(self):
        base = {'spline': self.x.copy(), 'linear': self.x.copy()}
        first = next(walk_forward(base, self.months, initial_train=24))
        for v in base.values():
            v[24:] = np.nan  # even missing future data cannot select training rows
        changed = next(walk_forward(base, self.months, initial_train=24))
        for key in ('forecast_log', 'mean', 'phi', 'loadings'):
            np.testing.assert_array_equal(first['fits']['spline'][key], changed['fits']['spline'][key])
        np.testing.assert_array_equal(first['train_indices'], changed['train_indices'])

    def test_grid_freezes_from_initial_training_only(self):
        s = [dict(axes=[np.array([.9,1.1]), np.array([.2,1.])]) for _ in range(30)]
        before = freeze_axes(s)
        s[24]['axes'] = [np.array([.99,1.01]), np.array([.3,.4])]
        after = freeze_axes(s)
        for a,b in zip(before,after):
            np.testing.assert_array_equal(a,b)
        s[2]['axes'][0] = np.array([1.2,1.3])
        with self.assertRaisesRegex(ValueError,'no common domain'):
            freeze_axes(s)

    def test_ar1_known_rank_one_process(self):
        score = np.array([.75**t for t in range(20)])
        loading = np.array([1.,2.,-1.])
        x = -1.5 + score[:,None]*loading
        fit = fit_pca_ar1(x,np.arange(len(x)),1)
        np.testing.assert_allclose(fit['phi'],[.75],atol=1e-12)
        np.testing.assert_allclose(fit['forecast_log'], -1.5 + .75**20*loading, atol=1e-12)

    def test_pca_mean_scores_and_orthogonality(self):
        fit = fit_pca_ar1(self.x, self.months)
        np.testing.assert_allclose(fit['mean'], self.x.mean(axis=0))
        np.testing.assert_allclose(fit['loadings'].T@fit['loadings'],np.eye(3),atol=1e-14)
        np.testing.assert_allclose(fit['scores'].mean(axis=0),0.,atol=1e-14)
        self.assertLessEqual(sum(fit['explained_ratio']),1.)

    def test_missing_month_not_compressed_into_ar_pair(self):
        x = np.delete(self.x,10,axis=0); months = np.delete(self.months,10)
        fit = fit_pca_ar1(x,months)
        self.assertEqual(fit['ar_pairs'],37)
        scores = fit['scores']; keep = np.diff(months)==1
        for j in range(3):
            b=np.linalg.lstsq(np.column_stack([np.ones(37),scores[:-1,j][keep]]),scores[1:,j][keep],rcond=None)[0]
            np.testing.assert_allclose([fit['intercept'][j],fit['phi'][j]],b)

    def test_common_training_dates_and_invalid_origin(self):
        logs = dict(spline=self.x.copy(),linear=self.x.copy())
        logs['spline'][10,0] = np.nan
        fold=next(walk_forward(logs,self.months,initial_train=24))
        self.assertNotIn(10,fold['train_indices'])
        self.assertEqual(fold['fits']['linear']['ar_pairs'],21)
        logs['spline'][23,0] = np.nan
        self.assertEqual(next(walk_forward(logs,self.months,initial_train=24))['status'],'skipped')

    def test_calendar_gap_target_is_skipped(self):
        months=self.months.copy();months[24:]+=1
        fold=next(walk_forward({'spline':self.x},months,initial_train=24))
        self.assertEqual(fold['reason'],'nonadjacent target month')

    def test_window_and_training_end(self):
        fold=list(walk_forward({'linear':self.x},self.months,initial_train=24,window=12))[-1]
        self.assertEqual(fold['train_indices'].tolist(),list(range(27,39)))
        self.assertEqual(fold['target'],39)

    def test_nonpositive_policies_do_not_fill_missing_support(self):
        iv=np.array([[.2,0.,-.1,np.nan,.00001]])
        linear=np.full_like(iv,.3)
        strict,a=log_surfaces(iv)
        self.assertEqual(a['nonpositive'],2)
        self.assertTrue(np.isnan(strict[0,1:4]).all())
        repaired,b=log_surfaces(iv,'linear_fallback',fallback=linear)
        np.testing.assert_allclose(repaired[0,1:3],np.log(.3))
        self.assertTrue(np.isnan(repaired[0,3]))
        self.assertEqual(b['repaired'],2)
        floored,c=log_surfaces(iv,'floor',floor=.01)
        self.assertEqual(c['repaired'],3)
        self.assertTrue(np.isnan(floored[0,3]))

    def test_interpolate_then_log_is_not_log_then_interpolate(self):
        iv=np.array([.1,.4])
        a=np.log(iv.mean());b=np.log(iv).mean()
        self.assertGreater(abs(a-b),.1)
        result,_=log_surfaces(np.array([iv.mean()]))
        self.assertAlmostEqual(result[0],a)

    def test_subspace_invariant_to_sign_permutation_and_rotation(self):
        a=np.linalg.qr(self.rng.normal(size=(12,3)))[0]
        rotation=np.linalg.qr(self.rng.normal(size=(3,3)))[0]
        result=subspace_distance(a,a@rotation)
        self.assertLess(result['projector_distance'],1e-14)
        self.assertLess(result['max_angle_degrees'],2e-6)

    def test_common_quote_operator_is_bilinear_in_log_and_uses_F_order(self):
        axes=[np.array([.9,1.1]),np.array([.1,1.])]
        x,t=np.meshgrid(*axes,indexing='ij'); z=-2+x*.1+t*.2+x*t*.1
        q=np.array([[1.,.5]])
        actual=evaluate_at_quotes(z.ravel(order='F'),axes,q)
        np.testing.assert_allclose(actual,np.exp(-2+.1+.1+.05),atol=1e-14)
        mask=quote_mask(dict(quote_q=np.array([[1.,.5],[1.2,.5]])),axes)
        self.assertEqual(mask.tolist(),[True,False])

    def test_failed_forecasts_are_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError,'Nonfinite'):
            error_stats(np.array([np.nan]),np.array([.2]))

    def test_native_import_rejects_false_evidence(self):
        expected=dict(forecast_log=[1.,2.],projector=[[1.,0.],[0.,1.]],phi=[.5],explained_ratio=[1.])
        f=dict(fixture_id='test',payload=dict(cases=[dict(name='one',expected=expected)]))
        r=dict(fixture_id='test',engine='R',engine_version='test',cases=[dict(name='one',**expected)])
        self.assertTrue(compare_native(r,f,'R')['passed'])
        bad=copy.deepcopy(r);bad['cases'][0]['forecast_log'][0]=10.
        self.assertFalse(compare_native(bad,f,'R')['passed'])
        for mutation in ('identity','missing','duplicate','shape'):
            bad=copy.deepcopy(r)
            if mutation=='identity':bad['engine']='MATLAB'
            if mutation=='missing':bad['cases']=[]
            if mutation=='duplicate':bad['cases']*=2
            if mutation=='shape':bad['cases'][0]['projector']=[1.,2.]
            with self.assertRaises(ValueError):compare_native(bad,f,'R')


if __name__=='__main__':
    unittest.main()
