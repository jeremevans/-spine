# Actual QQQ historical surface results

**Completed successfully on 2 November 2026.**
[GitHub run 41495485684](https://github.com/jeremevans/-spine/actions/runs/41495485684)
ran the benchmark at code commit
[`8b67526a1c19ebc53aa32886bc70b0aa831d77e6`](https://github.com/jeremevans/-spine/commit/8b67526a1c19ebc53aa32886bc70b0aa831d77e6).
The [unaltered summary](../evidence/historical-qqq-41495485684/summary.json)
records source hashes, software versions, every selected date and its metrics.

## Data actually read

The six annual Parquet files contain **2,435,400 QQQ option-contract/day rows**,
covering **1,453 distinct observation dates** between **2011-03-23 and 2016-12-30**.
The source is a public preservation mirror, not a licensed NDX export.

| Year | Rows read | Observation dates | First date | Last date | Invalid/nonpositive input IV |
|---|---:|---:|---|---|---:|
| 2011 | 201,100 | 197 | 2011-03-23 | 2011-12-30 | 0 |
| 2012 | 296,244 | 250 | 2012-01-03 | 2012-12-31 | 17 |
| 2013 | 369,383 | 252 | 2013-01-02 | 2013-12-31 | 0 |
| 2014 | 549,664 | 252 | 2014-01-02 | 2014-12-31 | 0 |
| 2015 | 516,063 | 251 | 2015-01-02 | 2015-12-31 | 0 |
| 2016 | 502,946 | 251 | 2016-01-04 | 2016-12-30 | 0 |

These are observed file counts, not a claim that every exchange trading day is
present. The benchmark used the first available date in each month: **70 snapshots**,
with no snapshot skipped by the stated grid-selection rules. The full-year files
were audited, but only those monthly snapshots were fitted.

## Held-out quote reconstruction

An entire interior strike and expiry were removed from each complete quote grid.
All three methods received the same remaining nodes and predicted the same
**1,903 held-out quotes**. See the [protocol](HISTORICAL_NASDAQ.md) for filtering,
grid selection and the fixed NW bandwidth rule.

| Method | IV RMSE, volatility percentage points | IV MAE, volatility percentage points | Nonpositive predictions |
|---|---:|---:|---:|
| Spline | 1.155304 | 0.466601 | 1 |
| Linear | **0.789525** | **0.325627** | 0 |
| Nadaraya-Watson | 0.843806 | 0.410074 | 0 |

For scale, 1 volatility percentage point is 0.01 in decimal IV units.
Errors are pooled across quotes, so dates with more held-out nodes receive more
weight. All 1,903 predictions per method were finite.

Linear had the smallest error **in this specific experiment**. This does not prove
that linear is universally preferable: the tested quotes are a filtered dense-grid
subset, and NW used a spacing-based bandwidth rather than an optimized bandwidth.
The target is the dataset's reported IV, not independently established latent IV.

The nonpositive spline prediction occurred on **2014-03-03**. This is material to
the intended interpolate-then-log workflow: a real logarithm is unavailable at
that prediction. The test retained and counted it; no clipping was applied.
Spline log-IV RMSE is 0.07896775 on only 1,902 positive pairs, while linear is
0.06569232 and NW is 0.07450840 on all 1,903 pairs. Those log metrics have different
sample sizes and must not be treated as an identical-sample comparison.

Interpolating log-IV and then exponentiating would guarantee positivity for
finite fitted log values, but would change the original interpolate-IV-then-log
calculation. It should be evaluated as a separate model choice.

## Numerical equivalence on historical inputs

There were **210 method/snapshot cases** and **5,709 predictions per engine**.
All Python/Octave/R comparisons passed the existing absolute `2e-11` plus relative
`2e-10` tolerance.

| Engine compared with Python | Version | Largest absolute IV difference, all methods |
|---|---|---:|
| GNU Octave | 8.4.0 | 1.061651e-15 |
| R | 4.3.3 | 2.331468e-15 |

Python was 3.12.15, NumPy 2.3.5, SciPy 1.17.0, pandas 2.3.3 and pyarrow 23.0.1.
The workflow also passed all 26 unit tests.
**MATLAB was not run on these historical fixtures.** Its existing synthetic
equivalence suite is separate evidence.

Matching implementations can share a poor market fit; numerical equivalence and
statistical suitability are different questions. This run does not establish
PCA/AR(1) forecasting accuracy, stochastic-volatility dynamics, arbitrage freedom,
or coverage of NDX in 2000-2010.
