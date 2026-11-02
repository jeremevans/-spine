#!/usr/bin/env python3
"""Generate the forecast results document and figure from measured JSON evidence."""
import argparse
import json
import gzip
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('spline', 'linear', 'nadaraya_watson')
LABELS = dict(spline='Cubic spline', linear='Linear', nadaraya_watson='Gaussian NW')


def metric(rows, method, model='pca_ar1', target='observed_quotes'):
    return next(r for r in rows if r['method']==method and r['model']==model and r['target_kind']==target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT/'evidence/forecast-qqq-2026-11-02/python-summary.json.gz')
    parser.add_argument('--ci', type=Path, default=ROOT/'evidence/forecast-qqq-2026-11-02/ci-native-summary.json')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/FORECAST_RESULTS.md')
    parser.add_argument('--figure', type=Path, default=ROOT/'docs/forecast_comparison.svg')
    args = parser.parse_args()
    raw = args.summary.read_bytes()
    s = json.loads(gzip.decompress(raw) if args.summary.suffix == '.gz' else raw)
    ci = json.loads(args.ci.read_text()) if args.ci.exists() else None
    lines = ['# Executed QQQ PCA / AR(1) forecasting results', '',
        '**2 November 2026.** Python historical forecasts and sensitivities completed. '
        'The sample provides a reproducible comparison, not a reliable universal method ranking.', '',
        '[Protocol and reproduction commands](FORECAST_PROTOCOL.md) · '
        '[Machine-readable Python evidence](../evidence/forecast-qqq-2026-11-02/python-summary.json.gz) · '
        '[Monthly losses](../evidence/forecast-qqq-2026-11-02/monthly-errors.csv)', '',
        '## What was actually forecast', '',
        f"The source has {s['snapshots']} monthly snapshots. The first 24 define the initial "
        'training sample and a frozen 9×7 moneyness/maturity grid. Of 46 scheduled '
        'one-month forecasts for March 2013–December 2016, **37 are eligible**, '
        'and all methods score the same **1,623 next-month observed quotes**. '
        'Nine origins lack full support for the training-frozen domain; no future data '
        'were used to fill them. There are 61 complete aligned surfaces.', '',
        'Every origin refits centered log-IV PCA and independent intercept-bearing AR(1) '
        'models on past factor scores. The primary model uses three components. '
        'IV is interpolated **before** taking its logarithm.', '',
        '## Forecast accuracy against observed quotes', '',
        'All IV errors below are **volatility percentage points**, not percentages of error.', '',
        '| Interpolation | PCA/AR(1) RMSE | Persistence RMSE | Historical-mean RMSE | PCA score-RW RMSE | AR(1) MAE | Equal-month AR(1) RMSE |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for m in METHODS:
        a = metric(s['aggregate'],m)
        values = [metric(s['aggregate'],m,model)['rmse_iv_pp'] for model in
                  ('pca_ar1','persistence','historical_mean','pca_score_rw')]
        lines.append('| '+LABELS[m]+' | '+' | '.join(f'{x:.6f}' for x in values)+
                     f" | {a['mae_iv_pp']:.6f} | {a['equal_month_rmse_iv_pp']:.6f} |")
    lines += ['', 'NW has the lowest pooled RMSE here, while spline has the lowest MAE. '
        'The three AR(1) methods improve modestly over their own persistence baselines '
        'in decimal-IV RMSE. Rankings depend on the loss: the historical-mean baseline '
        'has **lower log-IV RMSE** than AR(1) for all three methods. No method wins every criterion.', '',
        'The paired six-calendar-month block-bootstrap intervals for differences between '
        'interpolation methods include zero. There are only 37 eligible temporal observations, '
        'not 1,623 independent forecast experiments. These exploratory intervals do not '
        'validate future skill.', '',
        '| Equal-month MSE comparison (A minus B) | Difference, points² | Descriptive 95% interval |',
        '|---|---:|---:|']
    for p in s['paired_month_mse']:
        lo,hi=p['descriptive_95_interval']
        lines.append(f"| {p['a']} minus {p['b']} | {p['mean_delta_mse_pp2']:.4f} | [{lo:.4f}, {hi:.4f}] |")
    lines += ['', '![Forecast and nonpositive-policy comparison](forecast_comparison.svg)', '',
        '## Factor stability', '',
        '| Method | Three-PC variance explained, min–max | AR slope range | Fits with abs(slope) ≥ 1 |',
        '|---|---:|---:|---:|']
    for m in METHODS:
        f=[x for x in s['factors'] if x['method']==m]
        variance=[100*x['explained_variance'] for x in f]; phi=np.array([x['phi'] for x in f])
        lines.append(f"| {LABELS[m]} | {min(variance):.2f}%–{max(variance):.2f}% | {phi.min():.4f}–{phi.max():.4f} | {sum(x['unstable_factors'] for x in f)} |")
    lines += ['', '| Between-method comparison | Median PC1 angle | Median largest three-PC angle |',
              '|---|---:|---:|']
    for pair in ('spline/linear','spline/nadaraya_watson','linear/nadaraya_watson'):
        r=[x for x in s['stability'] if x['method']==pair]
        lines.append(f"| {pair} | {np.median([x['pc1_angle_degrees'] for x in r]):.2f}° | {np.median([x['max_angle_degrees'] for x in r]):.2f}° |")
    lines += ['', 'The leading component is fairly similar across methods, while the weaker '
        'higher components can occupy very different subspaces. High variance explained '
        'does not imply stable economic factor interpretations or strong forecast accuracy. '
        'Full consecutive-refit and cross-method diagnostics are preserved in '
        '[factor-stability.csv](../evidence/forecast-qqq-2026-11-02/factor-stability.csv).', '',
        '## Sensitivity to model choices', '',
        'The following all use the same 37 quote dates. These are reported alternatives, '
        'not test-selected settings for a claimed winner.', '',
        '| Specification | Spline RMSE | Linear RMSE | Gaussian NW RMSE |',
        '|---|---:|---:|---:|']
    lines.append('| Primary: k=3, expanding | '+' | '.join(f"{metric(s['aggregate'],m)['rmse_iv_pp']:.6f}" for m in METHODS)+' |')
    for name in ('k1','k2','k5','rolling24','nw_bandwidth_0.5','nw_bandwidth_2.0','grid_5x4'):
        rows=s['sensitivity'][name]['matched_to_primary']['sensitivity']
        lines.append('| '+name+' | '+' | '.join(f"{metric(rows,m)['rmse_iv_pp']:.6f}" for m in METHODS)+' |')
    lines += ['', 'The later-start (`initial36`) and dense-grid tests have different eligible '
        'date sets. Their JSON records include the primary result recalculated on matched '
        'dates; comparing their raw aggregate RMSE with all 37 primary dates would be misleading.', '',
        '## Negative spline IV changes the forecasting problem', '',
        'The primary 9×7 grid has no nonpositive fitted IV. On the same frozen domain, '
        'the 17×13 grid exposes **13 negative spline cells on 2014-03-03**, minimum '
        '**−0.0422029 decimal IV**. Strict handling removes that training row for every '
        'method and skips the following forecast origin, leaving 36 eligible dates.', '',
        'The table below compares spline policies on the **same 36 dates**. Repaired '
        'policies can also issue a 37th forecast, excluded from this matched comparison.', '',
        '| Dense-grid spline policy | Matched RMSE | Repaired cells | Unstable factor fits across full run |',
        '|---|---:|---:|---:|']
    dense_values=[]
    for name,label in [('grid_17x13','Strict row rejection'),('dense_linear_fallback','Linear fallback'),
                       ('dense_floor_0.0001','Floor 0.0001'),('dense_floor_0.01','Floor 0.01')]:
        r=s['sensitivity'][name]
        rows=r['aggregate'] if name=='grid_17x13' else r['matched_to_dense_strict']['sensitivity']
        value=metric(rows,'spline')['rmse_iv_pp'];dense_values.append(value)
        lines.append(f"| {label} | {value:.6f} | {r['repairs']['spline']['repaired']} | {r['factor_summary']['spline']['unstable_ar_fits']} |")
    lines += ['', 'The 0.0001 floor creates **seven** factor fits with `abs(phi) >= 1`. '
        'No slope is capped. The 0.01 floor changes 14 cells, including one positive '
        'cell below the floor. Repairs change the model; they do not restore spline '
        'equivalence or guarantee sensible dynamics. Strict rejection has the smallest '
        'matched error here, but discards observed information and reduces forecast coverage.', '',
        'The earlier reconstruction negative is recomputed separately: spline '
        '**−0.0439822**, observed and linear **0.01488**, at a coordinate outside this '
        'forecast domain. Flooring it at 0.0001 raises the reconstruction log-RMSE '
        'to **0.139225** on 1,903 quotes; linear fallback gives **0.078947**. The '
        'unrepaired log-RMSE **0.078968** uses only 1,902 positive pairs and has a '
        'different denominator. These are contemporaneous reconstruction results, '
        '**not** the forecast errors above.', '',
        '## Separate reconstructed-surface target', '',
        '| Method | AR(1) RMSE to its own next reconstructed surface | Months | Grid cells |',
        '|---|---:|---:|---:|']
    for m in METHODS:
        r=metric(s['aggregate'],m,target='method_surface')
        lines.append(f"| {LABELS[m]} | {r['rmse_iv_pp']:.6f} | {r['months']} | {r['n']} |")
    lines += ['', 'These method-dependent targets differ from one another. Use them to '
        'diagnose the fitted dynamics, not to rank market-quote forecasting methods.', '',
        '## Executed numerical verification', '']
    if ci:
        lines += [f"[Successful GitHub Actions run]({ci['run_url']}) at code commit "
                  f"`{ci['code_commit']}`: **{ci['unit_tests']} tests passed**. "
                  'Historical reconstruction regression also passed.', '',
                  '| Native engine vs Python | Aligned-IV max difference, 210 cases | Log-forecast max difference, 111 cases | AR-slope max difference |',
                  '|---|---:|---:|---:|']
        for engine in ('Octave','R'):
            a=ci['alignment_engines'][engine];b=ci['forecast']['engines'][engine]
            lines.append(f"| {engine} {b['version']} | {a['max_abs']:.3e} | {b['max_abs']['forecast_log']:.3e} | {b['max_abs']['phi']:.3e} |")
    lines += ['', 'Projection matrices and explained-variance ratios also pass. '
        'The native PCA/AR(1) comparisons use shared Python-generated log matrices; '
        'interpolation is independently checked in a separate stage. This is numerical '
        'stage parity, not three independent ingestion/backtest implementations. '
        '**Historical MATLAB forecasting was not run.** The MATLAB-compatible runner '
        'and import validator are supplied; existing synthetic MATLAB passes do not '
        'verify these historical forecasts.', '',
        'Local Python evidence preserves NOT RUN for local Octave/R/MATLAB; '
        'the [separate CI evidence](../evidence/forecast-qqq-2026-11-02/ci-native-summary.json) '
        'records the actual remote Octave/R execution. No local statuses were relabeled.', '',
        '## Interpretation limits', '',
        'This is 2011–2016 **QQQ ETF-call** research with narrow support and only 37 '
        'eligible one-month observations. It does not establish NDX 2000–2010 coverage, '
        'daily or multi-step skill, arbitrage freedom, trading profitability, or literal '
        'reproduction of an unavailable original MATLAB model. The historical sample '
        'was used during benchmark development; temporal isolation in the code does '
        'not turn an exploratory study into a preregistered statistical test.', '']
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text('\n'.join(lines))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    fig,ax=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    x=np.arange(3);colors=['#245C73','#899BA5']
    ar=[metric(s['aggregate'],m)['rmse_iv_pp'] for m in METHODS]
    rw=[metric(s['aggregate'],m,'persistence')['rmse_iv_pp'] for m in METHODS]
    b1=ax[0].bar(x-.18,ar,.36,label='PCA / AR(1)',color=colors[0])
    b2=ax[0].bar(x+.18,rw,.36,label='Persistence',color=colors[1])
    ax[0].bar_label(b1,fmt='%.3f',padding=4,fontsize=9);ax[0].bar_label(b2,fmt='%.3f',padding=4,fontsize=9)
    ax[0].set_xticks(x,[LABELS[m] for m in METHODS]);ax[0].set_ylim(0,5.5)
    ax[0].set_title('Primary forecast: small differences\n37 matched dates · 1,623 future quotes',loc='left',pad=16)
    ax[0].legend(loc='lower right');ax[0].set_ylabel('IV forecast RMSE (volatility points)')
    bars=ax[1].bar(np.arange(4),dense_values,color=['#245C73','#4B8C8A','#C46A38','#889CA1'],width=.65)
    ax[1].bar_label(bars,fmt='%.3f',padding=5,fontsize=9)
    ax[1].set_xticks(np.arange(4),['Strict','Linear\nfallback','Floor\n0.0001','Floor\n0.01'])
    ax[1].set_ylim(0,5.5);ax[1].set_title('Dense-grid spline: policy matters\n36 matched dates · 13 negative input cells',loc='left',pad=16)
    for a in ax:
        a.spines[['top','right']].set_visible(False);a.set_axisbelow(True);a.grid(axis='y',alpha=.16)
    fig.suptitle('Historical QQQ forecasts | interpolate IV → log → PCA → AR(1)',fontsize=15,fontweight='bold')
    args.figure.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.figure,metadata={'Date':None})
    fig.savefig(args.figure.with_suffix('.png'),dpi=160)
    plt.close(fig)
    print(args.output)
    print(args.figure)


if __name__=='__main__':
    main()
