#!/usr/bin/env python3
"""Reproducible QQQ 2011-2016 surface interpolation benchmark (not a forecast)."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from spline_equivalence import interpolate_surface
from make_fixtures import canonical
from verify import compare, validate_engine

SOURCE = 'anahatsingh-ui/options-dataset-hist'
REVISION = '37f6c456fe1a4775c875673fb8ef907d5cd2fd66'
FILES = {
    'underlying_prices.parquet': (332454, 'f3a892bc4c88c692900b5c0071322c6db408996a'),
    'options_2011.parquet': (7271151, '6d73b23d9e58cce54e2a6b3a855ad38cc2af37c1'),
    'options_2012.parquet': (10197428, '5c120074bda89db62022212f59c65daa81f232d2'),
    'options_2013.parquet': (12257488, '4df0007d3f5e152514a8da00889cf65583c73044'),
    'options_2014.parquet': (18615540, '074840f5bc5938226860eae54c87cb521be7e52b'),
    'options_2015.parquet': (17841650, '042c9c371ed85486824e9f0d686110306f514063'),
    'options_2016.parquet': (17307631, 'b695a8a8d04809fa650f746c825609a855643349'),
}
METHODS = ('spline', 'linear', 'nadaraya_watson')


def verified_file(name, directory, download):
    """Require the exact published Git blob, including when reusing a cache."""
    path = directory / name
    expected_size, expected_sha = FILES[name]
    if not path.exists():
        if not download:
            raise FileNotFoundError(f'{path}; provide the file or pass --download')
        directory.mkdir(parents=True, exist_ok=True)
        url = f'https://raw.githubusercontent.com/{SOURCE}/{REVISION}/qqq/{name}'
        temporary = path.with_suffix('.part')
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    data = path.read_bytes()
    sha = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    if len(data) != expected_size or sha != expected_sha:
        raise ValueError(f'Source size or Git blob hash mismatch: {name}')
    return path, dict(file=name, bytes=len(data), git_blob_sha1=sha,
                      sha256=hashlib.sha256(data).hexdigest())


def rectangle(pivot):
    """Choose a complete grid without imputing any missing option quotes.

    Search consecutive windows of 5-9 expiries. Keep up to 25 evenly spaced
    common strikes. Maximize retained node count; ties use the first window.
    Selection uses availability, not the magnitudes of held-out IV values.
    """
    best = None
    score = 0
    for width in range(5, min(9, pivot.shape[1]) + 1):
        for start in range(pivot.shape[1] - width + 1):
            block = pivot.iloc[:, start:start + width].dropna(axis=0)
            if len(block) < 5:
                continue
            if len(block) > 25:
                block = block.iloc[np.linspace(0, len(block) - 1, 25).astype(int)]
            if block.size > score:
                best, score = block, block.size
    return best


def split_grid(axes, values):
    """Remove one interior strike and expiry; train on their Cartesian complement."""
    i, j = (len(a) // 2 for a in axes)
    keep_i = np.delete(np.arange(len(axes[0])), i)
    keep_j = np.delete(np.arange(len(axes[1])), j)
    training = values[np.ix_(keep_i, keep_j)]
    training_axes = [axes[0][keep_i], axes[1][keep_j]]
    ii, jj = np.indices(values.shape)
    held = (ii == i) | (jj == j)
    q = np.column_stack([axes[0][ii[held]], axes[1][jj[held]]])
    return training_axes, training, q, values[held]


def metrics(prediction, truth):
    finite = np.isfinite(prediction)
    good = finite & (prediction > 0) & (truth > 0)
    errors = prediction[finite] - truth[finite]
    return dict(queries=len(truth), finite=int(finite.sum()),
                nonpositive=int((finite & (prediction <= 0)).sum()),
                rmse_iv=float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
                mae_iv=float(np.mean(abs(errors))) if len(errors) else None,
                log_pairs=int(good.sum()),
                rmse_log_iv=float(np.sqrt(np.mean((np.log(prediction[good]) - np.log(truth[good]))**2))) if good.any() else None)


def engine_checks(fixtures, python_values, output, require):
    input_path = output / 'market-fixtures.json'
    input_path.write_text(json.dumps(fixtures, allow_nan=False) + '\n')
    reports = {}
    for engine, binary in [('Octave', 'octave-cli'), ('R', 'Rscript')]:
        executable = shutil.which(binary)
        if not executable:
            reports[engine] = {'status': 'NOT RUN', 'passed': False}
            continue
        target = output / (engine.lower() + '.json')
        if engine == 'R':
            cmd = [executable, str(ROOT / 'scripts/run_methods.R'), str(input_path), str(target)]
        else:
            quote = lambda x: "'" + str(x).replace("'", "''") + "'"
            expression = f"addpath({quote(ROOT/'scripts')});run_methods({quote(input_path)},{quote(target)});"
            cmd = [executable, '--no-init-file', '--no-site-file', '--no-history', '--quiet', '--eval', expression]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=ROOT)
        (output / (engine.lower() + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'{engine} failed; inspect {engine.lower()}.log')
        raw = json.loads(target.read_text())
        data = validate_engine(raw, engine, fixtures)
        checks = {name: compare(data[name], value) for name, value in python_values.items()}
        reports[engine] = dict(status='RUN', version=raw['engine_version'],
                               passed=all(v['passed'] for v in checks.values()),
                               cases=len(checks), max_abs=max(v['max_abs'] for v in checks.values()))
    passed = all(reports[e]['status'] == 'RUN' for e in require)
    passed = passed and all(r['passed'] for r in reports.values() if r['status'] == 'RUN')
    return reports, passed


def main():
    import pandas as pd
    import pyarrow

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data/qqq')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/historical-qqq')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--years', type=int, nargs='+', default=list(range(2011, 2017)), choices=range(2011, 2017))
    parser.add_argument('--require', nargs='*', choices=['Octave', 'R'], default=[])
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source_files = []
    path, provenance = verified_file('underlying_prices.parquet', args.data_dir, args.download)
    source_files.append(provenance)
    underlying = pd.read_parquet(path)
    # Deliberately require raw close: adjusted closes would distort strike/spot.
    if not {'date', 'close'}.issubset(underlying.columns):
        raise ValueError(f'Expected date and unadjusted close, got {list(underlying.columns)}')
    underlying['date'] = pd.to_datetime(underlying['date']).dt.normalize()
    if underlying['date'].duplicated().any():
        raise ValueError('Duplicate underlying dates')
    spots = underlying.set_index('date')['close']
    cases, python_values, daily, audits, skipped = [], {}, [], [], []
    all_truth = []
    all_predictions = {m: [] for m in METHODS}
    for year in sorted(set(args.years)):
        path, provenance = verified_file(f'options_{year}.parquet', args.data_dir, args.download)
        source_files.append(provenance)
        df = pd.read_parquet(path)
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        df['expiration'] = pd.to_datetime(df['expiration']).dt.normalize()
        if df['date'].isna().any() or not (df['date'].dt.year == year).all():
            raise ValueError(f'Invalid observation dates in {year}')
        iv = pd.to_numeric(df['implied_volatility'], errors='coerce')
        audits.append(dict(year=year, rows=len(df), dates=df['date'].nunique(),
                           first_date=str(df['date'].min().date()), last_date=str(df['date'].max().date()),
                           invalid_or_nonpositive_iv=int((~np.isfinite(iv) | (iv <= 0)).sum()),
                           option_types=sorted(df['type'].astype(str).unique().tolist())))
        # One fixed snapshot per calendar month: first date available, without
        # searching forward for a day on which fitting happens to work better.
        dates = df.groupby(df['date'].dt.to_period('M'))['date'].min().sort_values()
        for date in dates:
            label = str(date.date())
            spot = float(spots.get(date, np.nan))
            if not np.isfinite(spot) or spot <= 0:
                skipped.append(dict(date=label, reason='missing/nonpositive raw close'))
                continue
            frame = df.loc[df['date'] == date].copy()
            frame['tau'] = (frame['expiration'] - date).dt.days / 365.0
            frame['moneyness'] = frame['strike'] / spot
            mid = (frame['bid'] + frame['ask']) / 2
            numeric = frame[['strike', 'bid', 'ask', 'implied_volatility', 'tau']].to_numpy(float)
            usable = (np.isfinite(numeric).all(axis=1)
                      & frame['type'].str.lower().isin(['call', 'c'])
                      & (frame['implied_volatility'] > 0) & (frame['bid'] > 0)
                      & (frame['ask'] >= frame['bid'])
                      & ((frame['ask'] - frame['bid']) <= .5 * mid)
                      & frame['tau'].between(21 / 365, 730 / 365)
                      & frame['moneyness'].between(.8, 1.2))
            clean = frame.loc[usable]
            # Exclude ambiguous duplicate contracts instead of averaging labels.
            clean = clean.loc[~clean.duplicated(['strike', 'tau'], keep=False)]
            grid = clean.pivot(index='strike', columns='tau', values='implied_volatility').sort_index().sort_index(axis=1)
            block = rectangle(grid)
            if block is None:
                skipped.append(dict(date=label, reason='no complete >=5x5 quote grid', usable_quotes=len(clean)))
                continue
            axes = [block.index.to_numpy(float) / spot, block.columns.to_numpy(float)]
            a, v, q, truth = split_grid(axes, block.to_numpy(float))
            # Fixed coordinate-only rule: Gaussian standard deviation equals
            # one median training-grid spacing on each axis. No IV-label tuning.
            bandwidth = [float(np.median(np.diff(x))) for x in a]
            row = dict(date=label, raw_quotes=len(frame), usable_quotes=len(clean),
                       full_grid=list(block.shape), training_grid=list(v.shape),
                       held_out=len(truth), bandwidth=bandwidth, methods={})
            for method in METHODS:
                y = interpolate_surface(a, v, q, method=method,
                    bandwidth=bandwidth if method == 'nadaraya_watson' else None)
                name = label + '_' + method
                cases.append(dict(name=name, kind='grid', method=method,
                    axes=[x.tolist() for x in a], shape=list(v.shape),
                    values=v.ravel(order='F').tolist(), queries=q.tolist(),
                    fill='nan', bandwidth=bandwidth if method == 'nadaraya_watson' else []))
                python_values[name] = y
                all_predictions[method].extend(y.tolist())
                row['methods'][method] = metrics(y, truth)
            all_truth.extend(truth.tolist())
            daily.append(row)
        print(f'{year}: {len(df):,} rows; {sum(r["date"].startswith(str(year)) for r in daily)} usable monthly snapshots', flush=True)
    if not daily:
        raise ValueError('No usable historical grids; no benchmark can be claimed')
    payload = dict(description='QQQ monthly first-day grids, 2011-2016, quote holdouts', cases=cases)
    fixtures = dict(fixture_id=hashlib.sha256(canonical(payload)).hexdigest(), payload=payload)
    engines, cross_passed = engine_checks(fixtures, python_values, out, args.require)
    truth = np.array(all_truth)
    pooled = {m: metrics(np.array(all_predictions[m]), truth) for m in METHODS}
    finite_passed = all(v['finite'] == v['queries'] for v in pooled.values())
    summary = dict(
        scope='QQQ ETF option quote reconstruction; not NDX and not a forecasting backtest',
        source_repository=SOURCE, source_revision=REVISION, source_files=source_files,
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                      pandas=pd.__version__, pyarrow=pyarrow.__version__),
        years=sorted(set(args.years)), annual_audit=audits, snapshots=len(daily),
        skipped_snapshots=skipped, skipped_reasons=dict(Counter(r['reason'] for r in skipped)),
        held_out_quotes=len(truth), pooled=pooled, engines=engines,
        absolute_tolerance=2e-11, relative_tolerance=2e-10,
        fixture_id=fixtures['fixture_id'], daily=daily,
        passed=bool(cross_passed and finite_passed),
        limitations=[
            'First available trading date per month, not every trading day.',
            'Dense complete call grids select a subset of quotes; results are not all-market accuracy.',
            'Vendor IV is the reconstruction target, not independently verified true volatility.',
            'NW bandwidth is a predeclared spacing heuristic, not optimized.',
            'No PCA/AR(1), temporal holdout, risk-neutral dynamics or arbitrage enforcement.',
            'MATLAB was not run on these historical fixtures.'
        ])
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: summary[k] for k in ['snapshots', 'held_out_quotes', 'pooled', 'engines', 'passed']}, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
