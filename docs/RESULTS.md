# Measured spline results

This is the original local run. A later GitHub run also passed in actual MATLAB
R2025b Update 7; see [CI_RESULTS.md](CI_RESULTS.md). The historical measurements
and statuses below remain unchanged.

Run timestamp: `2026-11-01T15:11:47.903746+00:00`.
Fixture SHA-256: `df542b66443931554da452e934c6c93907244bac04ec2f9b3243eb4af1e1659e`.

**42 cases; 8,687 queries; overall result: PASS.**

Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0.

| Engine | Version | Status | Max absolute error vs independent reference |
| --- | --- | --- | ---: |
| Python | 3.12.14 / SciPy 1.17.0 | RUN | 2.220446049250313e-15 |
| Octave | 8.4.0 | RUN | 4.25215418431435e-14 |
| R | R version 4.3.3 (2024-02-29); pracma 2.4.4; jsonlite 1.8.8 | RUN | 1.498801083243961e-15 |
| MATLAB | — | NOT RUN | — |

Tolerance: absolute 2.0e-11 plus relative 2.0e-10; NaN masks must agree. Infinities are rejected.

Exact arithmetic verifies 200 equalities and supplies 36 rational 2D reference values. The full one-dimensional polynomial coefficient arrays are also compared with SciPy CubicSpline.

## Direct comparisons with Python

| Engine | Max absolute difference from Python |
| --- | ---: |
| Octave | 4.268807529683727e-14 |
| R | 1.998401444325282e-15 |

## Each fixture

| Case | Dimensions | Queries | Python vs reference | Octave vs reference | R vs reference |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1d_uniform_random` | 1 | 67 | 2.776e-16 | 4.441e-16 | 3.331e-16 |
| `1d_irregular_random` | 1 | 67 | 3.331e-16 | 3.331e-16 | 3.331e-16 |
| `1d_tensor_polynomial` | 1 | 67 | 1.943e-16 | 1.665e-16 | 2.220e-16 |
| `2d_uniform_random` | 2 | 83 | 4.441e-16 | 4.441e-16 | 4.441e-16 |
| `2d_irregular_random` | 2 | 83 | 6.592e-16 | 9.437e-16 | 1.360e-15 |
| `2d_tensor_polynomial` | 2 | 83 | 3.331e-16 | 3.331e-16 | 2.220e-16 |
| `3d_uniform_random` | 3 | 143 | 6.661e-16 | 4.441e-16 | 4.441e-16 |
| `3d_irregular_random` | 3 | 143 | 5.551e-16 | 6.661e-16 | 1.443e-15 |
| `3d_tensor_polynomial` | 3 | 143 | 5.274e-16 | 4.718e-16 | 5.829e-16 |
| `4d_uniform_random` | 4 | 463 | 1.110e-15 | 6.661e-16 | 6.106e-16 |
| `4d_irregular_random` | 4 | 463 | 2.220e-15 | 1.332e-15 | 9.992e-16 |
| `4d_tensor_polynomial` | 4 | 463 | 4.441e-16 | 3.053e-16 | 4.718e-16 |
| `basis_5x5_00` | 2 | 31 | 1.214e-16 | 1.908e-16 | 1.492e-16 |
| `basis_5x5_01` | 2 | 31 | 3.331e-16 | 4.059e-16 | 2.498e-16 |
| `basis_5x5_02` | 2 | 31 | 5.551e-16 | 1.665e-16 | 1.665e-16 |
| `basis_5x5_03` | 2 | 31 | 1.249e-16 | 5.551e-17 | 5.551e-17 |
| `basis_5x5_04` | 2 | 31 | 1.214e-17 | 6.939e-18 | 8.674e-18 |
| `basis_5x5_05` | 2 | 31 | 3.400e-16 | 5.482e-16 | 3.123e-16 |
| `basis_5x5_06` | 2 | 31 | 8.882e-16 | 8.882e-16 | 4.441e-16 |
| `basis_5x5_07` | 2 | 31 | 1.166e-15 | 4.441e-16 | 8.882e-16 |
| `basis_5x5_08` | 2 | 31 | 4.996e-16 | 3.331e-16 | 2.498e-16 |
| `basis_5x5_09` | 2 | 31 | 6.939e-17 | 5.551e-17 | 1.110e-16 |
| `basis_5x5_10` | 2 | 31 | 5.759e-16 | 1.943e-16 | 1.665e-16 |
| `basis_5x5_11` | 2 | 31 | 9.437e-16 | 4.996e-16 | 6.661e-16 |
| `basis_5x5_12` | 2 | 31 | 9.992e-16 | 6.661e-16 | 7.772e-16 |
| `basis_5x5_13` | 2 | 31 | 7.772e-16 | 6.106e-16 | 4.996e-16 |
| `basis_5x5_14` | 2 | 31 | 2.220e-16 | 1.527e-16 | 3.331e-16 |
| `basis_5x5_15` | 2 | 31 | 1.943e-16 | 2.220e-16 | 2.220e-16 |
| `basis_5x5_16` | 2 | 31 | 8.882e-16 | 1.277e-15 | 7.772e-16 |
| `basis_5x5_17` | 2 | 31 | 6.661e-16 | 4.441e-16 | 8.188e-16 |
| `basis_5x5_18` | 2 | 31 | 6.661e-16 | 4.441e-16 | 4.441e-16 |
| `basis_5x5_19` | 2 | 31 | 1.388e-16 | 1.110e-16 | 1.110e-16 |
| `basis_5x5_20` | 2 | 31 | 2.151e-16 | 9.021e-17 | 1.388e-16 |
| `basis_5x5_21` | 2 | 31 | 2.220e-16 | 2.220e-16 | 1.110e-16 |
| `basis_5x5_22` | 2 | 31 | 3.331e-16 | 3.331e-16 | 2.220e-16 |
| `basis_5x5_23` | 2 | 31 | 1.110e-16 | 1.110e-16 | 1.110e-16 |
| `basis_5x5_24` | 2 | 31 | 2.082e-17 | 6.939e-18 | 7.806e-18 |
| `rational_2d` | 2 | 36 | 1.665e-16 | 1.388e-16 | 2.220e-16 |
| `volatility_surface` | 2 | 4941 | 4.718e-16 | 4.718e-16 | 4.996e-16 |
| `positive_overshoot` | 2 | 501 | 3.331e-16 | 3.747e-16 | 3.331e-16 |
| `coordinate_scaling` | 2 | 83 | 3.469e-16 | 4.252e-14 | 1.499e-15 |
| `constant_outside_fill` | 2 | 83 | 4.441e-16 | 4.441e-16 | 4.441e-16 |

## Interpretation

The largest Octave discrepancy occurs in the coordinate-scaling case. All reported errors are absolute in the fixture’s value units; the IV example uses decimal volatility.

The positive-input overshoot example reaches -0.203587754667; a real logarithm cannot be applied there. The smooth IV demo remains positive.

The separate default iterative-solver diagnostic differs from the direct solver by 6.4837e-14 on its fixture. It is an accuracy-sensitivity diagnostic, not part of the direct-solver acceptance result.

The ten unit tests check exact constraints, basis linearity, polynomial recovery, domain policy, unsupported input rejection, different natural-spline endpoints, corrupted numbers/masks/shapes, and missing/duplicate/wrong engine identities.

Actual MATLAB output is not included in this report. Mathematical equivalence follows from the common spline definition and uniqueness proof; measured MATLAB parity requires running the included native runner.

The JSON files preserve the underlying numbers and versions. The fixture and source manifest detects later byte changes; it is not an independent signature or a proof that an external execution was authentic.
