import copy,json,sys,unittest
from pathlib import Path
from fractions import Fraction as F
import numpy as np
from scipy.interpolate import CubicSpline
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from spline_equivalence import interpn_spline
from spline_equivalence.reference import exact_tensor,coefficient_basis,tensor_reference,weights
from verify import compare,read_fixtures,validate_engine,exact_checks


class SplineTests(unittest.TestCase):
    def setUp(self):
        self.axes=[np.array([0.,.3,1.,2.,3.]),np.array([-1.,0.,.5,2.])]
        self.v=np.random.default_rng(9).uniform(.1,.8,(5,4))
        self.q=np.array([[.1,-.4],[1.3,.9],[3.,2.]])

    def test_independent_construction(self):
        self.assertTrue(compare(interpn_spline(self.axes,self.v,self.q),tensor_reference(self.axes,self.v,self.q))['passed'])

    def test_exact_constraints_and_answers(self):
        c=next(c for c in read_fixtures()['payload']['cases'] if c['name']=='rational_2d')
        report,values=exact_checks(c)
        self.assertEqual(report['exact_constraint_equalities'],200)
        self.assertEqual(len(values),36)

    def test_constant_partition_of_unity(self):
        w=weights([F(0),F(1),F(2),F(4),F(7)],[F(1,3),F(9,2)],True)
        self.assertEqual([sum(row) for row in w],[F(1),F(1)])

    def test_tensor_cubic_reproduction(self):
        g=np.meshgrid(*self.axes,indexing='ij')
        f=lambda x,y: 2+x**3-.3*y**2+.5*x*x*y**3
        v=f(*g)
        self.assertTrue(compare(interpn_spline(self.axes,v,self.q),f(*self.q.T))['passed'])

    def test_basis_linearity(self):
        # Full data basis on this fixed grid, combined with arbitrary coefficients.
        mats=[]
        for k in range(self.v.size):
            e=np.eye(self.v.size)[k].reshape(self.v.shape,order='F')
            mats.append(interpn_spline(self.axes,e,self.q))
        reconstructed=np.column_stack(mats)@self.v.ravel(order='F')
        self.assertTrue(compare(reconstructed,interpn_spline(self.axes,self.v,self.q))['passed'])

    def test_outside_policy(self):
        q=np.array([[0.,-1.],[3.,2.],[-.1,0.],[1.,2.1]])
        a=interpn_spline(self.axes,self.v,q)
        self.assertTrue(np.isfinite(a[:2]).all());self.assertTrue(np.isnan(a[2:]).all())
        b=interpn_spline(self.axes,self.v,q,fill_value=-7.)
        np.testing.assert_array_equal(b[2:],[-7.,-7.])
        e=interpn_spline(self.axes,self.v,q,fill_value=None)
        self.assertTrue(compare(e,tensor_reference(self.axes,self.v,q,None))['passed'])

    def test_natural_spline_is_not_equivalent(self):
        a=self.axes[0];v=self.v[:,0];q=np.linspace(a[0],a[-1],101)
        natural=CubicSpline(a,v,bc_type='natural')(q)
        nak=CubicSpline(a,v,bc_type='not-a-knot')(q)
        self.assertGreater(np.max(np.abs(natural-nak)),1e-3)

    def test_rejects_unsupported_inputs(self):
        bad=[([np.arange(3.),self.axes[1]],self.v,self.q),
             ([self.axes[0][::-1],self.axes[1]],self.v,self.q),
             (self.axes,self.v.T,self.q),
             (self.axes,self.v.astype(complex),self.q),
             (self.axes,np.full(self.v.shape,np.nan),self.q),
             (self.axes,self.v,[np.nan,0]),
             ([np.array([0.,1.,1.,2.,3.]),self.axes[1]],self.v,self.q)]
        for a,v,q in bad:
            with self.subTest(axes=a),self.assertRaises(ValueError):interpn_spline(a,v,q)

    def test_comparator_rejects_corruption(self):
        for a,b in [([1.],[2.]),([np.nan],[1.]),([[1.]],[1.]),([np.inf],[np.inf])]:
            self.assertFalse(compare(a,b)['passed'])

    def test_engine_import_rejects_bad_evidence(self):
        fixtures=read_fixtures()
        good=dict(engine='MATLAB',fixture_id=fixtures['fixture_id'],results=[dict(name=c['name'],values=[0.]*len(c['queries'])) for c in fixtures['payload']['cases']])
        validate_engine(good,'MATLAB',fixtures)
        for mutation in ['engine','hash','duplicate','missing','shape']:
            d=copy.deepcopy(good)
            if mutation=='engine':d['engine']='Octave'
            if mutation=='hash':d['fixture_id']='wrong'
            if mutation=='duplicate':d['results'].append(d['results'][0])
            if mutation=='missing':d['results'].pop()
            if mutation=='shape':d['results'][0]['values']=[[0.]]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_engine(d,'MATLAB',fixtures)


if __name__=='__main__':unittest.main()
