#!/usr/bin/env python3
"""Walk-forward QQQ interpolate-IV -> log -> PCA -> AR(1) benchmark."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from spline_equivalence import interpolate_surface
from spline_equivalence.forecast import log_surfaces, walk_forward, subspace_distance
from historical_qqq import (SOURCE, REVISION, METHODS, verified_file, rectangle,
                            clean_snapshot, engine_checks, split_grid, metrics)
from make_fixtures import canonical


def load_snapshots(data_dir, download=False):
    """Use the predecessor's exact source hashes, month choice, screen and grid."""
    import pandas as pd
    path, provenance = verified_file('underlying_prices.parquet', data_dir, download)
    sources = [provenance]
    underlying = pd.read_parquet(path)
    underlying['date'] = pd.to_datetime(underlying['date']).dt.normalize()
    if underlying['date'].duplicated().any():
        raise ValueError('Duplicate underlying dates')
    spots = underlying.set_index('date')['close']
    snapshots, annual = [], []
    for year in range(2011, 2017):
        path, provenance = verified_file(f'options_{year}.parquet', data_dir, download)
        sources.append(provenance)
        df = pd.read_parquet(path)
        for col in ('date', 'expiration'):
            df[col] = pd.to_datetime(df[col]).dt.normalize()
        if df['date'].isna().any() or not (df['date'].dt.year == year).all():
            raise ValueError('Invalid observation dates')
        annual.append(dict(year=year, rows=len(df)))
        dates = df.groupby(df['date'].dt.to_period('M'))['date'].min().sort_values()
        for date in dates:
            spot = float(spots.get(date, np.nan))
            if not np.isfinite(spot) or spot <= 0:
                raise ValueError(f'Missing raw close on {date}; calendar cannot be silently compressed')
            clean = clean_snapshot(df.loc[df['date'] == date], date, spot)
            grid = clean.pivot(index='strike', columns='tau', values='implied_volatility')
            block = rectangle(grid.sort_index().sort_index(axis=1))
            if block is None:
                raise ValueError(f'No rectangle on {date}; calendar cannot be silently compressed')
            snapshots.append(dict(date=str(date.date()), month=date.year * 12 + date.month,
                axes=[block.index.to_numpy(float) / spot, block.columns.to_numpy(float)],
                values=block.to_numpy(float),
                pivot=grid.sort_index().sort_index(axis=1), spot=spot,
                quote_q=clean[['moneyness', 'tau']].to_numpy(float),
                quote_iv=clean['implied_volatility'].to_numpy(float)))
        print(f'Loaded {year}: {len(df):,} rows', flush=True)
    return snapshots, sources, annual


def freeze_axes(snapshots, initial_train=24, shape=(9, 7)):
    """Intersect ONLY initial training rectangles, then freeze a regular grid."""
    if not 4 <= initial_train < len(snapshots):
        raise ValueError('Invalid initial training length')
    if len(shape) != 2 or any(n < 4 for n in shape):
        raise ValueError('Need >=4 grid nodes per axis')
    axes = []
    for j, n in enumerate(shape):
        lo = max(s['axes'][j][0] for s in snapshots[:initial_train])
        hi = min(s['axes'][j][-1] for s in snapshots[:initial_train])
        if not lo < hi:
            raise ValueError('Initial training rectangles have no common domain')
        axes.append(np.linspace(lo, hi, n))
    return axes


def select_spanning_rectangles(snapshots, axes):
    """Select each month's observed rectangle to span the already frozen domain.

    Maximizing nodes without this constraint often selects only short expiries.
    This constraint uses same-date availability only and does not widen the
    forecast domain or extrapolate. Unavailable support remains explicitly NaN.
    """
    selected = []
    for s in snapshots:
        bounds = [(axes[0][0] * s['spot'], axes[0][-1] * s['spot']),
                  (axes[1][0], axes[1][-1])]
        block = rectangle(s['pivot'], bounds=bounds)
        item = s.copy()
        if block is not None:
            item.update(axes=[block.index.to_numpy(float)/s['spot'],block.columns.to_numpy(float)],
                        values=block.to_numpy(float))
        selected.append(item)
    return selected


def align_snapshots(snapshots, axes, bandwidth_scale=1.):
    q = np.column_stack([x.ravel(order='F') for x in np.meshgrid(*axes, indexing='ij')])
    iv = {m: [] for m in METHODS}
    audit, cases, expected = [], [], {}
    for s in snapshots:
        h = [float(np.median(np.diff(a)) * bandwidth_scale) for a in s['axes']]
        row = dict(date=s['date'], source_grid=list(s['values'].shape), bandwidth=h, methods={})
        for method in METHODS:
            y = interpolate_surface(s['axes'], s['values'], q, method=method,
                bandwidth=h if method == 'nadaraya_watson' else None)
            iv[method].append(y)
            row['methods'][method] = dict(nonfinite=int((~np.isfinite(y)).sum()),
                nonpositive=int((np.isfinite(y) & (y <= 0)).sum()),
                minimum_iv=float(np.min(y[np.isfinite(y)])) if np.isfinite(y).any() else None)
            name = s['date'] + '_' + method
            cases.append(dict(name=name, kind='grid', method=method,
                axes=[a.tolist() for a in s['axes']], shape=list(s['values'].shape),
                values=s['values'].ravel(order='F').tolist(), queries=q.tolist(), fill='nan',
                bandwidth=h if method == 'nadaraya_watson' else []))
            expected[name] = y
        audit.append(row)
    payload = dict(description='Training-frozen historical QQQ alignment, IV before log', cases=cases)
    fixtures = dict(fixture_id=hashlib.sha256(canonical(payload)).hexdigest(), payload=payload)
    return {m: np.array(v) for m, v in iv.items()}, audit, fixtures, expected


def quote_mask(snapshot, axes):
    q = snapshot['quote_q']
    return np.logical_and.reduce([(q[:, j] >= a[0]) & (q[:, j] <= a[-1])
                                   for j, a in enumerate(axes)])


def evaluate_at_quotes(forecast_log, axes, q):
    """One common evaluation operator: bilinear LOG surface, then exp.

    Future spot/expiry coordinates locate the observed targets only; they do
    not enter the forecast fit. No method-specific scoring interpolation.
    """
    z = interpolate_surface(axes, forecast_log.reshape(tuple(map(len, axes)), order='F'),
                            q, method='linear')
    with np.errstate(over='raise', invalid='raise'):
        return np.exp(z)


def error_stats(prediction, truth):
    if not len(truth):
        return dict(n=0, sse=0., sae=0., log_sse=0.)
    if not np.all(np.isfinite(prediction) & (prediction > 0)):
        raise ValueError('Nonfinite/nonpositive forecast; do not drop failed predictions')
    error = prediction - truth
    return dict(n=len(truth), sse=float(error @ error), sae=float(abs(error).sum()),
                log_sse=float(np.sum((np.log(prediction) - np.log(truth))**2)))


def aggregate(rows):
    groups = {}
    for row in rows:
        key = (row['method'], row['model'], row['target_kind'])
        if row['n']:
            groups.setdefault(key, []).append(row)
    result = []
    for (method, model, target), group in groups.items():
        n = sum(r['n'] for r in group)
        result.append(dict(method=method, model=model, target_kind=target, months=len(group), n=n,
            rmse_iv_pp=100 * np.sqrt(sum(r['sse'] for r in group) / n),
            mae_iv_pp=100 * sum(r['sae'] for r in group) / n,
            rmse_log_iv=np.sqrt(sum(r['log_sse'] for r in group) / n),
            equal_month_rmse_iv_pp=100 * np.sqrt(np.mean([r['sse']/r['n'] for r in group]))))
    return result


def paired_bootstrap(rows, block=6, repetitions=2000):
    """Descriptive paired moving-block interval on equal-month MSE differences."""
    out = []
    lookup = {(r['method'], r['model'], r['date']): r['sse'] / r['n'] * 10000
              for r in rows if r['target_kind'] == 'observed_quotes' and r['n']}
    candidates = [(m, 'pca_ar1') for m in METHODS]
    pairs = [(x, (x[0], 'persistence')) for x in candidates]
    pairs += list(itertools.combinations(candidates, 2))
    for a, b in pairs:
        dates = sorted(k[2] for k in lookup if k[:2] == a and (*b, k[2]) in lookup)
        if len(dates) < block:
            continue
        month_ids = [int(d[:4])*12+int(d[5:7]) for d in dates]
        delta = np.full(month_ids[-1]-month_ids[0]+1, np.nan)
        for d, month in zip(dates, month_ids):
            delta[month-month_ids[0]] = lookup[(*a, d)] - lookup[(*b, d)]
        rng = np.random.default_rng(20261102)
        means = []
        for _ in range(repetitions):
            starts = rng.integers(0, len(delta)-block+1, size=int(np.ceil(len(delta)/block)))
            indices = np.concatenate([np.arange(s, s+block) for s in starts])[:len(delta)]
            if np.isfinite(delta[indices]).any():
                means.append(np.nanmean(delta[indices]))
        out.append(dict(a='/'.join(a), b='/'.join(b), months=len(dates), block_months=block,
            mean_delta_mse_pp2=float(np.nanmean(delta)),
            descriptive_95_interval=np.quantile(means, [.025, .975]).tolist()))
    return out


def benchmark(snapshots, axes, iv, *, initial_train=24, k=3, window=None,
              policy='strict', floor=1e-4, export_cases=False):
    logs, repairs = {}, {}
    for m in METHODS:
        logs[m], repairs[m] = log_surfaces(iv[m], policy,
                                          fallback=iv['linear'], floor=floor)
    months = [s['month'] for s in snapshots]
    rows, factors, stability, skipped, cases = [], [], [], [], []
    previous = {}
    primary_predictions = {}
    factor_arrays = {}
    for fold in walk_forward(logs, months, initial_train=initial_train, n_components=k, window=window):
        t = fold['target']
        date = snapshots[t]['date']
        if fold['status'] != 'ok':
            skipped.append(dict(date=date, reason=fold['reason']))
            continue
        indices = fold['train_indices']
        mask = quote_mask(snapshots[t], axes)
        truth, q = snapshots[t]['quote_iv'][mask], snapshots[t]['quote_q'][mask]
        common_grid_target = all(np.isfinite(logs[m][t]).all() for m in METHODS)
        for m, fit in fold['fits'].items():
            models = dict(pca_ar1=fit['forecast_log'], persistence=logs[m][t-1],
                          historical_mean=fit['mean'], pca_score_rw=fit['score_rw_log'])
            for model, prediction_log in models.items():
                prediction = evaluate_at_quotes(prediction_log, axes, q)
                row = dict(date=date, origin=snapshots[t-1]['date'], method=m, model=model,
                           target_kind='observed_quotes', **error_stats(prediction, truth))
                rows.append(row)
                if common_grid_target:
                    rows.append(dict(date=date, origin=snapshots[t-1]['date'], method=m, model=model,
                        target_kind='method_surface', **error_stats(np.exp(prediction_log), np.exp(logs[m][t]))))
            eigen = fit['eigenvalues']
            factors.append(dict(date=date, origin=snapshots[t-1]['date'], method=m,
                training_first=snapshots[indices[0]]['date'], training_last=snapshots[indices[-1]]['date'],
                training_rows=len(indices), ar_pairs=fit['ar_pairs'],
                explained_variance=float(fit['explained_ratio'].sum()),
                explained_ratio=fit['explained_ratio'].tolist(),
                phi=fit['phi'].tolist(), intercept=fit['intercept'].tolist(),
                unstable_factors=int((abs(fit['phi']) >= 1).sum()),
                eigengap_at_k=float((eigen[k-1]-eigen[k])/eigen[0]) if k < len(eigen) else None))
            if m in previous:
                stability.append(dict(date=date, comparison='consecutive_refits', method=m,
                    **subspace_distance(previous[m], fit['loadings'])))
            previous[m] = fit['loadings']
            primary_predictions[f'{date}_{m}'] = fit['forecast_log'].tolist()
            if export_cases:
                for field in ('mean', 'loadings', 'scores', 'phi', 'intercept', 'forecast_scores'):
                    factor_arrays[f'{date}_{m}_{field}'] = fit[field]
                factor_arrays[f'{date}_{m}_training_months'] = np.array(months)[indices]
                cases.append(dict(name=f'{date}_{m}', train_log=logs[m][indices].tolist(),
                    months=np.array(months)[indices].tolist(), k=k,
                    expected=dict(forecast_log=fit['forecast_log'].tolist(),
                        projector=(fit['loadings'] @ fit['loadings'].T).tolist(),
                        phi=fit['phi'].tolist(), explained_ratio=fit['explained_ratio'].tolist())))
        for a, b in itertools.combinations(METHODS, 2):
            difference = np.exp(fold['fits'][a]['forecast_log'])-np.exp(fold['fits'][b]['forecast_log'])
            stability.append(dict(date=date, comparison='between_methods', method=f'{a}/{b}',
                forecast_grid_disagreement_rmse_iv_pp=float(100*np.sqrt(np.mean(difference**2))),
                **subspace_distance(fold['fits'][a]['loadings'], fold['fits'][b]['loadings'])))
    return dict(aggregate=aggregate(rows), monthly=rows, factors=factors, stability=stability,
                skipped=skipped, repairs=repairs, forecasts=primary_predictions,
                native_cases=cases, factor_arrays=factor_arrays)


def original_holdout_positivity(snapshots):
    """Actual negative predictions in the ORIGINAL reconstruction experiment.

    This diagnostic is deliberately separate from temporal forecast targets.
    It quantifies policy consequences without inventing historical PCA failures.
    """
    predictions, fallback, truth, events = [], [], [], []
    for s in snapshots:
        a, v, q, y = split_grid(s['axes'], s['values'])
        cubic = interpolate_surface(a, v, q, method='spline')
        linear = interpolate_surface(a, v, q, method='linear')
        for i in np.flatnonzero(cubic <= 0):
            events.append(dict(date=s['date'], query=q[i].tolist(), spline_iv=float(cubic[i]),
                               observed_iv=float(y[i]), linear_iv=float(linear[i])))
        predictions.extend(cubic); fallback.extend(linear); truth.extend(y)
    predictions, fallback, truth = map(np.array, (predictions, fallback, truth))
    policies = {}
    for name, policy, floor in [('strict','strict',1e-4),('linear_fallback','linear_fallback',1e-4),
                                ('floor_0.0001','floor',1e-4),('floor_0.01','floor',.01)]:
        z, audit = log_surfaces(predictions,policy,fallback=fallback,floor=floor)
        adjusted = predictions if policy == 'strict' else np.exp(z)
        policies[name] = dict(**audit, **{'metrics':metrics(adjusted,truth)})
    return dict(scope='Original contemporaneous held-out reconstruction, NOT forecasting',
                events=events, policies=policies)


def matched_comparison(run, reference):
    """Keep parameter sensitivity comparisons on the SAME observed quote dates."""
    def dates(r):
        return {x['date'] for x in r['monthly'] if x['target_kind']=='observed_quotes' and x['n']}
    common = dates(run) & dates(reference)
    def select(r):
        return aggregate([x for x in r['monthly'] if x['date'] in common and x['target_kind']=='observed_quotes'])
    return dict(dates=sorted(common), sensitivity=select(run), reference=select(reference))


def sensitivity_record(run, reference, **extra):
    factors = {}
    for method in METHODS:
        f = [x for x in run['factors'] if x['method']==method]
        factors[method] = dict(unstable_ar_fits=sum(x['unstable_factors'] for x in f),
            explained_variance_range=[min(x['explained_variance'] for x in f),
                                      max(x['explained_variance'] for x in f)]) if f else {}
    return dict(aggregate=run['aggregate'], repairs=run['repairs'], skipped=run['skipped'],
                matched_to_primary=matched_comparison(run,reference), factor_summary=factors, **extra)


def main():
    import pandas as pd
    import pyarrow
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data/qqq')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/forecast-qqq')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--require', nargs='*', choices=['Octave', 'R'], default=[])
    parser.add_argument('--skip-engines', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    snapshots, sources, annual = load_snapshots(args.data_dir, args.download)
    positivity = original_holdout_positivity(snapshots)
    axes = freeze_axes(snapshots)
    snapshots = select_spanning_rectangles(snapshots, axes)
    iv, audit, fixtures, expected = align_snapshots(snapshots, axes)
    result = benchmark(snapshots, axes, iv, export_cases=True)
    np.savez_compressed(out / 'pca-factors.npz', **result.pop('factor_arrays'))
    native_payload = dict(description='Historical QQQ training-only PCA/AR1 folds', cases=result.pop('native_cases'))
    native_fixture = dict(fixture_id=hashlib.sha256(canonical(native_payload)).hexdigest(), payload=native_payload)
    (out / 'forecast-fixtures.json').write_text(json.dumps(native_fixture, allow_nan=False) + '\n')
    (out / 'alignment-fixtures.json').write_text(json.dumps(fixtures, allow_nan=False) + '\n')
    np.savez_compressed(out / 'aligned-surfaces.npz', dates=[s['date'] for s in snapshots],
                        moneyness=axes[0], maturity=axes[1], **iv)
    if args.skip_engines:
        if args.require:
            raise ValueError('Cannot skip required engines')
        engines, passed = {e: {'status': 'NOT RUN'} for e in ['Octave', 'R']}, True
    else:
        engines, passed = engine_checks(fixtures, expected, out, args.require)
    from verify_forecast import verify_forecast
    native = verify_forecast(out / 'forecast-fixtures.json', out, require=args.require,
                             skip_engines=args.skip_engines)
    sensitivity = {}
    for name, params in [('k1', dict(k=1)), ('k2', dict(k=2)), ('k5', dict(k=5)),
                         ('rolling24', dict(window=24)), ('initial36', dict(initial_train=36)),
                         ('linear_fallback', dict(policy='linear_fallback')),
                         ('floor_0.0001', dict(policy='floor', floor=1e-4)),
                         ('floor_0.01', dict(policy='floor', floor=.01))]:
        run = benchmark(snapshots, axes, iv, **params)
        sensitivity[name] = sensitivity_record(run,result,parameters=params)
    for scale in [.5, 2.]:
        alt, _, _, _ = align_snapshots(snapshots, axes, bandwidth_scale=scale)
        run = benchmark(snapshots, axes, alt)
        sensitivity[f'nw_bandwidth_{scale}'] = sensitivity_record(run,result)
    for shape in [(5, 4), (17, 13)]:
        alt_axes = [np.linspace(a[0], a[-1], n) for a, n in zip(axes, shape)]
        alt, alt_audit, _, _ = align_snapshots(snapshots, alt_axes)
        run = benchmark(snapshots, alt_axes, alt)
        sensitivity[f'grid_{shape[0]}x{shape[1]}'] = sensitivity_record(run,result,alignment_audit=alt_audit)
        if shape == (17,13):
            dense_strict = run
            for name, params in [('linear_fallback',dict(policy='linear_fallback')),
                                 ('floor_0.0001',dict(policy='floor',floor=1e-4)),
                                 ('floor_0.01',dict(policy='floor',floor=.01))]:
                repaired = benchmark(snapshots,alt_axes,alt,**params)
                sensitivity[f'dense_{name}'] = sensitivity_record(repaired,result,parameters=params,
                    matched_to_dense_strict=matched_comparison(repaired,dense_strict))
    summary = dict(scope='One-month QQQ ETF IV surface forecasts; not NDX, option returns or trading P&L',
        source_repository=SOURCE, source_revision=REVISION, source_files=sources, annual=annual,
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                      pandas=pd.__version__, pyarrow=pyarrow.__version__),
        code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            'scripts/forecast_qqq.py','scripts/historical_qqq.py','scripts/make_fixtures.py',
            'scripts/verify_forecast.py','scripts/run_forecast.m','scripts/run_forecast.R',
            'src/spline_equivalence/forecast.py','src/spline_equivalence/methods.py',
            'src/spline_equivalence/core.py']},
        protocol=dict(initial_train=24, components=3, horizon_months=1, window='expanding',
            positivity='strict; shared training-row rejection; no temporal compression',
            alignment='intersection of initial 24 original rectangles, frozen; same-date rectangles constrained to span it',
            grid_shape=[len(a) for a in axes], axes=[a.tolist() for a in axes],
            bandwidth='one median source-grid spacing per axis; no optimization',
            target_operator='bilinear log surface followed by exp for every method and baseline',
            grid_metric='secondary: each method own reconstructed target, identical months',
            transform='interpolate IV first, then log; exp forecast is not bias-corrected'),
        snapshots=len(snapshots), dates=[s['date'] for s in snapshots], alignment_audit=audit,
        alignment_fixture_id=fixtures['fixture_id'], forecast_fixture_id=native_fixture['fixture_id'],
        alignment_engines=engines, forecast_engines=native, MATLAB='NOT RUN on this historical benchmark',
        original_holdout_positivity=positivity,
        paired_month_mse=paired_bootstrap(result['monthly']), sensitivity=sensitivity,
        coverage=dict(scheduled_origins=len(snapshots)-24,
                      eligible_origins=len(snapshots)-24-len(result['skipped']),
                      full_supported_surfaces=int(np.logical_and.reduce([
                          np.isfinite(v).all(axis=1) for v in iv.values()]).sum())),
        passed=bool(passed and native['passed'] and result['factors']), **result)
    # Native fixtures/NPZ are generated inputs and not evidence of engine execution.
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    pd.DataFrame(result['monthly']).to_csv(out / 'monthly-errors.csv', index=False)
    pd.DataFrame(result['stability']).to_csv(out / 'factor-stability.csv', index=False)
    print(json.dumps({k: summary[k] for k in ['snapshots', 'protocol', 'aggregate', 'passed']}, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
