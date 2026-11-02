#!/usr/bin/env python3
"""Verify exact reference, SciPy, and available Octave/R/MATLAB engines.

Missing engines are NOT RUN. --require makes missing evidence fail the run.
External imports validate engine, fixture identity, case identities and shapes.
"""
import argparse,hashlib,json,platform,shutil,subprocess,sys
from datetime import datetime,timezone
from fractions import Fraction as F
from pathlib import Path
import numpy as np
import scipy
from scipy.interpolate import CubicSpline,RegularGridInterpolator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from spline_equivalence import interpn_spline
from spline_equivalence.reference import tensor_reference,exact_tensor,coefficient_basis,weights
from make_fixtures import canonical

ATOL=2e-11
RTOL=2e-10


def compare(actual,expected):
    a,b=np.asarray(actual,dtype=float),np.asarray(expected,dtype=float)
    if a.shape!=b.shape:return {'passed':False,'reason':'shape mismatch'}
    masks=bool(np.array_equal(np.isnan(a),np.isnan(b)))
    finite=np.isfinite(a)&np.isfinite(b)
    no_inf=not (np.isinf(a).any() or np.isinf(b).any())
    err=np.abs(a[finite]-b[finite])
    return dict(passed=bool(masks and no_inf and np.all(err<=ATOL+RTOL*np.abs(b[finite]))),
        max_abs=float(np.max(err)) if err.size else 0.,finite_pairs=int(finite.sum()),matching_nan_masks=masks)


def read_fixtures(path=ROOT/'fixtures/splines.json'):
    obj=json.loads(path.read_text())
    if obj['fixture_id']!=hashlib.sha256(canonical(obj['payload'])).hexdigest():
        raise ValueError('Fixture fingerprint mismatch')
    return obj


def inputs(c):
    a=[np.array(x,float) for x in c['axes']]
    v=np.array(c['values']).reshape(c['shape'],order='F')
    q=np.array(c['queries'],float)
    fill=np.nan if c['fill']=='nan' else float(c['fill'])
    return a,v,q,fill


def validate_engine(data,engine,fixtures):
    if data.get('engine')!=engine or data.get('fixture_id')!=fixtures['fixture_id']:
        raise ValueError('Engine or fixture identity mismatch')
    rows=data['results']
    expected=[c['name'] for c in fixtures['payload']['cases']]
    names=[r['name'] for r in rows]
    if len(names)!=len(set(names)) or set(names)!=set(expected):
        raise ValueError('Missing, extra or duplicate case identity')
    mapping={r['name']:r['values'] for r in rows}
    for c in fixtures['payload']['cases']:
        if np.asarray(mapping[c['name']]).shape!=(len(c['queries']),):
            raise ValueError('Incorrect engine output shape')
    return mapping


def exact_checks(case):
    axes,values,q,_=inputs(case)
    axes=[[F(str(x)) for x in a] for a in axes]
    values=np.array([F(str(x)) for x in case['values']],dtype=object).reshape(case['shape'],order='F')
    queries=[[F(str(x)) for x in row] for row in q]
    exact=exact_tensor(axes,values,queries)
    constraints=0
    for a in axes:
        C=coefficient_basis(a,True);n=len(a)
        for i in range(n-1):
            h=a[i+1]-a[i]
            for j in range(n):
                assert C[i][0][j]==int(i==j);constraints+=1
                assert sum(C[i][p][j]*h**p for p in range(4))==int(i+1==j);constraints+=1
                if i<n-2:
                    assert sum(p*C[i][p][j]*h**(p-1) for p in range(1,4))==C[i+1][1][j];constraints+=1
                    assert sum(p*(p-1)*C[i][p][j]*h**(p-2) for p in range(2,4))==2*C[i+1][2][j];constraints+=1
        for j in range(n):
            assert C[0][3][j]==C[1][3][j];constraints+=1
            assert C[-1][3][j]==C[-2][3][j];constraints+=1
        # Compare full coefficients (not just sampled function values) to SciPy 1D.
        ref=np.array(C,float)
        got=CubicSpline(np.array(a,float),np.eye(n),axis=0,bc_type='not-a-knot').c[::-1].transpose(1,0,2)
        if not compare(got,ref)['passed']:raise AssertionError('CubicSpline coefficient mismatch')
    return dict(exact_constraint_equalities=constraints,exact_query_count=len(exact),
        answers=[str(x) for x in exact]),np.array(exact,float)


def run_external(engine,exe,out,fixtures_path):
    if engine=='R':cmd=[exe,str(ROOT/'scripts/run_r.R'),str(fixtures_path),str(out)]
    else:
        def mq(p):return "'"+str(p).replace("'","''")+"'"
        expr=f'addpath({mq(ROOT/"scripts")});run_engine({mq(fixtures_path)},{mq(out)});'
        cmd=[exe,'--no-init-file','--no-site-file','--no-history','--quiet','--eval',expr] if engine=='Octave' else [exe,'-batch',expr]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=600,cwd=ROOT)
    out.with_suffix('.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(f'{engine} failed; see {out.with_suffix(".log")}')
    return json.loads(out.read_text())


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'results')
    ap.add_argument('--require',nargs='*',choices=['Octave','R','MATLAB'],default=[])
    ap.add_argument('--matlab-results',type=Path)
    ap.add_argument('--octave-results',type=Path)
    ap.add_argument('--r-results',type=Path)
    ap.add_argument('--python-only',action='store_true')
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    fixtures=read_fixtures();cases=fixtures['payload']['cases']
    ex,exact_values=exact_checks(next(c for c in cases if c['name']=='rational_2d'))
    (out/'exact_reference.json').write_text(json.dumps(ex,indent=2)+'\n')
    rows=[];pyrows=[];refs={}
    for c in cases:
        a,v,q,fill=inputs(c)
        y=interpn_spline(a,v,q,fill_value=fill)
        ref=tensor_reference(a,v,q,fill)
        row=dict(name=c['name'],dimensions=len(a),queries=len(q),reference=compare(y,ref),engines={})
        # Axis-order independence, including nonseparable data.
        rev=tensor_reference(a[::-1],v.transpose(tuple(range(v.ndim-1,-1,-1))),q[:,::-1],fill)
        row['axis_order']=compare(rev,ref)
        if c.get('node_count'):
            row['node_recovery']=compare(y[:c['node_count']],v.ravel(order='F'))
        if c['kind']=='tensor_polynomial':
            truth=.2+sum(.01*(j+1)*q[:,j]**3 for j in range(len(a)))+.003*np.prod(1+q+q*q,axis=1)
            truth[~np.isfinite(y)]=np.nan
            row['polynomial']=compare(y,truth)
        if c['kind']=='exact_rational':row['rational']=compare(y,exact_values)
        if c['kind']=='overshoot':row['minimum_spline_value']=float(y.min())
        if c['kind']=='synthetic_iv':
            if not (y>0).all():raise AssertionError('Demo IV spline was not positive')
            row['log_comparison']=compare(np.log(y),np.log(ref))
        if c['name']=='2d_irregular_random':
            default=RegularGridInterpolator(a,v,method='cubic',bounds_error=False,fill_value=fill)(q)
            row['default_solver_diagnostic']=compare(default,y)
        rows.append(row);refs[c['name']]=ref
        pyrows.append(dict(name=c['name'],values=[float(x) if np.isfinite(x) else None for x in y]))
    engines={}
    for engine,binary,imported in [('Octave','octave-cli',args.octave_results),('R','Rscript',args.r_results),('MATLAB','matlab',args.matlab_results)]:
        exe=None if args.python_only else shutil.which(binary)
        if imported:data=json.loads(imported.read_text())
        elif exe:
            print(f'Running {engine}...',flush=True)
            data=run_external(engine,exe,out/(engine.lower()+'.json'),ROOT/'fixtures/splines.json')
        else:
            engines[engine]={'status':'NOT RUN'}
            continue
        vals=validate_engine(data,engine,fixtures)
        engines[engine]={k:v for k,v in data.items() if k!='results'}
        engines[engine]['status']='RUN'
        if imported:(out/(engine.lower()+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        for row in rows:row['engines'][engine]=compare(vals[row['name']],refs[row['name']])
    python_data=dict(engine='Python',engine_version=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,fixture_id=fixtures['fixture_id'],results=pyrows)
    (out/'python.json').write_text(json.dumps(python_data,indent=2,allow_nan=False)+'\n')
    def passed(row):
        keys=['reference','axis_order','node_recovery','polynomial','rational','log_comparison']
        return all(row[k]['passed'] for k in keys if k in row) and all(c['passed'] for c in row['engines'].values())
    missing=[engine for engine in args.require if engines[engine]['status']!='RUN']
    summary=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),fixture_id=fixtures['fixture_id'],
        python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,engines=engines,
        absolute_tolerance=ATOL,relative_tolerance=RTOL,cases=len(rows),queries=sum(c['queries'] for c in rows),
        exact_constraint_equalities=ex['exact_constraint_equalities'],exact_queries=ex['exact_query_count'],
        missing_required_engines=missing,passed=bool(not missing and all(map(passed,rows))),results=rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    brief={k:summary[k] for k in ['cases','queries','exact_constraint_equalities','exact_queries','passed','missing_required_engines']}
    brief['engines']={k:v['status'] for k,v in engines.items()}
    brief['max_python_vs_reference']=max(r['reference']['max_abs'] for r in rows)
    for e in engines:
        if engines[e]['status']=='RUN':brief['max_'+e+'_vs_reference']=max(r['engines'][e]['max_abs'] for r in rows)
    print(json.dumps(brief,indent=2))
    return 0 if summary['passed'] else 1


if __name__=='__main__':sys.exit(main())
