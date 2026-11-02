#!/usr/bin/env python3
"""Compare new methods with independent 50-digit Decimal references and native engines."""
import argparse
from bisect import bisect_right
from decimal import Decimal as D, localcontext
from itertools import product
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from spline_equivalence import interpolate_surface, nadaraya_watson
from verify import compare, read_fixtures, validate_engine


def sample_points(c):
    if c['kind'] == 'scattered':
        return np.asarray(c['points'], float)
    return np.column_stack([g.ravel(order='F') for g in np.meshgrid(*c['axes'], indexing='ij')])


def decimal_reference(c):
    """Corner sum or Gaussian weighted mean; no SciPy or project method calls."""
    y = [D(str(v)) for v in c['values']]
    ans = []
    with localcontext() as ctx:
        ctx.prec = 50
        for query in c['queries']:
            q = [D(str(v)) for v in query]
            if c['kind'] == 'grid':
                axes = [[D(str(v)) for v in a] for a in c['axes']]
                if any(t < a[0] or t > a[-1] for t, a in zip(q, axes)):
                    ans.append(np.nan if c['fill'] == 'nan' else c['fill']); continue
            if c['method'] == 'linear':
                cells = [min(bisect_right(a, t)-1, len(a)-2) for t, a in zip(q, axes)]
                frac = [(t-a[k])/(a[k+1]-a[k]) for t, a, k in zip(q, axes, cells)]
                total = D(0)
                for corner in product((0, 1), repeat=len(q)):
                    weight = D(1); index = 0; stride = 1
                    for j, bit in enumerate(corner):
                        weight *= frac[j] if bit else 1-frac[j]
                        index += (cells[j]+bit)*stride; stride *= len(axes[j])
                    total += weight*y[index]
            else:
                h = [D(str(v)) for v in c['bandwidth']]
                points = [[D(str(v)) for v in p] for p in sample_points(c)]
                lw = [-sum(((t-x)/b)**2 for t, x, b in zip(q, p, h))/2 for p in points]
                peak = max(lw); w = [(v-peak).exp() for v in lw]
                total = sum(a*b for a, b in zip(w, y))/sum(w)
            ans.append(float(total))
    return np.array(ans)


def evaluate(c):
    q = np.array(c['queries'])
    if c['kind'] == 'scattered':
        return nadaraya_watson(c['points'], c['values'], q, c['bandwidth'])
    v = np.array(c['values']).reshape(c['shape'], order='F')
    return interpolate_surface(c['axes'], v, q, method=c['method'],
        bandwidth=c['bandwidth'] if c['method']=='nadaraya_watson' else None,
        fill_value=np.nan if c['fill']=='nan' else c['fill'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT/'results/methods')
    ap.add_argument('--python-only', action='store_true')
    ap.add_argument('--matlab-results', type=Path)
    ap.add_argument('--require', nargs='*', default=[], choices=['Octave','R','MATLAB'])
    args = ap.parse_args(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    path = ROOT/'fixtures/methods.json'; fixtures = read_fixtures(path)
    refs = {c['name']:decimal_reference(c) for c in fixtures['payload']['cases']}
    rows = []; pyrows = []
    for c in fixtures['payload']['cases']:
        y = evaluate(c)
        row = dict(name=c['name'], method=c['method'], queries=len(y),
                   reference=compare(y, refs[c['name']]), engines={})
        if c.get('node_count'):
            row['nodes'] = compare(y[:c['node_count']], c['values'])
        rows.append(row)
        pyrows.append(dict(name=c['name'], values=[float(v) if np.isfinite(v) else None for v in y]))
    engines = {}
    for engine, binary in [('Octave','octave-cli'), ('R','Rscript'), ('MATLAB','matlab')]:
        imported = args.matlab_results if engine=='MATLAB' else None
        exe = None if args.python_only else shutil.which(binary)
        target = out/(engine.lower()+'.json')
        if imported:
            data = json.loads(imported.read_text()); target.write_bytes(imported.read_bytes()) if imported.resolve()!=target else None
        elif exe:
            if engine=='R': cmd = [exe, str(ROOT/'scripts/run_methods.R'), str(path), str(target)]
            else:
                quote = lambda p: "'"+str(p).replace("'", "''")+"'"
                expr = f"addpath({quote(ROOT/'scripts')});run_methods({quote(path)},{quote(target)});"
                cmd = [exe, '--no-init-file','--no-site-file','--no-history','--quiet','--eval', expr] if engine=='Octave' else [exe,'-batch',expr]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
            target.with_suffix('.log').write_text(run.stdout+run.stderr)
            if run.returncode: raise RuntimeError(f'{engine} failed; see {target.with_suffix(".log")}')
            data = json.loads(target.read_text())
        else:
            engines[engine] = dict(status='NOT RUN'); continue
        vals = validate_engine(data, engine, fixtures)
        engines[engine] = dict(status='RUN', version=data['engine_version'])
        for row in rows: row['engines'][engine] = compare(vals[row['name']], refs[row['name']])
    missing = [e for e in args.require if engines[e]['status']!='RUN']
    passed = not missing and all(r['reference']['passed'] and r.get('nodes',{'passed':True})['passed']
        and all(x['passed'] for x in r['engines'].values()) for r in rows)
    summary = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), fixture_id=fixtures['fixture_id'],
        cases=len(rows), queries=sum(r['queries'] for r in rows), python=platform.python_version(),
        reference='50-digit Decimal corner sums and Gaussian weighted means',
        absolute_tolerance=2e-11, relative_tolerance=2e-10, engines=engines,
        missing_required_engines=missing, passed=bool(passed), results=rows)
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    (out/'python.json').write_text(json.dumps(dict(engine='Python',engine_version=platform.python_version(),
        fixture_id=fixtures['fixture_id'], results=pyrows), indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='results'}, indent=2))
    return 0 if passed else 1


if __name__=='__main__': sys.exit(main())
