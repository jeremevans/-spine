# Actual MATLAB and open-source GitHub results

**Both jobs passed** in [GitHub Actions run 41390026607](https://github.com/jeremevans/-spine/actions/runs/41390026607),
on 1 November 2026 Pacific time (2 November UTC).

Tested code commit: `0a88379747c233227a287504adb02494d926bd45`.
Subsequent commits document the outcome and preserve evidence; they do not
change the numerical implementations, fixtures or workflow.

| Job | Execution | Result |
| --- | --- | --- |
| `python-octave-r` | Native Python, Octave and R; ten unit tests; IV-surface example | PASS |
| `actual-matlab` | Native MATLAB export and Python comparison against an independent reference | PASS |

Each comparison job covered **42 cases and 8,687 query points in 1D–4D**, including
200 exact rational constraint checks and 36 exact rational reference values.
One-dimensional MATLAB cases use `interp1(...,'spline')`; N-D cases use
`interpn(...,'spline')`.

## MATLAB measurements

Actual engine version: **25.2.0.3360999 (R2025b) Update 7**.
Its comparison job used Python 3.12.15, NumPy 2.3.5 and SciPy 1.17.0.
The report timestamp is `2026-11-02T04:44:59.950930+00:00`.

| Comparison | Maximum absolute difference |
| --- | ---: |
| MATLAB vs independent reference | 2.0539125955565396e-15 |
| Python vs independent reference, same MATLAB job | 1.7763568394002505e-15 |
| MATLAB vs Python, directly comparing saved native arrays | 3.552713678800501e-15 |

The predeclared tolerance was `2e-11 + 2e-10 * abs(reference)`, with matching
NaN masks and no infinities. These are floating-point agreements within a
specified contract, not bit-for-bit identity or proof for every software release.

The separate Python/Octave/R job also passed all 42 cases. Its maximum errors
against the reference were 2.220446049250313e-15 for Python,
4.2521541843143495e-14 for Octave, and 1.4988010832439613e-15 for R.
The IV example's maximum cross-engine surface difference was
3.3306690738754696e-16.

## Permanent evidence and reproduction

The [saved MATLAB-job evidence](../evidence/github-actions-41390026607/) contains
the actual `matlab.json`, the same job's `python.json`, its full `summary.json`,
and exact reference outputs. They were extracted unchanged from GitHub artifact
`13116019738`; the archive SHA-256 was verified before extraction.

Fixture fingerprint:
`df542b66443931554da452e934c6c93907244bac04ec2f9b3243eb4af1e1659e`.

To independently check the saved MATLAB outputs from the repository root:

```bash
python -m pip install -r requirements-tested.txt
python scripts/verify.py --python-only \
  --matlab-results evidence/github-actions-41390026607/matlab.json \
  --require MATLAB
```

This rechecks an actual MATLAB export; it does not run MATLAB on your computer.
A local import verification also passed all 42 cases. Minor differences from
the recorded reference errors can arise when recomputing on another platform.
To execute MATLAB afresh, use the native runner in the main README or rerun
the workflow. GitHub artifacts can expire; the native JSON preserved here remains
in repository history.

The [original local results](RESULTS.md) remain a separate historical snapshot.
