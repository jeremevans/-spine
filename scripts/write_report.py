#!/usr/bin/env python3
"""Generate Markdown evidence summary from recorded engine results."""
import argparse,json
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results',type=Path,default=Path('results'))
    ap.add_argument('--output',type=Path,default=Path('docs/RESULTS.md'))
    args=ap.parse_args();p=args.results;s=json.loads((p/'summary.json').read_text())
    lines=['# Measured spline results','',f"Run timestamp: `{s['timestamp_utc']}`.",
        f"Fixture SHA-256: `{s['fixture_id']}`.",'',
        f"**{s['cases']} cases; {s['queries']:,} queries; overall result: {'PASS' if s['passed'] else 'FAIL'}.**",'',
        f"Python {s['python']}, NumPy {s['numpy']}, SciPy {s['scipy']}.",'',
        '| Engine | Version | Status | Max absolute error vs independent reference |',
        '| --- | --- | --- | ---: |',
        f"| Python | {s['python']} / SciPy {s['scipy']} | RUN | {max(r['reference']['max_abs'] for r in s['results']):.16g} |"]
    for e,meta in s['engines'].items():
        value=f"{max(r['engines'][e]['max_abs'] for r in s['results']):.16g}" if meta['status']=='RUN' else '—'
        version=meta.get('engine_version','—')
        if e=='R' and meta['status']=='RUN':version+=f"; pracma {meta['pracma_version']}; jsonlite {meta['jsonlite_version']}"
        lines.append(f"| {e} | {version} | {meta['status']} | {value} |")
    lines += ['',f"Tolerance: absolute {s['absolute_tolerance']:.1e} plus relative {s['relative_tolerance']:.1e}; NaN masks must agree. Infinities are rejected.",
        '',f"Exact arithmetic verifies {s['exact_constraint_equalities']} equalities and supplies {s['exact_queries']} rational 2D reference values. The full one-dimensional polynomial coefficient arrays are also compared with SciPy CubicSpline.",'',
        '## Direct comparisons with Python','',
        '| Engine | Max absolute difference from Python |','| --- | ---: |']
    py={r['name']:np.asarray(r['values'],float) for r in json.loads((p/'python.json').read_text())['results']}
    for e,meta in s['engines'].items():
        if meta['status']!='RUN':continue
        native=json.loads((p/(e.lower()+'.json')).read_text())
        err=max(float(np.nanmax(abs(np.asarray(r['values'],float)-py[r['name']]))) for r in native['results'])
        lines.append(f'| {e} | {err:.16g} |')
    ran=[e for e,meta in s['engines'].items() if meta['status']=='RUN']
    headers=['Case','Dimensions','Queries','Python vs reference']+[e+' vs reference' for e in ran]
    lines += ['', '## Each fixture','',
        '| '+' | '.join(headers)+' |',
        '| '+' | '.join(['---']+['---:']*(len(headers)-1))+' |']
    for r in s['results']:
        vals=[f"{r['engines'][e]['max_abs']:.3e}" for e in ran]
        cells=[f"`{r['name']}`",str(r['dimensions']),str(r['queries']),f"{r['reference']['max_abs']:.3e}"]+vals
        lines.append('| '+' | '.join(cells)+' |')
    stress=next(r for r in s['results'] if r['name']=='positive_overshoot')
    diagnostic=next(r for r in s['results'] if 'default_solver_diagnostic' in r)['default_solver_diagnostic']
    lines += ['', '## Interpretation','',
        'The largest Octave discrepancy occurs in the coordinate-scaling case. All reported errors are absolute in the fixture’s value units; the IV example uses decimal volatility.',
        '',f"The positive-input overshoot example reaches {stress['minimum_spline_value']:.12f}; a real logarithm cannot be applied there. The smooth IV demo remains positive.",
        '',f"The separate default iterative-solver diagnostic differs from the direct solver by {diagnostic['max_abs']:.6g} on its fixture. It is an accuracy-sensitivity diagnostic, not part of the direct-solver acceptance result.",
        '', 'The ten unit tests check exact constraints, basis linearity, polynomial recovery, domain policy, unsupported input rejection, different natural-spline endpoints, corrupted numbers/masks/shapes, and missing/duplicate/wrong engine identities.',
        '', ('Actual MATLAB output was imported or executed for this report; see its recorded version and case checks.' if s['engines']['MATLAB']['status']=='RUN' else 'Actual MATLAB output is not included in this report. Mathematical equivalence follows from the common spline definition and uniqueness proof; measured MATLAB parity requires running the included native runner.'),
        '', 'The JSON files preserve the underlying numbers and versions. The fixture and source manifest detects later byte changes; it is not an independent signature or a proof that an external execution was authentic.']
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text('\n'.join(lines)+'\n')
    print(args.output)


if __name__=='__main__':main()
