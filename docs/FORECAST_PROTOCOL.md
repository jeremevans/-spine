# Historical QQQ PCA / AR(1) forecasting protocol

This is an executed **research benchmark**, separate from the original
[held-out reconstruction test](HISTORICAL_RESULTS.md). It reproduces the specified
operation order, **interpolate IV → log → centered PCA → factor AR(1)**. It is not
a verified reproduction of an unavailable original MATLAB research script, a
risk-neutral model, a trading strategy, or a calibrated stochastic-volatility model.

## Data and aligned surfaces

The exact seven source files, Git blob checks and quality filters are inherited
from `scripts/historical_qqq.py`. The 2,435,400 contract/day observations yield
70 snapshots: the first available date of each month from March 2011 through
December 2016. Use raw underlying close for `m = strike / spot`; maturity is
calendar days / 365. Calls only; positive finite IV and bid; ask ≥ bid; spread
≤ 50% of midpoint; maturity 21–730 days; moneyness 0.8–1.2. Ambiguous duplicate
strike/expiry records are excluded. Reported vendor IV is the target, not
independently recovered or established true volatility.

1. On the **first 24 months only**, run the original complete-rectangle selection
   (5–9 consecutive expiries, at most 25 common strikes, maximum node count).
2. Intersect these rectangles' coordinate bounds and freeze them. This gives
   moneyness **0.8661008141–1.0360904852**, and maturity **107–182 days**.
   The primary alignment grid has **9 × 7 = 63** equally weighted nodes, equally
   spaced on both axes. This is an asymmetric slice, not the full volatility smile.
3. For every month, including training months, select the maximum-node complete
   rectangle **subject to spanning that frozen domain**, using only that month's
   observed availability. This avoids selecting a large short-expiry rectangle
   when a smaller observed rectangle covers the required maturities.
4. Evaluate each of the three methods on exactly those 63 nodes. Splines are the
   repository's not-a-knot tensor-product spline with a direct solve. NW uses
   Gaussian standard deviations of one median source-grid spacing on each axis.
   This fixed coordinate rule uses neither forecast labels nor optimized bandwidths.

No extrapolation, temporal filling, use of future support to shrink the domain,
or filling from another month's quotes is allowed. If no spanning rectangle
exists, the original rectangle is evaluated with explicit NaN outside its support;
the incomplete aligned row is unusable. This leaves **61 complete monthly surfaces**.
The raw files and local generated matrices are not redistributed in the committed
evidence; source provenance does not establish redistribution rights.

During implementation, unconstrained maximum-node rectangles caused 18 unsupported
origins. Adding the same-date spanning constraint reduced that to nine without
changing the training-frozen domain. This design choice is disclosed: the experiment
was developed against this historical sample and is **not a preregistered untouched
holdout**. The code's chronological calculations still exclude future values.

## Walk-forward fit and forecast

The primary experiment uses an expanding window with 24 initial calendar snapshots,
March 2011–February 2013. There are 46 scheduled one-month forecast origins, targeting
March 2013–December 2016. A month is a discrete observation step; actual intervals
vary with trading dates, and the first March 2011 date is March 23.

At each origin, take only earlier/current available surfaces. Apply a real logarithm
**after** IV interpolation. A training row must be finite and positive for **every**
method. Use the same retained dates for all methods. If the latest origin is invalid,
skip that origin for all methods. Never drop dates and then treat the resulting gap
as a one-month lag. AR regressions include only adjacent calendar-month pairs.
No test target's validity is used to determine training rows or issue a forecast.

For each method, let `X` be its retained time × grid-node log-IV matrix:

\[
\mu=\operatorname{mean}_{\mathrm{train}}(X),\quad
X-\mu=U\Sigma V^T,\quad F=(X-\mu)V_k.
\]

Use covariance PCA: center each node, do not standardize its variance. Use **k=3**
in the primary specification. All historical scores are recomputed in this origin's
training-only basis. Never combine scores produced by differently rotated bases.
Each factor is fitted independently by OLS, with an intercept:

\[
F_{t+1,j}=a_j+b_j F_{t,j}+\epsilon_{t+1,j},\qquad
\widehat\ell_{t+1}=\mu+V_k(a+b\odot F_t).
\]

The IV forecast is `exp(forecast_log)`. It is **not** adjusted for Jensen's inequality
or claimed to be a conditional mean of IV. No AR coefficient is clipped or forced
stationary; `abs(phi) >= 1` is counted. PCA signs are made deterministic for exported
arrays, but sign/rotation-invariant quantities define numerical comparisons.

Every fit exports its training dates, AR pair count, explained variance, slopes,
intercepts and eigengap. Local `pca-factors.npz` contains loadings, training scores,
means and forecast scores for every primary fold. The implementation rejects
rank-deficient requested PCA subspaces instead of silently changing factor count.

## Forecast targets and baselines

**Primary target: next-month observed quotes.** Use all screened target-month calls
inside the frozen domain, including quotes outside the source rectangle selected
for that month's aligned surface. Future strike/spot and time-to-expiry are used
only to locate those evaluation targets. They are never fit inputs. This evaluates
a surface at future observed coordinates; it does not predict future spot, the
future quote universe, or returns on a fixed option portfolio.

To score every method and every baseline identically, bilinearly evaluate the
**forecast log surface** at these coordinates, then exponentiate. This scoring
operator is separate from the original **IV-before-log** surface construction.
It introduces a common spatial discretization approximation. It is not a second
method-specific cubic/NW fit. Future vendor IV appears only in the loss calculation.

Compare four temporal models:

| Model | Definition |
|---|---|
| PCA AR(1) | Forecast three factor scores with fitted intercept and slope |
| Persistence | Carry the whole most recent observed log surface forward |
| Historical mean | Carry the training mean log surface forward |
| PCA score random walk | Carry current scores forward in the current truncated basis |

Report pooled IV RMSE and MAE in **volatility percentage points** (decimal IV × 100),
log-IV RMSE, and equal-month RMSE `100*sqrt(mean(monthly MSE))`. The latter is the
square root of average monthly MSE, **not** the average of monthly RMSEs.
Pooled scores weight dates by quote count. Nonfinite forecast values fail rather
than disappearing from the denominator.

**Secondary target: each method's own next reconstructed surface.** Score only
dates on which every method's target surface is valid. All methods share dates and
nodes, but their targets differ. These scores help diagnose dynamics; they cannot
establish which interpolation method best forecasts market quotes. Forecasts can
still be scored against raw future quotes when that future aligned surface is
unsupported. That is why grid and quote target counts differ.

The old **1,903 contemporaneous reconstruction holdouts** remain a separate
experiment. Do not compare their RMSE directly with the **1,623 future quotes**
scored across **37 eligible forecast dates** here.

## Sensitivity and stability

No specification is selected by best test performance. The script reports all of:
k=1,2,3,5; expanding versus trailing 24 calendar snapshots; a later first forecast
after 36 snapshots (same frozen domain); NW bandwidth ×0.5 and ×2; and 5×4 / 9×7 /
17×13 grid resolutions on identical domain bounds. Sensitivities with different
eligible dates include the primary reference **restricted to exactly the same
quote dates**, plus full sample counts. A later test start is not directly comparable
with the full primary-period RMSE.

Across consecutive refits and across interpolation methods, report maximum principal
angle, normalized projector distance, and absolute PC1 loading cosine/angle.
Principal angles handle sign changes and rotations; PC1 identity still depends on
eigenvalue separation. A near-right angle in the full three-dimensional space can
reflect weak higher modes while PC1 remains similar. Report explained variance and
eigenvalue gaps beside these diagnostics. High variance explained is not evidence
of high out-of-sample accuracy.

Paired equal-month MSE differences use a descriptive 2,000-replicate moving-block
bootstrap with six **calendar-month** blocks and seed 20261102. Missing origins
remain missing within those blocks. Intervals describe this small selected sample;
they are not a guarantee of significance, stability, independence, or future skill.
They are not adjusted for the many exploratory specifications.

## Nonpositive spline handling

The primary policy is **strict**: preserve invalid IV, do not take its logarithm,
exclude a contaminated training row for all methods, and skip an invalid origin.
Three explicit alternatives are run separately:

| Policy | Change before the logarithm |
|---|---|
| Linear fallback | Replace finite nonpositive spline cells by same-date linear IV |
| Floor 0.0001 | Raise every finite IV below 0.0001 to 0.0001 |
| Floor 0.01 | Raise every finite IV below 0.01 to 0.01 |

None fills unsupported NaN cells. These are altered models, not equivalent spline
implementations. The 9×7 primary grid encounters no nonpositive cell; the 17×13
grid encounters **13 on 2014-03-03**, with minimum IV about **−0.042203**.
The dense-grid policy comparison runs actual historical forecasts and matches
dates against the dense strict policy. Because the strict policy shares training
date exclusions, repairing a spline row also restores that date to the other
methods' training samples; their changes must not be attributed to clipping their IVs.

The original holdout negative is also recomputed separately. It lies at moneyness
0.802944 and maturity 201/365 years, outside this forecast domain; it is not one of
the dense aligned cells. Both phenomena occur on March 3, 2014. Floors can create
large log outliers even when their decimal-IV changes look small. A positive floor
does not establish arbitrage freedom or statistical validity.

## Reproduce and verify

```bash
python -m pip install -r requirements-tested.txt pandas==2.2.3 pyarrow==23.0.1
python -m unittest discover -s tests -v
OPENBLAS_NUM_THREADS=1 python scripts/historical_qqq.py --download
OPENBLAS_NUM_THREADS=1 python scripts/forecast_qqq.py --download
python scripts/write_forecast_report.py
```

Install Octave and R with `pracma` and `jsonlite` to require native verification:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/forecast_qqq.py --require Octave R
```

`--skip-engines` deliberately records them as **NOT RUN**. `passed: true` with no
required native engines means the computations and any executed checks passed;
it does not mean absent engines ran or every scheduled origin was supported.
Check `coverage`, `skipped`, and individual engine status fields.

Source-file hashes, numerical-code SHA-256 hashes, fixture fingerprints, versions,
monthly losses, factor diagnostics and sensitivity records are in `summary.json`.
Generated `aligned-surfaces.npz`, `pca-factors.npz`, alignment fixtures and forecast
fixtures support detailed local inspection. Only aggregate/diagnostic evidence is
committed. The GitHub workflow re-downloads and validates the source data.

Native checks have two explicit boundaries:

* Historical **alignment IV** is independently evaluated by the existing R/Octave
  interpolation runners; tolerance `2e-11 + 2e-10*abs(reference)`, matching NaN masks.
* Primary **PCA/AR(1)** folds are independently fitted in native R/Octave from shared
  Python-constructed log matrices. Compare log forecasts, projection matrices,
  AR slopes and explained-variance ratios at `2e-9 + 2e-8*abs(reference)`.

These checks establish parity of those numerical stages, not independent data
cleaning/backtesting pipelines. Sensitivity runs and positivity policies are Python
experiments; native primary-fold checks do not independently validate all sensitivities.

For actual MATLAB, generate fixtures, run the supplied native runner, then import:

```matlab
addpath('scripts');
run_forecast('results/forecast-qqq/forecast-fixtures.json', ...
             'results/forecast-qqq/forecast-matlab.json');
% Separately export historical IV alignment using the existing run_methods runner:
run_methods('results/forecast-qqq/alignment-fixtures.json', ...
            'results/forecast-qqq/alignment-matlab.json');
```

```bash
python scripts/verify_forecast.py results/forecast-qqq/forecast-fixtures.json \
  --matlab-results results/forecast-qqq/forecast-matlab.json --require MATLAB
```

The forecast importer verifies actual engine identity, version, fixture fingerprint,
case membership, shapes and finite values. The MATLAB alignment export above still
needs a historical alignment importer/comparison using the existing method verifier
utilities; the forecast importer alone does not check it. **Neither historical
MATLAB command has been executed as part of this delivered benchmark.** Existing
synthetic MATLAB evidence remains separate. MATLAB's `interpn(...,'cubic')` is
outside the spline-equivalence contract.

## Limits of the conclusion

Seventy monthly snapshots provide only 46 scheduled and 37 eligible one-step
forecast dates. Quote counts are not independent temporal observations. Coverage
exclusions select a subset of market conditions. The frozen domain is narrow;
the first short calendar interval, changing quote support, rates/dividends and
vendor-IV quality are not separately modeled. QQQ ETF calls are not NDX index
options. No 2000–2010 coverage, daily forecasting, continuous-time AR dynamics,
multi-step forecasting, confidence-calibrated predictive distribution, arbitrage
constraints, transaction costs, or profitable trading conclusions are established.
The original paper's full model choices and original MATLAB script are not available
here; this implementation cannot claim literal reproduction of those details.
