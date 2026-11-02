# Forecast evidence, 2 November 2026

`python-summary.json.gz` contains the unaltered local Python output (gzip-compressed) of
`scripts/forecast_qqq.py --skip-engines`. It includes source and numerical-code
hashes, exact grid, all monthly metrics, forecast log surfaces, factor diagnostics,
and parameter/positivity sensitivities. Local native statuses remain NOT RUN.

`ci-native-summary.json` records the two JSON summaries printed by successful
[GitHub run 41528114577](https://github.com/jeremevans/-spine/actions/runs/41528114577),
plus run/commit/job identity and the 41-test count. The original job log and downloadable
`forecast-qqq-evidence` artifact are the primary CI record. This small file is a
faithful extraction of summary objects, not the complete raw native output.
The run's Python results agree with the local primary metrics. Fixture fingerprint
identity is recorded independently; do not imply bitwise equality across platforms.

The run independently checks 210 historical alignment cases in Octave/R and
111 primary PCA/AR(1) folds using shared log matrices. Actual historical MATLAB
forecasting is NOT RUN. The separate synthetic MATLAB job passed and is not
historical evidence. Sensitivity experiments execute in Python.

`monthly-errors.csv` preserves per-date sums of loss and target counts, allowing
aggregate RMSE/MAE to be rebuilt without source quotes. `factor-stability.csv`
contains sign/rotation-aware diagnostics. `unit-tests.log` records the local tests.

Generated raw input fixtures, aligned IV arrays, loadings and factor-score arrays
are available by rerunning the script; source data and generated raw/derived surface
fixtures are not committed here. The source mirror's legal provenance is not
established by a matching hash. See the protocol for sample and interpretation limits.
