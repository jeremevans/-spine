# Historical Nasdaq data: what is available and what we test

Research date: 2026-11-02. Here, Nasdaq means the **Nasdaq-100**, distinguishing
NDX index options from QQQ ETF options. Nasdaq Composite price history is not
an implied-volatility surface dataset.

**Executed results:** [70 monthly surfaces and 1,903 held-out quotes](HISTORICAL_RESULTS.md),
with successful Python/Octave/R numerical comparisons. The actual files contain
2,435,400 option rows from 2011-03-23 through 2016-12-30.

## Availability for the requested 2000-2016 interval

| Source | Instrument and published history | What it supplies | Relevance |
|---|---|---|---|
| [Public preservation repository](https://github.com/anahatsingh-ui/options-dataset-hist) | QQQ, 2011-2025 | Daily option chains: strikes, expirations, call/put, bid/ask, IV and Greeks; underlying prices | Files for 2011-2016 are present. This is an ETF proxy, with no 2000-2010 coverage. |
| [Options portfolio backtester data notice](https://github.com/lambdaclass/options_portfolio_backtester/blob/master/data/DATA_NOTICE.md) | QQQ, reported start 2011-03-23 | Another preservation of the same original dataset | Not an independent source confirming the quotes. |
| [OptionMetrics IvyDB US](https://optionmetrics.com/united-states/) / [WRDS](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/optionmetrics/) | US equity and index options, January 1996 onward | Raw quotes, vendor IV/Greeks, standardized daily delta-by-maturity surfaces | A licensed route that can potentially cover the full requested NDX period. Security-specific availability must be confirmed in the actual export. No licensed data was obtained for this project. |
| [FRED VXNCLS](https://fred.stlouisfed.org/series/VXNCLS) | Nasdaq-100 volatility index, daily history beginning 2001 | One volatility-index observation per day | Useful as a regime indicator; cannot replace strike-by-expiry surfaces. |
| [FuNVol](https://github.com/vedantch/FuNVol) | Research code and model-generated examples | The README explicitly withholds the historical training dataset for licensing reasons | Not a public NDX 2000-2016 quote archive. |

We have **not verified a freely accessible repository containing complete NDX
surfaces for 2000-2016**. That is a search finding, not proof that none exists.
The QQQ repository's technical report gives 2011-03-23 as its start date;
the executable audit reports the actual first and last dates in each input file.
QQQ does not supply the dot-com period or the 2008 crisis in this archive.

## Provenance and limits

The original dataset is credited to Philipp D. Dubach. The surviving mirror
reports recovery from a fork in July 2026 and carries an MIT license. Its original
README describes the IV field as Black-Scholes implied volatility. Upstream
exchange/vendor provenance and the original IV calculation are not independently
validated here. QQQ ETF options and NDX index options have different contract
features; their results must be labeled separately.

The benchmark pins mirror commit
`37f6c456fe1a4775c875673fb8ef907d5cd2fd66` and verifies the byte count and Git blob
SHA-1 of all seven files (six years plus the underlying series). It also records
SHA-256 digests. The six annual option files total 83,490,888 bytes. The repository
stores our code and aggregate evidence, not copies of source option quotes.
Review the source's terms for your intended use; the mirror's license statement
does not independently establish the rights attached to the original feed.

## Historical quote test

Run from the project root with Python 3.11 or later:

```sh
python -m pip install -e '.[historical]'
python scripts/historical_qqq.py --download --require Octave R
```

Octave and R with `pracma` and `jsonlite` must be installed when required.
Omit `--require Octave R` if they are unavailable: missing engines are explicitly
reported as `NOT RUN`. A one-year pilot uses `--years 2011`. Downloads are opt-in;
without `--download`, supply the exact pinned Parquet files in `data/qqq/`.
The [GitHub workflow](../.github/workflows/historical-qqq.yml) installs all required
runtimes and runs the six-year benchmark. Its artifact contains summary JSON and
engine logs; temporary market fixtures and raw data are not uploaded.

1. Audit rows, observation dates, option types and invalid/nonpositive IV by year.
2. Select the first available date of each calendar month. Do not search forward
   for a day with more favorable results; report skipped snapshots.
3. Retain finite call quotes with positive IV and bid, uncrossed quotes, spread
   at most 50% of mid, 21-730 calendar days to expiration, and strike/raw-close
   between 0.8 and 1.2. Exclude duplicate strike-expiry pairs entirely.
4. Select a genuinely complete quote rectangle: 5-9 consecutive available
   expiries and up to 25 common strikes. Maximize retained node count; break ties
   in deterministic search order. Do not fill missing quotes before testing.
5. Withhold the middle strike and middle expiry in full. Their union is the test
   set; the Cartesian complement is the training grid. Each training axis retains
   at least four nodes, and every query is inside the training domain.
6. Fit all three methods to exactly the same training IV values. Use coordinates
   `(strike/raw-close, calendar_days/365)`. Gaussian NW bandwidths equal the median
   training-node spacing on each axis. This predeclared heuristic uses no held-out
   IV values and is not a claim of optimal bandwidth selection.
7. Measure pooled quote-weighted IV RMSE/MAE, nonpositive predictions and log-IV
   RMSE on positive finite pairs. IV units are decimal: an RMSE of 0.01 means one
   volatility percentage point. Fit in IV levels, then take logs, matching the
   original preprocessing order under discussion. Never clip negative spline
   predictions silently.
8. Evaluate identical fixtures with Python, Octave and R. Compare with the
   existing absolute `2e-11` plus relative `2e-10` tolerance. MATLAB has not been
   run on these new historical fixtures; existing synthetic MATLAB evidence is
   a separate result.

The benchmark fails if required engines are absent, engine agreement fails, no
usable grids exist, source hashes differ, or any method produces nonfinite test
predictions. It does not fail solely because one method has larger market error:
this is a comparison, not an assertion that spline must win.

Dense-grid selection and quote filtering limit the population to which the
results apply. Vendor IV is a reconstruction target, not ground-truth latent
volatility. These tests establish numerical agreement and quote-reconstruction
error on sampled historical surfaces, not predictive performance or absence of
static arbitrage.

## Additional PCA/AR(1) model test

The historical script does **not** fit PCA/AR(1) or project stochastic volatility.
A subsequent forecasting experiment needs daily surfaces on one fixed grid,
consistent coverage rules, and a chronological split, for example 2011-2014
training and 2015-2016 testing. Select NW bandwidth, PCA rank, centering and AR
parameters using training data only. Compare one-step log-IV forecasts against
the previous day's surface, and evaluate simulated intervals on held-out dates.
Distinguish conditional medians after exponentiation from conditional means.
No risk-neutral calibration or arbitrage-free dynamics follow automatically from
PCA plus AR(1). Full-period NDX claims additionally require actual NDX inputs for
2000-2016, rather than filling the missing years with synthetic QQQ observations.
