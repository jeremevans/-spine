#!/usr/bin/env python3
"""Generate deterministic, public-domain synthetic fixtures; no market data."""
import hashlib,itertools,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def make_cases():
    rng=np.random.default_rng(20261101)
    cases=[]
    def add(name,axes,v,q,**kw):
        cases.append(dict(name=name,axes=[np.asarray(a).tolist() for a in axes],
            shape=list(np.shape(v)),values=np.asarray(v).ravel(order='F').tolist(),
            queries=np.asarray(q).tolist(),fill='nan',**kw))
    for d in range(1,5):
        for kind in ['uniform_random','irregular_random','tensor_polynomial']:
            axes=[]
            for j in range(d):
                a=np.arange(4+j%2,dtype=float) if kind=='uniform_random' else np.r_[0,np.cumsum(rng.uniform(.4,1.7,3+j%2))]
                axes.append(a/a[-1])
            g=np.meshgrid(*axes,indexing='ij')
            v=(.2+sum(.01*(j+1)*a**3 for j,a in enumerate(g))+.003*np.prod([1+a+a*a for a in g],axis=0)) if kind=='tensor_polynomial' else rng.uniform(.08,.7,tuple(map(len,axes)))
            nodes=np.column_stack([a.ravel(order='F') for a in g])
            q=np.vstack([nodes,rng.uniform(0,1,(61,d)),np.full((1,d),-.01),np.full((1,d),1.01)])
            add(f'{d}d_{kind}',axes,v,q,kind=kind,node_count=len(nodes))
    # Exhaust every data basis vector on a 5x5 irregular grid.
    axes=[np.array([0,.2,.7,1.2,2]),np.array([-1,-.4,.1,.8,2])]
    q=rng.uniform([0,-1],[2,2],(31,2))
    for k in range(25):
        v=np.eye(25)[k].reshape((5,5),order='F')
        add(f'basis_5x5_{k:02}',axes,v,q,kind='basis_vector',basis_index=k)
    # A non-polynomial rational fixture with independently exact answers.
    axes=[np.array([0,1,2,4,7]),np.array([-2,0,1,3,4,6])]
    v=np.array([[((i+2)*(j+3)%11+10)/100 for j in range(6)] for i in range(5)])
    q=np.array(list(itertools.product([0,.25,1.5,3.25,6.75,7],[-2,-1.25,.5,2.5,5.5,6])))
    add('rational_2d',axes,v,q,kind='exact_rational')
    # Smooth, positive, synthetic IV example with skew and term structure.
    m=np.array([.7,.82,.94,1.,1.13,1.3,1.5]);t=np.array([.04,.12,.3,.65,1.2,2.])
    M,T=np.meshgrid(m,t,indexing='ij')
    v=.16+.1*np.exp(-T)+.32*(M-1)**2-.055*(M-1)+.008*np.sin(5*M*T)
    mq=np.linspace(m[0],m[-1],81);tq=np.linspace(t[0],t[-1],61)
    g=np.meshgrid(mq,tq,indexing='ij')
    q=np.column_stack([a.ravel(order='F') for a in g])
    add('volatility_surface', [m,t],v,q,kind='synthetic_iv',query_shape=[81,61])
    axes=[np.arange(6.),np.arange(4.)]
    v=np.repeat(np.array([.04,.04,.6,.04,.04,.04])[:,None],4,axis=1)
    q=np.column_stack([np.linspace(0,5,501),np.full(501,1.25)])
    add('positive_overshoot',axes,v,q,kind='overshoot')
    # Coordinate units are deliberately very different, but data unchanged.
    base=cases[4]
    axes=[np.array(base['axes'][0])*1e3+1e5,np.array(base['axes'][1])*.001]
    q=np.array(base['queries']);q[:,0]=q[:,0]*1e3+1e5;q[:,1]*=.001
    add('coordinate_scaling',axes,np.array(base['values']).reshape(base['shape'],order='F'),q,kind='coordinate_scaling')
    # Explicit numeric outside fill, separate from NaN missing-mask tests.
    case={**cases[3],'name':'constant_outside_fill','fill':-777.0}
    cases.append(case)
    return cases


def main():
    payload={'schema_version':1,'seed':20261101,'order':'F','cases':make_cases()}
    obj={'fixture_id':hashlib.sha256(canonical(payload)).hexdigest(),'payload':payload}
    path=ROOT/'fixtures/splines.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
    print(f'{len(payload["cases"])} cases -> {path}')


if __name__=='__main__':main()
