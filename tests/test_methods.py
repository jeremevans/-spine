import copy
import math
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from spline_equivalence import interpn_spline, interpn_linear, nadaraya_watson, interpolate_surface
from verify import read_fixtures, validate_engine


class MethodTests(unittest.TestCase):
    def test_linear_multiaffine_and_axis_order(self):
        a=[np.array([0.,.4,2.]),np.array([-2.,1.]),np.array([1.,2.,5.]),np.array([0.,3.])]
        f=lambda x: .2+.03*x[0]-.01*x[1]*x[2]+.002*np.prod(x,axis=0)
        v=f(np.array(np.meshgrid(*a,indexing='ij')))
        q=np.array([[.2,-.3,1.4,.5],[1.3,.8,4.4,2.]])
        np.testing.assert_allclose(interpn_linear(a,v,q),f(q.T),atol=2e-16)
        np.testing.assert_allclose(interpn_linear(a[::-1],v.transpose(3,2,1,0),q[:,::-1]),f(q.T))

    def test_bilinear_is_not_triangulated(self):
        self.assertAlmostEqual(interpn_linear([[0.,1.],[0.,1.]],np.array([[0.,0.],[0.,1.]]),[[.25,.5]])[0],.125)

    def test_linear_nodes_fill_and_extrapolation(self):
        a=[[0.,2.]]; v=[.1,.5]; q=[[-1.],[0.],[1.],[2.],[3.]]
        np.testing.assert_allclose(interpn_linear(a,v,q),[np.nan,.1,.3,.5,np.nan],equal_nan=True)
        np.testing.assert_allclose(interpn_linear(a,v,q,fill_value=-7),[-7,.1,.3,.5,-7])
        np.testing.assert_allclose(interpn_linear(a,v,q,fill_value=None),[-.1,.1,.3,.5,.7])

    def test_nw_closed_form_and_smoothing_at_nodes(self):
        p=[[0.],[1.]]; y=[.1,.9]; q=[[0.],[.25],[.5]]; h=.7
        expected=[]
        for x in [0.,.25,.5]:
            r=math.exp(-((x-1)**2-x*x)/(2*h*h))
            expected.append((.1+r*.9)/(1+r))
        got=nadaraya_watson(p,y,q,h)
        np.testing.assert_allclose(got,expected,atol=2e-16)
        self.assertGreater(got[0],y[0]); self.assertAlmostEqual(got[-1],.5)

    def test_nw_units_chunking_and_permutation(self):
        rng=np.random.default_rng(8); p=rng.normal(size=(11,3));q=rng.normal(size=(17,3));y=rng.random(11)
        h=np.array([.3,1.,2.]);scale=np.array([100.,.5,7.]);offset=np.array([2.,8.,-5.])
        expected=nadaraya_watson(p,y,q,h,chunk_size=1)
        np.testing.assert_allclose(nadaraya_watson(p*scale+offset,y,q*scale+offset,h*scale,chunk_size=6),expected,atol=1e-14)
        np.testing.assert_allclose(nadaraya_watson(p[::-1],y[::-1],q,h),expected,atol=2e-16)

    def test_nw_underflow_and_large_values(self):
        np.testing.assert_allclose(nadaraya_watson([[0.],[1.]],[.1,.9],[[1000.],[-1000.]],.001),[.9,.1])
        self.assertTrue(np.isfinite(nadaraya_watson([[0.],[1.]],[1e308,1e308],[[.5]],1.)).all())
        with self.assertRaises(ValueError):nadaraya_watson([[1e308]], [.2], [[-1e308]], 1e-300)

    def test_nw_constant_single_sample_empty_and_duplicates(self):
        np.testing.assert_allclose(nadaraya_watson([[2.,3.]],[.23],[[4.,5.],[0.,0.]],[.4,2.]),.23)
        self.assertEqual(nadaraya_watson([[0.]],[1.],np.empty((0,1)),1.).shape,(0,))
        self.assertAlmostEqual(nadaraya_watson([[0.],[0.],[0.]],[0.,0.,.9],[[0.]],1.)[0],.3)

    def test_positive_convex_results_and_log_order(self):
        x=np.linspace(0,1,4);y=np.array([.1,.8,.2,.9]);q=np.linspace(0,1,51)[:,None]
        for method in ['linear','nadaraya_watson']:
            kwargs=dict(method=method,bandwidth=.3 if method=='nadaraya_watson' else None)
            a=interpolate_surface([x],y,q,**kwargs)
            self.assertGreaterEqual(a.min(),y.min()-1e-15);self.assertLessEqual(a.max(),y.max()+1e-15)
            self.assertTrue(np.isfinite(np.log(a)).all())
            b=interpolate_surface([x],np.log(y),q,**kwargs)
            self.assertGreater(np.max(abs(np.log(a)-b)),.01)

    def test_grid_nw_order_and_boundary_policy(self):
        a=[[0.,1.],[0.,2.]];v=np.array([[.1,.2],[.3,.9]]);q=np.array([[.3,.7],[2.,4.]])
        p=[[0.,0.],[1.,0.],[0.,2.],[1.,2.]]
        expected=nadaraya_watson(p,[.1,.3,.2,.9],q,[.2,1.])
        got=interpolate_surface(a,v,q,method='nadaraya_watson',bandwidth=[.2,1.])
        self.assertAlmostEqual(got[0],expected[0]);self.assertTrue(np.isnan(got[1]))
        np.testing.assert_allclose(interpolate_surface(a,v,q,method='nadaraya_watson',bandwidth=[.2,1.],fill_value=None),expected)

    def test_selector_preserves_spline_and_rejects_unused_parameters(self):
        a=[np.arange(4.)];v=[.2,.1,.5,.3];q=[[.7],[2.5]]
        np.testing.assert_array_equal(interpolate_surface(a,v,q),interpn_spline(a,v,q))
        for kwargs in [dict(method='cubic'),dict(method='linear',bandwidth=1.),dict(method='nadaraya_watson')]:
            with self.assertRaises(ValueError):interpolate_surface(a,v,q,**kwargs)

    def test_bad_inputs(self):
        for h in [0.,-1.,np.nan,np.inf,[],[1.,2.],1j]:
            with self.subTest(h=h),self.assertRaises(ValueError):nadaraya_watson([[0.],[1.]],[.1,.2],[[.5]],h)
        for p,y,q in [([],[],[[0.]]),([[0.]],[np.nan],[[0.]]),([[0.]],[1.],[[0.,1.]]),([[0.]],[1.,2.],[[0.]]),([[0j]],[1.],[[0.]])]:
            with self.assertRaises(ValueError):nadaraya_watson(p,y,q,1.)
        for chunk in [0,-1,1.5]:
            with self.assertRaises(ValueError):nadaraya_watson([[0.]],[1.],[[0.]],1.,chunk_size=chunk)
        for a,v,q in [([[0.]],[1.],[[0.]]),([[0.,0.]],[1.,2.],[[0.]]),([[0.,1.]],[1.,np.nan],[[.5]])]:
            with self.assertRaises(ValueError):interpn_linear(a,v,q)

    def test_method_import_rejects_wrong_fixtures_and_missing_cases(self):
        f=read_fixtures(ROOT/'fixtures/methods.json')
        good=dict(engine='MATLAB',fixture_id=f['fixture_id'],results=[dict(name=c['name'],values=[0.]*len(c['queries'])) for c in f['payload']['cases']])
        validate_engine(good,'MATLAB',f)
        for key in ['hash','missing']:
            bad=copy.deepcopy(good)
            if key=='hash':bad['fixture_id']='wrong'
            else:bad['results'].pop()
            with self.assertRaises(ValueError):validate_engine(bad,'MATLAB',f)


if __name__=='__main__':unittest.main()
