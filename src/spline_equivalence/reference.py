"""Independent construction: second derivatives and piecewise cubics.

No SciPy interpolation code is used. Float algebra uses numpy.linalg.solve;
the exact construction uses fractions.Fraction and Gauss-Jordan elimination.
See docs/PROOF.md for the equations and the nonsingularity proof.
"""
from fractions import Fraction as F
import itertools
import numpy as np
from .core import validate


def systems(x, exact=False):
    x = [F(t) for t in x] if exact else list(map(float, x))
    n = len(x)
    if n < 4 or any(x[i+1] <= x[i] for i in range(n-1)):
        raise ValueError("Need >=4 increasing nodes")
    z = F(0) if exact else 0.0
    A = [[z for _ in x] for _ in x]
    B = [[z for _ in x] for _ in x]
    h = [x[i+1]-x[i] for i in range(n-1)]
    A[0][:3] = [-h[1], h[0]+h[1], -h[0]]
    A[-1][-3:] = [-h[-1], h[-2]+h[-1], -h[-2]]
    for i in range(1,n-1):
        A[i][i-1:i+2] = [h[i-1], 2*(h[i-1]+h[i]), h[i]]
        B[i][i-1:i+2] = [6/h[i-1], -6*(1/h[i-1]+1/h[i]), 6/h[i]]
    return x,h,A,B


def rational_solve(A,B):
    """Exact Gauss-Jordan elimination with multiple right-hand sides."""
    n = len(A)
    a = [[F(v) for v in row+rhs] for row,rhs in zip(A,B)]
    for k in range(n):
        p = next((i for i in range(k,n) if a[i][k]), None)
        if p is None:
            raise ValueError("Singular exact system")
        a[k],a[p] = a[p],a[k]
        v = a[k][k]
        a[k] = [t/v for t in a[k]]
        for i in range(n):
            if i != k:
                v = a[i][k]
                a[i] = [u-v*w for u,w in zip(a[i],a[k])]
    return [row[n:] for row in a]


def coefficient_basis(x, exact=False):
    """Return coefficients [interval, power 0..3, data-node]."""
    x,h,A,B = systems(x,exact)
    M = rational_solve(A,B) if exact else np.linalg.solve(A,B)
    n = len(x)
    eye = [[F(int(i==j)) if exact else float(i==j) for j in range(n)] for i in range(n)]
    c=[]
    for i,step in enumerate(h):
        c.append([eye[i],
            [(eye[i+1][j]-eye[i][j])/step-step*(2*M[i][j]+M[i+1][j])/6 for j in range(n)],
            [M[i][j]/2 for j in range(n)],
            [(M[i+1][j]-M[i][j])/(6*step) for j in range(n)]])
    return c if exact else np.asarray(c)


def weights(x, queries, exact=False):
    xx = [F(t) for t in x] if exact else np.asarray(x,float)
    c = coefficient_basis(xx,exact)
    rows=[]
    for q in queries:
        q = F(q) if exact else float(q)
        i = min(len(xx)-2,max(0,sum(t<=q for t in xx)-1))
        t=q-xx[i]
        rows.append([sum(c[i][k][j]*t**k for k in range(4)) for j in range(len(xx))])
    return rows if exact else np.asarray(rows)


def tensor_reference(axes,values,queries,fill_value=np.nan):
    axes,values,queries=validate(axes,values,queries)
    w=[weights(a,queries[:,j]) for j,a in enumerate(axes)]
    out=np.tensordot(w[0],values,axes=(1,0))
    for wj in w[1:]:
        out=np.einsum('qi,qi...->q...',wj,out)
    if fill_value is not None:
        outside=np.any(np.column_stack([(queries[:,j]<a[0])|(queries[:,j]>a[-1]) for j,a in enumerate(axes)]),axis=1)
        out[outside]=fill_value
    return out


def exact_tensor(axes,values,queries):
    """Exact values at rational queries; educational small fixtures only."""
    values=np.asarray(values,dtype=object)
    indices=list(itertools.product(*(range(len(a)) for a in axes)))
    ws=[weights(a,[q[j] for q in queries],True) for j,a in enumerate(axes)]
    out=[]
    for k in range(len(queries)):
        total=F(0)
        for ind in indices:
            term=F(values[ind])
            for j,i in enumerate(ind):term*=ws[j][k][i]
            total+=term
        out.append(total)
    return out
