#!/usr/bin/env python3
"""Validate independent native PCA/AR1 computations; absent engines are NOT RUN."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from make_fixtures import canonical

ROOT = Path(__file__).resolve().parents[1]
ATOL, RTOL = 2e-9, 2e-8


def compare_native(raw, fixture, engine):
    if (raw.get('engine') != engine or not raw.get('engine_version')
            or raw.get('fixture_id') != fixture['fixture_id']):
        raise ValueError('Wrong engine, missing version or fixture identity')
    rows = raw.get('cases', [])
    if isinstance(rows, dict):
        rows = [rows]
    names = [r['name'] for r in rows]
    expected = {c['name']: c['expected'] for c in fixture['payload']['cases']}
    if len(names) != len(set(names)) or set(names) != set(expected):
        raise ValueError('Missing, extra or duplicate native cases')
    maxima = {key: 0. for key in ('forecast_log', 'projector', 'phi', 'explained_ratio')}
    passed = True
    for row in rows:
        for key, truth in expected[row['name']].items():
            a, b = np.asarray(row[key], float), np.asarray(truth, float)
            # Native JSON may flatten a singleton vector.
            if b.ndim == 1:
                a = a.reshape(-1)
            if a.shape != b.shape or not np.isfinite(a).all():
                raise ValueError(f'Invalid native shape/values: {row["name"]}/{key}')
            error = np.max(abs(a-b))
            maxima[key] = max(maxima[key], float(error))
            passed &= bool(np.all(abs(a-b) <= ATOL + RTOL * abs(b)))
    return dict(status='RUN', version=raw['engine_version'], cases=len(rows),
                max_abs=maxima, passed=passed)


def verify_forecast(fixture_path, output, require=(), skip_engines=False, matlab_results=None):
    fixture = json.loads(Path(fixture_path).read_text())
    if hashlib.sha256(canonical(fixture['payload'])).hexdigest() != fixture['fixture_id']:
        raise ValueError('Fixture fingerprint mismatch')
    reports = {}
    for engine, binary in [('Octave', 'octave-cli'), ('R', 'Rscript')]:
        executable = shutil.which(binary)
        if skip_engines or not executable:
            reports[engine] = dict(status='NOT RUN', passed=False)
            continue
        target = output / f'forecast-{engine.lower()}.json'
        if engine == 'R':
            cmd = [executable, str(ROOT/'scripts/run_forecast.R'), str(fixture_path), str(target)]
        else:
            quote = lambda p: "'" + str(p).replace("'", "''") + "'"
            expr = f"addpath({quote(ROOT/'scripts')});run_forecast({quote(fixture_path)},{quote(target)});"
            cmd = [executable, '--no-init-file', '--no-site-file', '--no-history', '--quiet', '--eval', expr]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=ROOT)
        (output/f'forecast-{engine.lower()}.log').write_text(run.stdout+run.stderr)
        if run.returncode:
            raise RuntimeError(f'{engine} forecast runner failed')
        reports[engine] = compare_native(json.loads(target.read_text()), fixture, engine)
    reports['MATLAB'] = (compare_native(json.loads(Path(matlab_results).read_text()), fixture, 'MATLAB')
                         if matlab_results else dict(status='NOT RUN', passed=False))
    passed = all(reports[e]['status'] == 'RUN' for e in require)
    passed &= all(r['passed'] for r in reports.values() if r['status'] == 'RUN')
    result = dict(fixture_id=fixture['fixture_id'], atol=ATOL, rtol=RTOL,
                  engines=reports, passed=passed)
    (output/'forecast-engine-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('fixture', type=Path)
    p.add_argument('--output', type=Path, default=ROOT/'results/forecast-qqq')
    p.add_argument('--require', nargs='*', choices=['Octave', 'R', 'MATLAB'], default=[])
    p.add_argument('--matlab-results', type=Path)
    p.add_argument('--skip-engines', action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    result = verify_forecast(a.fixture.resolve(), a.output.resolve(), a.require,
                             a.skip_engines, a.matlab_results)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['passed'] else 1)
