"""Exact worked example from docs/PROOF.md; run from any working directory."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from spline_equivalence import interpn_spline

x=np.array([0,1,2,4,7.]);y=np.array([-2,0,1,3,4,6.])
i,j=np.indices((5,6));values=(10+((i+2)*(j+3))%11)/100
q=np.array([[1.5,.5],[3.25,2.5],[6.75,5.5]])
actual=interpn_spline((x,y),values,q)
expected=np.array([838733/5632000,2031089/13926400,10632481/69632000])
np.testing.assert_allclose(actual,expected,atol=2e-14,rtol=2e-13)
print(actual)
